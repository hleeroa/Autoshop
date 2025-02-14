from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.http import JsonResponse
from rest_framework.authtoken.models import Token

from .serializers import UserSerializer
from .tasks import new_user_registered_task, password_reset_token_created_task
from .models import USER_TYPE_CHOICES


class ResetPasswordForm(forms.Form):
    """
    Форма для сброса пароля
    """

    email = forms.EmailField(label='email')

    def send_reset_token(self):
        """
        Ускоренно отправляем письмо с помощью celery
        :return:
        """
        password_reset_token_created_task.delay(
            self.cleaned_data['email'],
        )


class RegisterAccountForm(forms.Form):
    """
    Форма для регистрации пользователей
    """

    email = forms.EmailField(label='Email', widget=forms.EmailInput)
    first_name = forms.CharField(max_length=20, label='Имя')
    last_name = forms.CharField(max_length=25, label='Фамилия')
    type = forms.ChoiceField(choices=USER_TYPE_CHOICES, label='Тип аккаунта')
    position = forms.CharField(max_length=30, label='Позиция', required=False)
    company = forms.CharField(max_length=35, label='Компания', required=False)
    password = forms.CharField(widget=forms.PasswordInput, label='Придумайте пароль')
    widgets = {
        'password': forms.PasswordInput(),
        'email': forms.EmailInput(),
    }

    def send_reg_token(self):
        """
        Заносим пользователя в базу данных и отправляем письмо с токеном активации

        Returns:
            JsonResponse: The response indicating the status of the operation and any errors.
        """
        # проверяем пароль на сложность
        try:
            validate_password(self.cleaned_data['password'])
        except Exception as password_error:
            error_array = []
            # noinspection PyTypeChecker
            for item in password_error:
                error_array.append(item)
            return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
        else:
            # проверяем данные для уникальности имени пользователя

            user_serializer = UserSerializer(data=self.cleaned_data)
            if user_serializer.is_valid():
                # сохраняем пользователя
                user = user_serializer.save()
                user.set_password(self.cleaned_data['password'])
                user.save()
                # отправляем email с токеном активации аккаунта
                new_user_registered_task.delay(
                    sender=user,
                )
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class LoginAccountForm(forms.Form):
    """
    Форма для авторизации пользователей
    """
    email = forms.EmailField(label='Email', widget=forms.EmailInput, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    widgets = {
        'email': forms.EmailInput(),
        'password': forms.PasswordInput(),
    }

    def login(self):
        """
        Authenticate a user.

        Returns:
            JsonResponse: The response indicating the status of the operation and any errors.
        """
        user = authenticate(self.cleaned_data, username=self.cleaned_data['email'], password=self.cleaned_data['password'])

        if user is not None:
            if user.is_active:
                token, _ = Token.objects.get_or_create(user=user)

                return JsonResponse({'Status': True, 'Token': token.key})

        return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'})


class YAMLUploadForm(forms.Form):
    """
    Upload a file form
    """
    file = forms.FileField()
