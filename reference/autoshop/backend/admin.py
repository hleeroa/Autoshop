from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    """
    model = User

    fieldsets = (
        (None, {'fields': ('email', 'password', 'type')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """
    Панель управления магазинами
    """
    list_display = ('name', 'state')
    search_fields = ('name', 'state')
    list_filter = ('state',)
    ordering = ('name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Панель управления категориями
    """
    list_display = ('name',)
    search_fields = ('name',)
    list_filter = ('name',)
    ordering = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Панель управления товарами
    """
    list_display = ('name', 'category')
    search_fields = ('name', 'category')
    list_filter = ('category',)
    ordering = ('category',)


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """
    Панель управления информацией о товарах
    """
    list_display = ('external_id', 'product__name', 'shop__id', 'quantity', 'price')
    search_fields = ('model', 'external_id')
    list_filter = ('price', 'model', 'shop__id')
    ordering = ('model',)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """
    Панель управления категориями параметров
    """
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """
    Панель управления параметрами
    """
    list_display = ('id', 'parameter__name', 'value')
    search_fields = ('value', 'parameter__name')
    list_filter = ('parameter__name',)
    ordering = ('parameter__name',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Панель управления заказами
    """
    list_display = ('user', 'dt', 'state')
    search_fields = ('user', 'state')
    list_filter = ('user', 'dt', 'state')
    ordering = ('-dt',)
    date_hierarchy = 'dt'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Панель управления элементами заказа
    """
    list_display = ('order', 'product_info', 'quantity')
    search_fields = ('order__id', 'product_info__product__name')
    list_filter = ('product_info__product__name',)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Панель управления контактами пользователей
    """
    list_display = ('user__email', 'city')
    search_fields = ('user__email', 'city')
    list_filter = ('city',)
    ordering = ('city',)


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'created_at',)
