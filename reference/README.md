## **Запустить проект**

1. Ввести пароли и ключи в `settings.py`

2. Установить зависимости:
```bash
pip install -r requirements.txt
```
3. Сменить директорию, сделать миграции и запустить сервер:
```bash
cd autoshop
python manage.py migrate
python manage.py runserver
```
4. Подключить redis и celery:
```bash
redis-server
celery -A autoshop worker
```

## **Запустить тесты**

```bash
export DJANGO_SETTINGS_MODULE=autoshop.settings
pytest backend/tests.py
```
