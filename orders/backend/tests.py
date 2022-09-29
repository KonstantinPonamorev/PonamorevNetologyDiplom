import random
from random import choice
from string import ascii_letters
import factory
import factory.django

from django.urls import reverse, path, include
from factory.fuzzy import FuzzyInteger
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase, URLPatternsTestCase

from backend.models import User, ConfirmEmailToken, Category, Shop, Product, ProductInfo, Parameter, ProductParameter, \
    Contact, Order, OrderItem


def generate_random_string(len):
    return ''.join(choice(ascii_letters) for i in range(len))

def log_in_user(user, APIClient):
    user.is_active = True
    user.save()
    token, _ = Token.objects.get_or_create(user=user)
    APIClient.credentials(HTTP_AUTHORIZATION='Token ' + token.key)


class UserFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = User

    email = factory.Faker('email')
    password = factory.Faker('password')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    company = factory.Faker('company')
    position = factory.Faker('job')


class ShopFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Shop

    name = factory.Faker('company')
    url = factory.Faker('url')
    user = factory.SubFactory(UserFactory)
    state = True


class CategoryFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Category

    name = factory.Faker('word')

    @factory.post_generation
    def shops(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for shop in extracted:
                self.shops.add(shop)


class ProductFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Product

    name = factory.Faker('sentence')
    category = factory.SubFactory(CategoryFactory)


class ProductInfoFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = ProductInfo

    model = factory.Faker('sentence')
    external_id = FuzzyInteger(1, 1000000)
    product = factory.SubFactory(ProductFactory)
    shop = factory.SubFactory(ShopFactory)
    price = FuzzyInteger(1, 1000000)
    quantity = FuzzyInteger(1, 1000000)
    price_rrc = FuzzyInteger(1, 1000000)


class ParameterFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Parameter

    name = factory.Faker('sentence')


class ProductParameterFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = ProductParameter

    product_info = factory.SubFactory(ProductInfoFactory)
    parameter = factory.SubFactory(ParameterFactory)
    value = factory.Faker('sentence')


class ContactFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Contact

    user = factory.SubFactory(UserFactory)
    city = factory.Faker('city')
    street = factory.Faker('street_name')
    house = factory.Faker('building_number')
    structure = factory.Faker('word')
    building = factory.Faker('word')
    apartment = factory.Faker('building_number')
    phone = factory.Faker('phone_number')


class OrderFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    dt = factory.Faker('date_time')
    state = 'new'
    contact = factory.SubFactory(ContactFactory)


class OrderItemFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product_info = factory.SubFactory(ProductInfoFactory)
    quantity = FuzzyInteger(1, 10)



class RegisterAccountTests(APITestCase):

    url = reverse('backend:user-register')

    def generate_register_data(self):
        return {
            'email': f'{generate_random_string(10)}@gmail.com',
            'password': generate_random_string(10),
            'first_name': generate_random_string(10),
            'last_name': generate_random_string(10),
            'company': generate_random_string(10),
            'position': generate_random_string(10)
        }

    def test_user_registration_correct(self):
        data = self.generate_register_data()
        response = self.client.post(self.url, data)
        user = User.objects.filter(email=data['email']).first()
        assert response.status_code == 200
        assert user is not None
        assert user.first_name == data['first_name'] and \
               user.last_name == data['last_name']
        assert User.objects.count() == 1

    def test_user_registration_no_company(self):
        data = self.generate_register_data()
        data.pop('company')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_email(self):
        data = self.generate_register_data()
        data.pop('email')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(first_name=data['first_name'], last_name=data['last_name'],
                                   company=data['company'], position=data['position']).first() is None

    def test_user_registration_no_first_name(self):
        data = self.generate_register_data()
        data.pop('first_name')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_last_name(self):
        data = self.generate_register_data()
        data.pop('last_name')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_position(self):
        data = self.generate_register_data()
        data.pop('position')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_password(self):
        data = self.generate_register_data()
        data.pop('password')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_invalid_password(self):
        data = self.generate_register_data()
        data['password'] = '1'
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None


class ConfirmAccountTests(APITestCase):

    url = reverse('backend:user-register-confirm')

    def test_confirm_token_correct(self):
        user = UserFactory.create()
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
        data = {'email': user.email,
                'token': token.key}
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert ConfirmEmailToken.objects.filter(user_id=user.id).first() is None
        assert User.objects.filter(id=user.id).first().is_active == True

    def test_confirm_token_uncorrect_token(self):
        user = UserFactory.create()
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
        data = {'email': user.email,
                'token': generate_random_string(20)}
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert ConfirmEmailToken.objects.filter(user_id=user.id).first() is not None
        assert User.objects.filter(id=user.id).first().is_active == False

    def test_confirm_token_uncorrect_email(self):
        user = UserFactory.create()
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
        data = {'email': 'mail@gmail.com',
                'token': token.key}
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert ConfirmEmailToken.objects.filter(user_id=user.id).first() is not None
        assert User.objects.filter(id=user.id).first().is_active == False


class AccountDetailsTests(APITestCase):

    url = reverse('backend:user-details')

    def test_view_account_details_correct(self):
        user = UserFactory.create()
        log_in_user(user, self.client)
        response = self.client.get(self.url)
        assert response.status_code == 200

    def test_view_account_details_unauthenticated(self):
        response = self.client.get(self.url)
        assert response.status_code == 403

    def test_edit_account_details_unathenticated(self):
        response = self.client.post(self.url)
        assert response.status_code == 403

    def test_edit_account_details_names_coorect(self):
        data = {
            'first_name': generate_random_string(15),
            'last_name': generate_random_string(15),
        }
        user = UserFactory.create()
        log_in_user(user, self.client)
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=user.email).first().first_name == data['first_name'] and \
               User.objects.filter(email=user.email).first().last_name == data['last_name']

    def test_edit_account_details_work_correct(self):
        data = {
            'company': generate_random_string(15),
            'position': generate_random_string(15)
        }
        user = UserFactory.create()
        log_in_user(user, self.client)
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=user.email).first().company == data['company'] and \
               User.objects.filter(email=user.email).first().position == data['position']

    def test_edit_account_details_unexpected_argument(self):
        data = {
            generate_random_string(10): generate_random_string(15),
            'email': 'new_email',
        }
        user = UserFactory.create()
        log_in_user(user, self.client)
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=user.email).first().email != data['email']

    def test_edit_account_details_invalid_password(self):
        data = {
            'password': generate_random_string(3),
        }
        user = UserFactory.create()
        log_in_user(user, self.client)
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=user.email).first().password != data['password']


class LoginAccountTests(APITestCase):

    url = reverse('backend:user-login')

    # def test_correct_login(self):
    #     user = UserFactory.create()
    #     user.is_active = True
    #     user.save()
    #     data = {
    #         'email': user.email,
    #         'password': user.password
    #     }
    #     response = self.client.post(self.url, data)
    #     assert response.status_code == 200
    #     assert Token.objects.filter(user=user.id).first() is not None

    def test_uncorrect_password(self):
        # user = create_user()
        user = UserFactory.create()
        user.is_active = True
        user.save()
        data = {
            'email': user.email,
            'password': generate_random_string(10)
        }
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert Token.objects.filter(user=user.id).first() is None

    def test_uncorrect_email(self):
        user = UserFactory.create()
        user.is_active = True
        user.save()
        data = {
            'email': generate_random_string(10),
            'password': user.password
        }
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert Token.objects.filter(user=user.id).first() is None


class CategoryTests(APITestCase):

    url = reverse('backend:category-list')

    def test_get_categories(self):
        count = random.randint(1, 15)
        for i in range(1, count + 1):
            CategoryFactory.create()
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert response.data['count'] == count
        assert Category.objects.count() == count

    def test_get_category_details(self):
        category = CategoryFactory.create()
        response = self.client.get(f'{self.url}{category.id}/')
        assert response.status_code == 200
        assert response.data['name'] == category.name

    def test_get_category_detail_not_exist(self):
        response = self.client.get(f'{self.url}{random.randint(1, 20)}/')
        assert response.status_code == 404


class ShopTest(APITestCase):

    url = reverse('backend:shop-list')

    def test_get_shops(self):
        count = random.randint(1, 15)
        for i in range(1, count + 1):
            ShopFactory.create()
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert response.data['count'] == count
        assert Shop.objects.count() == count

    def test_get_shop_details(self):
        shop = ShopFactory.create()
        response = self.client.get(f'{self.url}{shop.id}/')
        assert response.status_code == 200
        assert response.data['name'] == shop.name

    def test_get_shop_detail_not_exist(self):
        response = self.client.get(f'{self.url}{random.randint(1, 20)}/')
        assert response.status_code == 404


class ProductTest(APITestCase):

    url = reverse('backend:product_info-list')

    def test_get_products(self):
        count = random.randint(1, 15)
        for i in range(1, count + 1):
            ProductInfoFactory.create()
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert response.data['count'] == count
        assert ProductInfo.objects.count() == count

    def test_get_product_detail(self):
        product_info = ProductInfoFactory.create()
        response = self.client.get(f'{self.url}{product_info.id}/')
        assert response.status_code == 200
        assert response.data['id'] == product_info.id

    def test_get_product_detail_not_exist(self):
        response = self.client.get(f'{self.url}{random.randint(1, 20)}/')
        assert response.status_code == 404

    def test_get_product_detail_by_shop(self):
        product_info = ProductInfoFactory.create()
        response = self.client.get(self.url, params={'shop_id': product_info.shop.id})
        assert response.status_code == 200
        assert response.data['results'][0]['id'] == product_info.product.id

    def test_get_product_detail_by_category(self):
        product_info = ProductInfoFactory.create()
        response = self.client.get(self.url, params={'category_id': product_info.product.category.id})
        assert response.status_code == 200
        assert response.data['results'][0]['id'] == product_info.product.id


class ContactTests(APITestCase):

    url = reverse('backend:user-contact')

    def generate_contacts_data(self):
        return {
            'city': generate_random_string(10),
            'street': generate_random_string(10),
            'house': random.randint(1, 100),
            'structure': random.randint(1, 20),
            'building': random.randint(1, 20),
            'apartment': random.randint(1, 100),
            'phone': generate_random_string(10)
        }

    def test_get_user_contacts(self):
        contact = ContactFactory.create()
        user = contact.user
        log_in_user(user, self.client)
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert response.data[0]['phone'] == contact.phone

    def test_get_user_contacts_unauthenticated(self):
        response = self.client.get(self.url)
        assert response.status_code == 403

    def test_add_new_contact_unauthenticated(self):
        response = self.client.get(self.url)
        assert response.status_code == 403

    def test_add_new_contact_correct(self):
        data = self.generate_contacts_data()
        user = UserFactory.create()
        log_in_user(user, self.client)
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert user.contacts.filter(phone=data['phone'], city=data['city'], street=data['street']).first() is not None

    def test_add_new_contact_no_phone(self):
        data = self.generate_contacts_data()
        data.pop('phone')
        user = UserFactory.create()
        log_in_user(user, self.client)
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert user.contacts.filter(city=data['city'], street=data['street']).first() is None

    def test_add_new_contact_no_city(self):
        data = self.generate_contacts_data()
        data.pop('city')
        user = UserFactory.create()
        log_in_user(user, self.client)
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert user.contacts.filter(phone=data['phone'], street=data['street']).first() is None

    def test_delete_user_contacts_unauthenticated(self):
        response = self.client.delete(self.url, {'items': '1'})
        assert response.status_code == 403

    def test_delete_user_contacts_correct(self):
        contact = ContactFactory.create()
        user = contact.user
        log_in_user(user, self.client)
        response = self.client.delete(self.url, {'items': contact.id})
        assert response.status_code == 200
        assert Contact.objects.filter(user_id=user.id).first() is None

    def test_delete_user_contact_uncorrect(self):
        contact = ContactFactory.create()
        user = contact.user
        log_in_user(user, self.client)
        response = self.client.delete(self.url, {'contact': contact.id})
        assert response.status_code == 200
        assert Contact.objects.filter(user_id=user.id).first() is not None

    def test_edit_contacts_unauthenticated(self):
        response = self.client.put(self.url)
        assert response.status_code == 403


class OrderTests(APITestCase):

    url = reverse('backend:orders')

    def test_get_user_order_unauthenticated(self):
        response = self.client.get(self.url)
        assert response.status_code == 403

    def test_get_user_order_correct(self):
        order = OrderFactory.create()
        user = order.user
        log_in_user(user, self.client)
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert response.data[0]['contact']['id'] == order.contact.id

    def test_make_new_order_unauthenticated(self):
        response = self.client.post(self.url)
        assert response.status_code == 403

    def test_make_new_order_correct(self):
        basket = OrderFactory.create()
        basket.state = 'basket'
        basket.save()
        user = basket.user
        contact = ContactFactory.create()
        contact.user = user
        log_in_user(user, self.client)
        response = self.client.post(self.url, {'id': basket.id,
                                               'contact': contact.id})
        assert response.status_code == 200
        assert Order.objects.get(id=basket.id).state == 'new'

    def test_make_new_order_uncorrect(self):
        basket = OrderFactory.create()
        basket.state = 'basket'
        basket.save()
        user = basket.user
        contact = ContactFactory.create()
        contact.user = user
        log_in_user(user, self.client)
        response = self.client.post(self.url, {'contact': contact.id,})
        assert response.status_code == 200
        assert Order.objects.get(id=basket.id).state == 'basket'


class BasketTest(APITestCase):

    url = reverse('backend:basket')

    def test_get_user_basket_unauthenticated(self):
        response = self.client.get(self.url)
        assert response.status_code == 403

    def test_get_user_basket_correct(self):
        basket = OrderFactory.create()
        basket.state = 'basket'
        basket.save()
        user = basket.user
        log_in_user(user, self.client)
        response = self.client.get(self.url)
        assert response.status_code == 200
        assert response.data[0]['contact']['id'] == basket.contact.id

    def test_delete_user_basket_unauthenticated(self):
        response = self.client.delete(self.url)
        assert response.status_code == 403


