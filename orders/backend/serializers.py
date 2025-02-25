from rest_framework import serializers

from backend.models import Contact, User, Category, Shop, Product, ProductParameter, ProductInfo, OrderItem, Order


class ContactSerializer(serializers.ModelSerializer):
    '''Сериализатор модели Contact'''

    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user', 'phone')
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


class UserSerializer(serializers.ModelSerializer):
    '''Сериализатор модели User'''
    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'company', 'position', 'contacts')
        read_only_fields = ('id',)


class CategorySerializer(serializers.ModelSerializer):
    '''Сериализатор модели Category'''

    class Meta:
        model = Category
        fields = ('id', 'name',)
        read_only_fields = ('id',)


class ShopSerializer(serializers.ModelSerializer):
    '''Сериализатор модели Shop'''

    class Meta:
        model = Shop
        fields = ('id', 'name', 'state',)
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    '''Сериализатор модели product'''
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ('name', 'category',)


class ProductParameterSerializer(serializers.ModelSerializer):
    '''Сериализатор модели ProductParameter'''
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value',)


class ProductInfoSerializer(serializers.ModelSerializer):
    '''Сериализатор модели ProductInfo'''
    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = ('id', 'model', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'product_parameters')
        read_only_fields = ('id',)
        ordering = ['-id']


class OrderItemSerializer(serializers.ModelSerializer):
    '''Сериализатор модели OrderItem'''
    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'order',)
        read_only_fields = ('id',)
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemCreateSerializer(serializers.ModelSerializer):
    '''Вспомогательный сериализатор модели OrderItem'''
    product_info = ProductInfoSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ("__all__")


class OrderSerializer(serializers.ModelSerializer):
    '''Сериализатор модели Order'''
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)
    total_sum = serializers.IntegerField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'dt', 'state', 'total_sum', 'contact')
        read_only_field = ('id',)
