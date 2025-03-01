from django.contrib import admin, messages
from django.urls import path, reverse
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.views import main
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage

from .models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken
from .tasks import do_import_task


class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    """
    def __init__(self, *args, **kwargs):
        super(CustomUserAdmin, self).__init__(*args, **kwargs)
        main.EMPTY_CHANGELIST_VALUE = '-'

    model = User
    fieldsets = (
        (None, {'fields': ('image', 'email', 'type', 'image_tag')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    readonly_fields = ['image_tag']
    list_display = ('email', 'first_name', 'last_name', 'is_staff')

# Регистрируем модель User
admin.site.register(User, CustomUserAdmin)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """
    Панель управления магазинами
    """
    change_list_template = "admin/shop_change_list.html"
    list_display = ('name', 'state')
    search_fields = ('name', 'state')
    list_filter = ('state',)
    ordering = ('name',)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-data/', self.admin_site.admin_view(self.import_data_view), name='shop_import_data'),
        ]
        return custom_urls + urls

    def import_data_view(self, request):
        if request.method == 'POST':
            uploaded_file = request.FILES.get('data_file')
            if uploaded_file:
                have_shop = User.objects.filter(id=request.user.id).cache()[0].shop
                if have_shop:
                    self.message_user(request, 'One user cannot have multiple shops.', messages.ERROR)
                else:
                    file_path = default_storage.save('tmp/shop_import.yaml', uploaded_file)
                    file_url = default_storage.url(file_path)
                    # Trigger the asynchronous import task.
                    do_import_task.delay(''.join(('http://127.0.0.1:8000', file_url)), request.user.id)
                    self.message_user(request, 'Data import has been started.', messages.SUCCESS)
                return redirect(reverse('admin:shop_import_data'))
            else:
                self.message_user(request, "No file was uploaded.", messages.ERROR)
        return render(request, "admin/import_data_form.html")


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
    readonly_fields = ['image_tag']


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
