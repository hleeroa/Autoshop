from django.views.generic import FormView, TemplateView
from drf_spectacular.utils import OpenApiResponse, OpenApiExample, OpenApiRequest
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.request import Request
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from json import loads

from backend.models import Shop, Category, ProductInfo, Order, OrderItem, Contact, ConfirmEmailToken
from backend.serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, \
    OrderItemSerializer, OrderSerializer, ContactSerializer
from backend.tasks import new_order_task, do_import_task
from backend.forms import ResetPasswordForm, RegisterAccountForm, LoginAccountForm


class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """
    throttle_scope = 'confirm'

    @extend_schema(
        summary="Подтверждение почты",
        parameters=[
            OpenApiParameter("email", description="Email пользователя"),
            OpenApiParameter("token", description="Токен подтверждения почты"),
        ],
        description="Подтверждает email пользователя, делая его активным (is_active=True).",
        responses={200: OpenApiResponse(response=OpenApiResponse(),
                                        description='Success',
                                        examples=[
                                                 OpenApiExample("Аккаунт подтверждён",
                                                                value={"Status": True}),
                                                 OpenApiExample("Не всё указано",
                                                                value={"Status": False, "Errors": "Не указаны все "
                                                                                             "необходимые аргументы"}),
                                                 OpenApiExample("Неправильные аргументы",
                                                                value={'Status': False, 'Errors': 'Неправильно '
                                                                                             'указан токен или email'})
                                            ]
                                        )
                   },
    )
    # Регистрация методом POST
    def post(self, request, *args, **kwargs):
        """
        Подтверждает почтовый адрес пользователя.

        Args:
        - request (Request): The Django request object.

        Returns:
        - JsonResponse: The response indicating the status of the operation and any errors.
        """
        # проверяем обязательные аргументы
        if {'email', 'token'}.issubset(request.data):

            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан токен или email'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class AccountDetails(APIView):
    """
    A class for managing user account details.

    Methods:
    - get: Retrieve the details of the authenticated user.
    - post: Update the account details of the authenticated user.

    Attributes:
    - None
    """

    @extend_schema(
        summary="Получение данных аккаунта",
        description="Возвращает данные авторизованного пользователя.",
        responses={200: UserSerializer,
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        examples=[
                       OpenApiExample('Не авторизован',
                                      value={'Status': False, 'Error': 'Log in required'}),
                   ])},
    )
    # получить данные
    def get(self, request: Request, *args, **kwargs):
        """
               Retrieve the details of the authenticated user.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the details of the authenticated user.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        summary="Обновление данных аккаунта",
        description="Обновляет данные авторизованного пользователя, включая смену пароля.",
        request=UserSerializer,
        responses={200: OpenApiResponse(response=OpenApiResponse(),
                                        description='Success',
                                        examples=[
                                                    OpenApiExample(name='Успех',
                                                                   value={"Status": True})
                                                ]
                                        ),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                       OpenApiExample('Не авторизован',
                                      value={'Status': False, 'Error': 'Log in required'}),
                   ])},
    )
    # Редактирование методом POST
    def post(self, request, *args, **kwargs):
        """
            Update the account details of the authenticated user.

            Args:
            - request (Request): The Django request object.

            Returns:
            - JsonResponse: The response indicating the status of the operation and any errors.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        # проверяем обязательные аргументы

        if 'password' in request.data:
            # проверяем пароль на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                request.user.set_password(request.data['password'])

        # проверяем остальные данные
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class LoginAccount(FormView):
    """
    Класс для авторизации пользователей
    """
    # Авторизация методом POST
    template_name = 'login.html'
    form_class = LoginAccountForm
    success_url = 'success'

    def form_valid(self, form):
        form.login()
        return super().form_valid(form)


class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @extend_schema(
        summary="Список категорий",
        description="Возвращает список доступных категорий.",
        responses={200: CategorySerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer

    @extend_schema(
        summary="Список магазинов",
        description="Возвращает список активных магазинов.",
        responses={200: ShopSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ProductInfoView(APIView):
    """
        A class for searching products.

        Methods:
        - get: Retrieve the product information based on the specified filters.

        Attributes:
        - None
        """

    @extend_schema(
        summary="Поиск товаров",
        parameters=[
            OpenApiParameter("shop_id", description="ID магазина"),
            OpenApiParameter("category_id", description="ID категории"),
        ],
        description="Возвращает список товаров, отфильтрованных по магазину и/или категории.",
        responses={200: ProductInfoSerializer(many=True)},
    )
    def get(self, request: Request, *args, **kwargs):
        """
               Retrieve the product information based on the specified filters.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the product information.
               """
        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        # фильтруем и отбрасываем дубликаты
        queryset = ProductInfo.objects.filter(
            query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)


class BasketView(APIView):
    """
    A class for managing the user's shopping basket.

    Methods:
    - get: Retrieve the items in the user's basket.
    - post: Add an item to the user's basket.
    - put: Update the quantity of an item in the user's basket.
    - delete: Remove an item from the user's basket.

    Attributes:
    - None
    """

    @extend_schema(
        summary="Просмотр корзины",
        description="Возвращает содержимое корзины пользователя.",
        responses={200: OrderSerializer(many=True),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Не авторизован',
                                                           value={'Status': False, 'Error': 'Log in required'})
                                        ])},
    )
    # получить корзину
    def get(self, request, *args, **kwargs):
        """
                Retrieve the items in the user's basket.

                Args:
                - request (Request): The Django request object.

                Returns:
                - Response: The response containing the items in the user's basket.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        basket = Order.objects.filter(
            user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Добавление в корзину",
        description="Добавляет товары в корзину пользователя.",
        request=OpenApiRequest(request='request',
                               examples=[
                                   OpenApiExample('post',
                                                  value={'items': [
                                                      {"id": 95, "quantity": 80},
                                                      {"id": 96, "quantity": 1234, }
                                                  ]
                                                  })
                               ]
                               ),
        responses={200: OpenApiResponse(response=OpenApiResponse(),
                                        examples=[
                                            OpenApiExample('Success',
                                                           value={'Status': True, 'Создано объектов': 1}),
                                            OpenApiExample('Не правильное тело запроса',
                                                           value={'Status': False, 'Errors':
                                                               'Неверный формат запроса'}),
                                            OpenApiExample('Data base errors',
                                                           value={'Status': False, 'Errors': 'IntegrityError: '
                                                                                             'Order already exists'}),
                                            OpenApiExample('Serializer errors',
                                                           value={'Status': False, 'Errors':
                                                                  'ValidationError: this item does not exist'}),
                                            OpenApiExample('Необходимые параметры',
                                                           {'Status': False, 'Errors':
                                                                  'Не указаны все необходимые аргументы'})
                                        ]),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Не авторизован',
                                                           value={'Status': False, 'Error': 'Log in required'})
                                        ])},
    )
    # добавить в корзину
    def post(self, request, *args, **kwargs):
        """
               Add an items to the user's basket.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = loads(items_sting)
                print(items_dict)
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
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
                            print(error)
                            return JsonResponse({'Status': False, 'Errors': str(error)})
                        else:
                            objects_created += 1

                    else:

                        return JsonResponse({'Status': False, 'Errors': serializer.errors})

                return JsonResponse({'Status': True, 'Создано объектов': objects_created})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    @extend_schema(
        summary="Удаление товаров из корзины",
        description="Удаляет указанные товары из корзины пользователя. В запросе передаётся параметр "
                    "'items' – строка, содержащая ID товаров, разделённые запятыми.",
        request=OpenApiRequest(request='request',
                               examples=[
                                            OpenApiExample('delete',
                                                           value={'items': '96, 95'})
                                        ]),
        responses={200: OpenApiResponse(response=OpenApiResponse(),
                                        examples=[
                                            OpenApiExample(' Успех',
                                                           value={'Status': True, 'Удалено объектов': 5}),
                                            OpenApiExample('Не все аргументы',
                                                           value={'Status': False, 'Errors': 'Не указаны все'
                                                                                             ' необходимые аргументы'})
                                        ]),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Не авторизован',
                                                           value={'Status': False, 'Error': 'Log in required'})
                                        ])}
    )
    # удалить товары из корзины
    def delete(self, request, *args, **kwargs):
        """
                Remove  items from the user's basket.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    @extend_schema(
        summary="Обновление товаров в корзине",
        description="Обновляет количество товаров в корзине пользователя. В запросе передаётся параметр 'items' – "
                    "JSON-строка, содержащая список объектов с ключами 'id' и 'quantity'.",
        request=OpenApiRequest(request='request',
                               examples=[
                                            OpenApiExample('put',
                                                           value={'items': [
                                                                               { "id": 95, "quantity": 2 },
                                                                               { "id": 96, "quantity": 1, }
                                                                           ]
                                                           })
                                        ]
        ),
        responses={200: OpenApiResponse(response=OpenApiResponse(),
                                        examples=[
                                            OpenApiExample('Успех',
                                                           value={'Status': True, 'Обновлено объектов': 7}),
                                            OpenApiExample('Форма запроса',
                                                           value={'Status': False,
                                                                  'Errors': 'Неверный формат запроса'}),
                                            OpenApiExample('Не всё указано',
                                                           value={'Status': False,
                                                                  'Errors': 'Не указаны все необходимые аргументы'})
                                        ]),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Не авторизован',
                                                           value={'Status': False, 'Error': 'Log in required'})
                                        ])}
    )
    # редактировать позиции в корзине
    def put(self, request, *args, **kwargs):
        """
               Update the items in the user's basket.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = loads(items_sting)
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                for order_item in items_dict:
                    if type(order_item['id']) == int and type(order_item['quantity']) == int:
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity'])

                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerUpdate(APIView):
    """
    A class for updating partner information.

    Methods:
    - post: Update the partner information.

    Attributes:
    - None
    """

    @extend_schema(
        summary="Обновление прайс-листа партнёра",
        description="Обновляет информацию о товарах партнёра, загружая данные по указанному URL. "
                    "В запросе передаётся параметр 'url' – ссылка на YAML-файл с данными.",
        request=OpenApiRequest(request='yml file',
                               examples=[
                                   OpenApiExample('.yaml',
                                                  value=open('../../data/shop_exmpl.yaml')
                                                  ),]),
        responses={200: OpenApiResponse(response=OpenApiResponse(),
                                        examples=[
                                            OpenApiExample('Успех',
                                                           value={'Status': True}),
                                            OpenApiExample('Незаполненные необходимые поля',
                                                           value={'Status': False,
                                                                  'Errors': 'Не указаны все необходимые аргументы'}),
                                            OpenApiExample('serializer errors',
                                                           value={'Status': False, 'Errors':
                                                                  'ValidationError: this item does not exist'}),
                                        ]),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Не авторизован',
                                                           value={'Status': False, 'Error': 'Log in required'}),
                                            OpenApiExample('Только для магазинов',
                                                           value={'Status': False, 'Error': 'Только для магазинов'})
                                        ])
                   }
    )
    def post(self, request, *args, **kwargs):
        """
                Update the partner price list information.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                do_import_task.delay(url, request)
                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerState(APIView):
    """
       A class for managing partner state.

       Methods:
       - get: Retrieve the state of the partner.

       Attributes:
       - None
       """

    @extend_schema(
        summary="Получение статуса партнёра",
        description="Возвращает информацию о текущем статусе магазина партнёра.",
        responses={200: ShopSerializer,
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Нужна авторизация',
                                                           value={'Status': False, 'Error': 'Log in required'}),
                                            OpenApiExample('Только для магазинов',
                                                           value={'Status': False, 'Error': 'Только для магазинов'})
                                        ])}
    )
    # получить текущий статус
    def get(self, request, *args, **kwargs):
        """
               Retrieve the state of the partner.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the state of the partner.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    @extend_schema(
        summary="Изменение статуса партнёра",
        description="Изменяет состояние магазина партнёра. В запросе передаётся параметр 'state', "
                    "значение 'on' означает активное состояние.",
        request=OpenApiRequest(request='post',
                               examples=[
                                    OpenApiExample('request',
                                                   value={'state': 'on'})
                                        ]),
        responses={200: OpenApiResponse(response=OpenApiResponse(),
                                        examples=[
                                            OpenApiExample('Успех',
                                                           value={'Status': True}),
                                            OpenApiExample('Форма запроса',
                                                           value={'Status': False,
                                                                  'Errors': 'Неверный формат запроса'}),
                                            OpenApiExample('Необходимые параметры',
                                                           value={'Status': False,
                                                                  'Errors': 'Не указаны все необходимые аргументы'})
                                        ]),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Нужна авторизация',
                                                           value={'Status': False, 'Error': 'Log in required'}),
                                            OpenApiExample('Только для магазинов',
                                                           value={'Status': False, 'Error': 'Только для магазинов'})
                                        ])}
    )
    # изменить текущий статус
    def post(self, request, *args, **kwargs):
        """
               Update the state of a partner.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        state = request.data.get('state')
        if state:
            try:
                (Shop.objects.filter(user_id=request.user.id)
                 .update(state=(lambda x: True if x == 'on' else False)(state)))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrders(APIView):
    """
    Класс для получения заказов поставщиками
     Methods:
    - get: Retrieve the orders associated with the authenticated partner.

    Attributes:
    - None
    """

    @extend_schema(
        summary="Получение заказов партнёра",
        description="Возвращает заказы, связанные с магазином партнёра (исключая заказы в состоянии 'basket').",
        responses={200: OrderSerializer(many=True),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Нужна авторизация',
                                                           value={'Status': False, 'Error': 'Log in required'}),
                                            OpenApiExample('Только для магазинов',
                                                           value={'Status': False, 'Error': 'Только для магазинов'})
                                        ])}
    )
    def get(self, request, *args, **kwargs):
        """
               Retrieve the orders associated with the authenticated partner.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the orders associated with the partner.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ContactView(APIView):
    """
       A class for managing contact information.

       Methods:
       - get: Retrieve the contact information of the authenticated user.
       - post: Create a new contact for the authenticated user.
       - put: Update the contact information of the authenticated user.
       - delete: Delete the contact of the authenticated user.

       Attributes:
       - None
       """

    @extend_schema(
        summary="Получение контактов пользователя",
        description="Возвращает список контактов авторизованного пользователя.",
        responses={200: ContactSerializer(many=True),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Нужна авторизация',
                                                           value={'Status': False, 'Error': 'Log in required'})
                                        ])}
    )
    # получить мои контакты
    def get(self, request, *args, **kwargs):
        """
               Retrieve the contact information of the authenticated user.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the contact information.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        contact = Contact.objects.filter(
            user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Добавление нового контакта",
        description="Создаёт новый контакт для авторизованного пользователя. "
                    "Обязательные поля: 'city', 'street', 'phone'.",
        request=OpenApiRequest(request='post',
                               examples=[
                                   OpenApiExample('request',
                                                  value={
                                                        "properties": {
                                                            "city": "Berlin",
                                                            "street": "Peetey",
                                                            "phone": "+12345678910"
                                                        },

                                                      "required": ['city', 'street', 'phone']
                                                        })
                               ]),
        responses={200: OpenApiResponse(response=OpenApiResponse(),
                                        examples=[
                                            OpenApiExample('Успех',
                                                           value={'Status': True}),
                                            OpenApiExample('Serializer errors',
                                                           value={'Status': False, 'Errors':
                                                                  'ValidationError: this item already exists'}),
                                            OpenApiExample('Не все необходимые элементы',
                                                           value={'Status': False, 'Errors':
                                                               'Не указаны все необходимые аргументы'})
                                        ]),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Нужна авторизация',
                                                           value={'Status': False, 'Error': 'Log in required'})
                                        ])}
    )
    # добавить новый контакт
    def post(self, request, *args, **kwargs):
        """
               Create a new contact for the authenticated user.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
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
                return JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    @extend_schema(
        summary="Удаление контакта",
        description="Удаляет контакты пользователя. В запросе передаётся параметр "
                    "'items' – строка с ID контактов, разделённых запятыми.",
        request=OpenApiRequest(request='delete',
                               examples=[
                                   OpenApiExample('request',
                                                  value={'items': '1, 2, 6'})
                               ]),
        responses={200: OpenApiResponse(response=OpenApiResponse(),
                                        examples=[
                                            OpenApiExample('Успех',
                                                           value={'Status': True, 'Удалено объектов': 3}),
                                            OpenApiExample('Не все необходимые элементы',
                                                           value={'Status': False, 'Errors':
                                                               'Не указаны все необходимые аргументы'})
                                        ]),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Нужна авторизация',
                                                           value={'Status': False, 'Error': 'Log in required'})
                                        ])}
    )
    # удалить контакт
    def delete(self, request, *args, **kwargs):
        """
               Delete the contact of the authenticated user.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(user_id=request.user.id, id=contact_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    @extend_schema(
        summary="Обновление контакта",
        description="Обновляет данные контакта пользователя. "
                    "В запросе обязательно должен присутствовать параметр 'id' (числовой ID контакта).",
        request=OpenApiRequest(request='put',
                               examples=[
                                   OpenApiExample('request',
                                                  value={
                                                      "properties": {
                                                          "id": 3,
                                                          "house": 67,
                                                          "building": 1,
                                                          "phone": "87654321098"
                                                      },

                                                      "required": ['id']
                                                  })
                               ]),
        responses={200: OpenApiResponse(response=OpenApiResponse(),
                                        examples=[
                                            OpenApiExample('Успех',
                                                           value={'Status': True}),
                                            OpenApiExample('Serializer errors',
                                                           value={'Status': False, 'Errors':
                                                               'ValidationError: this contact does not exist'}),
                                            OpenApiExample('Не все необходимые элементы',
                                                           value={'Status': False, 'Errors':
                                                               'Не указаны все необходимые аргументы'})
                                        ]),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Нужна авторизация',
                                                           value={'Status': False, 'Error': 'Log in required'})
                                        ])}
    )
    # редактировать контакт
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            """
                   Update the contact information of the authenticated user.

                   Args:
                   - request (Request): The Django request object.

                   Returns:
                   - JsonResponse: The response indicating the status of the operation and any errors.
                   """
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
                        return JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class OrderView(APIView):
    """
    Класс для получения и размещения заказов пользователями
    Methods:
    - get: Retrieve the details of a specific order.
    - post: Create a new order.
    - put: Update the details of a specific order.
    - delete: Delete a specific order.

    Attributes:
    - None
    """

    @extend_schema(
        summary="Получение заказов пользователя",
        description="Возвращает список заказов пользователя, исключая корзину (state='basket').",
        responses={200: OrderSerializer(many=True),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Необходима авторизация',
                                                           value={'Status': False, 'Error': 'Log in required'})
                                        ])}
    )
    # получить мои заказы
    def get(self, request, *args, **kwargs):
        """
               Retrieve the details of user orders.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the details of the order.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        order = Order.objects.filter(
            user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Размещение заказа",
        description="Переводит заказ из состояния 'basket' в 'new' и отправляет уведомление. "
                    "В запросе передаются параметры 'id' (ID заказа) и 'contact' (ID контакта).",
        request=OpenApiRequest(request='post',
                               examples=[
                                   OpenApiExample('request',
                                                  value={
                                                      "id": 7,
                                                      "contact": 1,
                                                      "required": ["id", "contact"]
                                                  })
                               ]),
        responses={200: OpenApiResponse(response=OpenApiResponse(),
                                        examples=[
                                            OpenApiExample('Успех',
                                                           value={'Status': True}),
                                            OpenApiExample('Незаполненны необходимые поля',
                                                           value={'Status': False,
                                                                  'Errors': 'Не указаны все необходимые аргументы'}),
                                            OpenApiExample('Не правильные аргументы',
                                                           value={'Status': False,
                                                                  'Errors': 'Неправильно указаны аргументы'}),
                                        ]),
                   403: OpenApiResponse(response=OpenApiResponse(),
                                        description='Error: Forbidden',
                                        examples=[
                                            OpenApiExample('Не авторизован',
                                                           value={'Status': False, 'Error': 'Log in required'})
                                        ])
                   }
    )
    # разместить заказ из корзины
    def post(self, request, *args, **kwargs):
        """
               Put an order and send a notification.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'id', 'contact'}.issubset(request.data):
            if request.data['id'].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data['id']).update(
                        contact_id=request.data['contact'],
                        state='new')
                except IntegrityError:
                    return JsonResponse({'Status': False, 'Errors': 'Неправильно указаны аргументы'})
                else:
                    if is_updated:
                        new_order_task.delay(user_id=request.user.id)
                        return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

class HomeView(APIView):
    """
    Class for having a cool picture on the main page.
    """
    def get(self, request, *args, **kwargs):
        return render(request, 'main.html')


class ResetPasswordFormView(FormView):
    """
    Class for resetting password
    """
    template_name = 'reset_password.html'
    form_class = ResetPasswordForm
    success_url = 'success'

    def form_valid(self, form):
        form.send_reset_token()
        return super().form_valid(form)


class SuccessView(TemplateView):
    """
    Class for success page
    """
    template_name = 'success.html'


class RegisterAccountView(FormView):
    """
    Class for signing up users
    """
    template_name = 'register.html'
    form_class = RegisterAccountForm
    success_url = 'login'

    @extend_schema(
        responses={200, "Success"}
    )
    def form_valid(self, form):
        form.send_reg_token()
        return super().form_valid(form)
