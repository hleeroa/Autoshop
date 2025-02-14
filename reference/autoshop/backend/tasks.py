from typing import Type

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from celery import shared_task
from django_rest_passwordreset.views import generate_token_for_email
from requests import get
from yaml import load as load_yaml, Loader

from backend.models import ConfirmEmailToken, User, Parameter, ProductParameter, ProductInfo, Product, Category, Shop


@shared_task()
def password_reset_token_created_task(email):
    """
    Ускорено отправляем письмо с токеном для сброса пароля
    с помощью celery
    When a token is created, an e-mail needs to be sent to the user
    :param email: an e-mail address for password resetting
    :return:
    """

    token = generate_token_for_email(email=email)
    # send an e-mail to the user
    msg = EmailMultiAlternatives(
        # title:
        f"Токен для сброса пароля для {email}",
        # message:
        token,
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [email]
    )
    msg.send()


@shared_task()
def new_user_registered_task(sender: Type[User], user: User, created: bool, **kwargs):
    """
    Ускорено отправляем письмо с подтверждением почты
    с помощью celery
    """
    if created and not user.is_active:
        # send an e-mail to the user
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.pk)

        msg = EmailMultiAlternatives(
            # title:
            f"Токен активации аккаунта для {user.email}",
            # message:
            token.key,
            # from:
            settings.EMAIL_HOST_USER,
            # to:
            [user.email]
        )
        msg.send()


@shared_task()
def new_order_task(user_id, **kwargs):
    """
    Ускорено отправляем письмо при изменении статуса заказа
    с помощью celery
    """
    # send an e-mail to the user
    user = User.objects.get(id=user_id)

    msg = EmailMultiAlternatives(
        # title:
        f"Обновление статуса заказа",
        # message:
        'Заказ сформирован',
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [user.email]
    )
    msg.send()


@shared_task()
def do_import_task(url, request):
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
