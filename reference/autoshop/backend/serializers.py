from rest_framework import serializers
from versatileimagefield.serializers import VersatileImageFieldSerializer

from backend.models import User, Category, Shop, ProductInfo, Product, ProductParameter, OrderItem, Order, Contact


class ContactSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user', 'phone')
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


class UserSerializer(serializers.HyperlinkedModelSerializer):
    contacts = ContactSerializer(read_only=True, many=True, help_text='Адрес и телефон пользователя.')
    image = VersatileImageFieldSerializer(
        sizes=[
            ('full_size', 'url'),
            ('thumbnail', 'thumbnail__100x100'),
            ('medium_square_crop', 'crop__400x400'),
            ('small_square_crop', 'crop__50x50')
        ]
    )

    class Meta:
        model = User
        fields = ('id', 'image', 'first_name', 'last_name', 'type', 'company',
                  'position', 'email', 'password', 'contacts')
        read_only_fields = ('id',)


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name',)


class ShopSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'name', 'state',)
        read_only_fields = ('id',)


class ProductSerializer(serializers.HyperlinkedModelSerializer):
    category = serializers.StringRelatedField(help_text='Категория продукта. Телефон, еда или транспортное средство')

    class Meta:
        model = Product
        fields = ('name', 'category',)


class ProductParameterSerializer(serializers.HyperlinkedModelSerializer):
    parameter = serializers.StringRelatedField(help_text='Отдельный критерий описания. Форма, '
                                                         'разрешение экрана, память')

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value',)


class ProductInfoSerializer(serializers.HyperlinkedModelSerializer):
    product = ProductSerializer(read_only=True, help_text='Конкретный продукт.')
    product_parameters = ProductParameterSerializer(read_only=True, many=True, help_text='Список параметров. '
                                                                                         'Описывают продукт.')
    image = VersatileImageFieldSerializer(
        sizes=[
            ('full_size', 'url'),
            ('thumbnail', 'thumbnail__100x100'),
            ('medium_square_crop', 'crop__400x400'),
            ('small_square_crop', 'crop__50x50')
        ]
    )

    class Meta:
        model = ProductInfo
        fields = ('id', 'image', 'model', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'product_parameters',)
        read_only_fields = ('id',)


class OrderItemSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity',)
        read_only_fields = ('id',)
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemCreateSerializer(serializers.HyperlinkedModelSerializer):
    product_info = ProductInfoSerializer(read_only=True, help_text='Продукт и его описание.')


class OrderSerializer(serializers.HyperlinkedModelSerializer):
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True, help_text='Список продуктов в одном заказе.')

    total_sum = serializers.IntegerField(help_text='Итоговая сумма заказа.')
    contact = ContactSerializer(read_only=True, help_text='Телефон и адрес заказчика.')

    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'state', 'dt', 'total_sum', 'contact',)
        read_only_fields = ('id',)
