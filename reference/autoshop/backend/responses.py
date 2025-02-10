from drf_spectacular.utils import OpenApiExample

EMAIL_CONFIRMATION_RESPONSE_EXAMPLES = OpenApiExample(
    name='EMAIL_CONFIRMATION_RESPONSE_EXAMPLES',
    status_codes=[200, 402, 403],
    response_only=True,
    value=[
        {
            'Status': True,
        },
        {
            'Status': False,
            'Errors': 'Неправильно указан токен или email'
        },
        {
            'Status': False,
            'Errors': 'Не указаны все необходимые аргументы'
        }
    ]
)