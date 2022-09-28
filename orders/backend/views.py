from distutils.util import strtobool

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Sum, F, Q
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from requests import get
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from yaml import load as load_yaml, Loader
from ujson import loads as load_json

from backend.models import Shop, Category, ProductInfo, Product, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken
from backend.serializers import UserSerializer, ShopSerializer, OrderSerializer, CategorySerializer, \
    ProductInfoSerializer, OrderItemSerializer, ContactSerializer
# from backend.signals import new_user_registered, new_order
from backend.tasks import new_user_registered_task, new_order_task


class PartnerUpdateView(APIView):
    '''Класс для обновления прайса от поставщика.'''

    def post(self, request, *args, **kwargs):
        '''Обновление прайса поставщика методом POST.

        Для использования необходима авторизация от лица поставщика.
        В запросе необходимо указать url файла ".yaml", в котором находится информация для обновления.

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Only shops'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                stream = get(url).content
                data = load_yaml(stream, Loader=Loader)
                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_object.shops.add(shop.id)
                    category_object.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])
                    product_info = ProductInfo.objects.create(product_id=product.id,
                                                              external_id=item['id'],
                                                              model=item['model'],
                                                              price=item['price'],
                                                              price_rrc=item['price_rrc'],
                                                              quantity=item['quantity'],
                                                              shop_id=shop.id)
                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=parameter_object.id,
                                                        value=value)
                return JsonResponse({'Status': True})
        return JsonResponse({'Status': False, "Errors": 'Не указаны необходимые аргументы'})


class PartnerStateView(APIView):
    '''Класс для работы со статусом поставщика.'''

    def get(self, request, *args, **kwargs):
        '''Узнать статус поставщика методом GET.

        Необходима авторизация от лица поставщика.
        На выходе показывает текущий статус магазина.

        '''

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'For shops only'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        '''Изменить статус поставщика методом POST.

        Необходима авторизация от лица поставщика.
        Меняет текущий стату магазина на прием заказов onn\off.

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'For shops only'}, status=403)

        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True, 'State': state})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})
        return JsonResponse({'Status': False, 'Error': 'Need new state'})


class PartnerOrdersView(APIView):
    '''Класс для работы поставщиков с заказами'''

    def get(self, request, *args, **kwargs):
        '''Получить заказы методом GET.

        Необходима авторизация от лица поставшика.
        На выходе дает активные заказы текущего поставщика.

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'For shops only'}, status=403)

        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class RegisterAccountView(APIView):
    '''Класс для регистрации покупателей.'''

    def post(self, request, *args, **kwargs):
        '''Регистрация нового покупателя методом POST.

        Необходимо передать аргументы:
            first_name,
            last_name,
            email,
            company,
            position

        По результату отправляет письмо на указанную электронную почту с токеном для подтверждения.

        '''
        if {'first_name', 'last_name', 'email', 'company', 'position'}.issubset(request.data):
            errors = {}
            try:
                validate_password(request.data['password'])
            except Exception as password_er:
                error_array = []
                for item in password_er:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': error_array})
            else:
                request.data._mutable = True
                request.data.update({})
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    new_user_registered_task.delay(user_id=user.id)
                    # new_user_registered.send(sender=self.__class__, user_id=user.id)
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны аргументы'})


class ConfirmAccountView(APIView):
    '''Класс подтверждения адреса электронной почты.'''

    def post(self, request, *args, **kwargs):
        '''Подтверждение электронной почты методом POST.

        Для подтверждения необходимо передать токен, полученный на электронную почту при регистрации.

        '''
        if {'email', 'token'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Error': 'Wrong token or email'})

        return JsonResponse({'Status': False, 'Error': 'enter token and email'})


class AccountDetailsView(APIView):
    '''Класс для работы с данными пользователя.'''

    def get(self, request, *args, **kwargs):
        '''Получить данные методом GET.

        Необходима авторизация от лица покупателя.
        На выходе дает информацию о пользователе.

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        '''Редактировать данные методом POST.

        Необходимо передать новые данные для редактирования.
        Изменяет текущие данные пользователя на новые.

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if 'password' in request.data:
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                request.user.set_password(request.data['password'])

        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class LoginAccountView(APIView):
    '''Класс для авторизации пользователей'''

    def post(self, request, *args, **kwargs):
        '''Авторизация пользователя методом POST.

        Необходимо передать верные логин и пароль для авторизации.
        На выходе дает уникальный token авторизации.

        '''
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    return JsonResponse({'Status': True, 'Token': token.key})
                return JsonResponse({'Status': False, 'Errors': 'Can"t authenticate'})
            return JsonResponse({'Status': False, 'Errors': 'Need more uthenticate arguments'})


# class CategoryView(ListAPIView):
#
#     queryset = Category.objects.all()
#     serializer_class = CategorySerializer


class CategoryViewSet(ReadOnlyModelViewSet):
    '''Класс для просмотра категорий.'''

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


# class ShopView(ListAPIView):
#
#     queryset = Shop.objects.filter(state=True)
#     serializer_class = ShopSerializer

class ShopViewSet(ReadOnlyModelViewSet):
    '''Класс для просмотра магазинов'''

    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer

# class ProductInfoView(APIView):
#
#     def get(self, request, *args, **kwargs):
#
#         query = Q(shop__state=True)
#         shop_id = request.query_params.get('shop_id')
#         category_id = request.query_params.get('category_id')
#
#         if shop_id:
#             query = query & Q(shop_id=shop_id)
#         if category_id:
#             query = query & Q(product__category_id=category_id)
#
#         queryset = ProductInfo.objects.filter(query).select_related(
#             'shop', 'product__category').prefetch_related('product_parameters__parameter').distinct()
#
#         serializer = ProductInfoSerializer(queryset, many=True)
#         return Response(serializer.data)

class ProductInfoViewSet(ModelViewSet):
    '''Класс для поиска товаров'''

    queryset = ProductInfo.objects.all()
    serializer_class = ProductInfoSerializer

    def product_info(self, request, *args, **kwargs):
        '''Функция поиска товаров.

        Используется метод GET.
        В query string можно передать:
            id магазина
            id категории

        '''
        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)
        if category_id:
            query = query & Q(product__category_id=category_id)

        queryset = ProductInfo.objects.filter(query).select_related(
            'shop', 'product__category').prefetch_related('product_parameters__parameter').distinct()

        serializer = ProductInfoSerializer(queryset, many=True)
        return Response(serializer.data)



class BasketView(APIView):
    '''Класс для работы с корзиной пользователя'''


    def get(self, request, *args, **kwargs):
        '''Посмотреть корзину методом GET.

        Необходима авторизация от лица покупателяю

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'})

        basket = Order.objects.filter(
            user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        '''Редактировать корзину методом post.

        Необходимо передать добавляемые товары в формате:
            [{"product_info": x, "quantity": y}, ...]
            Где:
                x - id информации о продукте,
                y - количество товара

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_string = request.data.get('items')
        if items_string:
            try:
                items_dict = load_json(items_string)
            except ValueError:
                return JsonResponse({'Status': False, 'Error': 'Wrong format'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({'order': basket.id})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return JsonResponse({'Status': False, 'Error': str(error)})
                        else:
                            objects_created += 1
                    else:
                        return JsonResponse({'Status': False, 'Error': serializer.errors})

                return JsonResponse({'Status': True, 'В корзину добавлено': f'{objects_created} товаров'})
        return JsonResponse({'Status': False, 'Error': 'Не указаны аргументы'})

    def delete(self, request, *args, **kwargs):
        '''Удалить товары из корзины методом DELETE.

        Необходимо передать id удаляемых товаров через запятую.

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_string = request.data.get('items')
        if items_string:
            items_list = items_string.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено': f'{deleted_count} объектов'})
            return JsonResponse({'Status': False, 'Error': 'не указаны все аргументы'})

    def put(self, request, *args, **kwargs):
        '''Редактировать количество товаров в корзине методом PUT.

        Необходимо передать редактируемы товары списком в формате:
            [ { "id": x, "quantity": y }, ... ] , где:
                x - id  редактируемого товара,
                y - какое количество товара добавить

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_string = request.data.get('items')
        if items_string:
            try:
                items_dict = load_json(items_string)
            except ValueError:
                return JsonResponse({'Status': False, "Errors": 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                for order_item in items_dict:
                    if type(order_item['id']) == int and type(order_item['quantity']) == int:
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity'])
                return JsonResponse({'Status': True, 'Обновлено': f'{objects_updated} объектов'})
        return JsonResponse({'Status': False, 'Error': 'Укажите аргументы'})


class ContactView(APIView):
    '''Класс для работы с контактами покупателей'''

    def get(self, request, *args, **kwargs):
        '''Получить контакты пользователя методом GET.

        Необходима авторизация от лица пользователя.

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        contact = Contact.objects.filter(user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        '''Добавить новый контакт методом POST.

        Необходима авторизация от лица пользователя.
        Необходимо передать обязательные параметры:
            city - город проживания,
            street - улица проживания,
            phone - номер телефона
        Необязательные параметры:
            house - дом,
            structure - корпус,
            building - строение,
            apartment - квартира

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'city', 'street', 'phone'}.issubset(request.data):
            request.data._mutable = True
            request.data.update({'user': request.user.id})
            serializer = ContactSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True})
            else:
                JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Error': 'Введите все аргументы'})

    def delete(self, request, *args, **kwargs):
        '''Удалить контакты методом DELETE.

        Необходима авторизация от лица пользователя.
        Необходимо передать id удаляемых контактов.

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_string = request.data.get('items')
        if items_string:
            items_list = items_string.split(',')
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(id=contact_id, user_id=request.user.id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено': f'{deleted_count} контактов'})
            return JsonResponse({'Status': False, 'Error': 'Укажите аргументы'})


    def put(self, request, *args, **kwargs):
        '''Редактировать контакты методом PUT.

        Необходима авторизация от лица пользователя.
        Необходимо передать изменяемые данные и id изменяемого контакта.

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if 'id' in request.data:
            if request.data['id'].isdigit():
                contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
                if contact:
                    serializer = ContactSerializer(contact, data=request.data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return JsonResponse({'Status': True})
                    else:
                        JsonResponse({'Status': False, 'Error': serializer.errors})

        return JsonResponse({'Status': False, 'Error': 'Укажите аргументы'})


class OrderView(APIView):
    '''Класс для работы пользователей с заказами'''

    def get(self, request, *args, **kwargs):
        '''Получить заказы пользователя методом GET.

        Необходима авторизация от лица покупателя.

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        orders = Order.objects.filter(user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        '''Разместить заказ из корзины методом POST.

        Необходима авторизация от лица покупателя.
        Необходимо передать id заказа.
        Заказ должен быть в статусте "basket".
        Необходимо указать контакты покупателя.

        '''
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'id', 'contact'}.issubset(request.data):
            if request.data['id'].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data['id']).update(
                        contact_id=request.data['contact'],
                        state='new')
                except IntegrityError as error:
                    return JsonResponse({'Status': False, 'Error': 'Wrong arguments'})
                else:
                    if is_updated:
                        new_order_task.delay(user_id=request.user.id)
                        # new_order.send(sender=self.__class__, user_id=request.user.id)
                        return JsonResponse({'Status': True})

        return JsonResponse({'Status': 'Укажите все аргументы'})
