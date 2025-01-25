from typing import Type

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from celery import shared_task
from django_rest_passwordreset.views import generate_token_for_email

from backend.models import ConfirmEmailToken, User


@shared_task()
def password_reset_token_created(email):
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
        f"Password Reset Token for {email}",
        # message:
        token,
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [email]
    )
    msg.send()


@shared_task()
def new_user_registered(sender: Type[User], instance: User, created: bool, **kwargs):
    """
    Ускорено отправляем письмо с подтверждением почты
    с помощью celery
    """
    if created and not instance.is_active:
        # send an e-mail to the user
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)

        msg = EmailMultiAlternatives(
            # title:
            f"Password Reset Token for {instance.email}",
            # message:
            token.key,
            # from:
            settings.EMAIL_HOST_USER,
            # to:
            [instance.email]
        )
        msg.send()


@shared_task()
def new_order(user_id, **kwargs):
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
