from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.http import JsonResponse
from rest_framework.authtoken.models import Token
from versatileimagefield.widgets import SizedImageCenterpointClickDjangoAdminWidget

from .serializers import UserSerializer
from .tasks import new_user_registered_task, password_reset_token_created_task
from .models import User


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


class CustomImageWidget(SizedImageCenterpointClickDjangoAdminWidget):
    template_name = 'widgets/custom_image_widget.html'

    def value_from_datadict(self, data, files, name):
        # Ensure the file is correctly returned from the uploaded files
        file_val = files.get(name)
        if file_val:
            return file_val
        return super().value_from_datadict(data, files, name)


class RegisterAccountForm(forms.ModelForm):
    """
    Форма для регистрации пользователей
    """
    image = forms.ImageField(required=False, widget=CustomImageWidget)

    class Meta:
        model = User
        fields = ('image', 'first_name', 'last_name', 'type',
                  'position', 'company', 'email', 'password')
        labels = {
            'first_name': '',
            'last_name': '',
            'type': '',
            'position': '',
            'company': '',
            'email': '',
            'password': ''
        }
        widgets = {
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Придумай пароль'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Должность'}),
            'company': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Компания'}),
        }

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if isinstance(image, tuple):
            return image[0]
        return image

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
            return error_array
        else:
            data = self.cleaned_data.copy()
            user_serializer = UserSerializer(data=data)
            if user_serializer.is_valid():
                # сохраняем пользователя
                user = user_serializer.save()
                user.set_password(self.cleaned_data['password'])
                user.save()
                # отправляем email с токеном активации аккаунта
                new_user_registered_task.delay(
                    pk=user.id,
                    sender='',
                    email=user.email,
                    is_active=user.is_active,
                    created=True,
                )
                return {'Status': True}
            else:
                return user_serializer.errors


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
        user = authenticate(self.cleaned_data, username=self.cleaned_data['email'],
                            password=self.cleaned_data['password'])

        if user is not None:
            if user.is_active:
                token, _ = Token.objects.get_or_create(user=user)

                return JsonResponse({'Status': True, 'Token': token.key})

        return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'})
