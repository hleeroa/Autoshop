import os
import django
import yaml
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from backend.models import User, ConfirmEmailToken
from json import dumps

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autoshop.settings')
django.setup()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def authenticated_user():
    user = User.objects.create_user(first_name="testuser", email="testuser@example.com", password="testpass")
    return user


@pytest.mark.django_db
class TestConfirmAccount:
    def test_confirm_account_success(self, api_client):
        """
        Verifies successful account confirmation when a valid email and token are provided.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        """
        user = User.objects.create_user(username="user", email="user@example.com", is_active=False)
        ConfirmEmailToken.objects.create(user=user, key="testtoken")
        url = reverse("backend:user-register-confirm")
        data = {"email": "user@example.com", "token": "testtoken"}

        response = api_client.post(url, data)
        user.refresh_from_db()

        assert response.status_code == 200
        assert user.is_active is True
        assert not ConfirmEmailToken.objects.filter(key="testtoken").exists()

    def test_confirm_account_missing_params(self, api_client):
        """
        Checks the behavior when required parameters are missing for account confirmation.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests.
        :return:
        """
        url = reverse("backend:user-register-confirm")
        response = api_client.post(url, {})
        assert response.status_code == 200
        assert response.json() == {"Status": False, "Errors": "Не указаны все необходимые аргументы"}

    def test_confirm_account_wrong_params(self, api_client):
        """
        Verifies the Error when the required parameter is wrong for account confirmation.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests.
        :return:
        """
        user = User.objects.create_user(username="user", email="user@example.com", is_active=False)
        ConfirmEmailToken.objects.create(user=user, key="testtoken")
        data = {"email": "wrong@address.om", "token": "testtoken"}

        url = reverse("backend:user-register-confirm")
        response = api_client.post(url, data)
        assert response.status_code == 200
        assert response.json() == {'Status': False, 'Errors': 'Неправильно указан токен или email'}


@pytest.mark.django_db
class TestAccountDetails:
    def test_get_authenticated(self, api_client, authenticated_user):
        """
        Verifies the retrieval of account details for an authenticated user.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :param authenticated_user: a user with predefined credentials (first_name, email, password)
        :return:
        """
        api_client.force_authenticate(user=authenticated_user)
        url = reverse("backend:user-details")

        response = api_client.get(url)

        assert response.status_code == 200
        assert response.data["first_name"] == "testuser"

    def test_get_unauthenticated(self, api_client):
        """
        Verifies that unauthenticated users cannot access account details and receive a 403 error.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :return:
        """
        url = reverse("backend:user-details")

        response = api_client.get(url)

        assert response.status_code == 403
        assert response.json() == {"Status": False, "Error": "Log in required"}

    def test_too_easy_password(self, api_client):
        """
        Checks error when trying to set too simple password.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :return:
        """
        user = User.objects.create_user(username="user", email="user@example.com")
        ConfirmEmailToken.objects.create(user=user, key="testtoken")
        api_client.force_authenticate(user)

        data = {"password": "123"}
        url = reverse("backend:user-details")

        response = api_client.post(url, data)

        assert response.status_code == 200
        assert ('password' in response.json()["Errors"])


@pytest.mark.django_db
class TestCategoryView:
    def test_get_categories(self, api_client):
        """
        Verifies the retrieval of category data from the API.
        Ensures the response contains a dictionary of categories.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :return:
        """
        url = reverse("backend:categories")

        response = api_client.get(url)

        assert response.status_code == 200
        assert isinstance(response.data, dict)


@pytest.mark.django_db
class TestShopView:
    def test_get_shops(self, api_client):
        """
        Tests if the API returns a list of shops successfully.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :return:
        """
        url = reverse("backend:shops")

        response = api_client.get(url)

        assert response.status_code == 200
        assert isinstance(response.data, list)


@pytest.mark.django_db
class TestProductInfoView:
    def test_get_products(self, api_client):
        """
        Checks if the API returns product information as a list.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :return:
        """
        url = reverse("backend:shops")

        response = api_client.get(url)

        assert response.status_code == 200
        assert isinstance(response.data, list)


@pytest.mark.django_db
class TestBasketView:
    def test_add_to_basket_authenticated(self, api_client, authenticated_user):
        """
        Tests adding items to the basket by an authenticated user.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :param authenticated_user: a user with predefined credentials (first_name, email, password)
        :return:
        """
        api_client.force_authenticate(user=authenticated_user)
        url = reverse("backend:basket")
        items = [{"product_info": 1, "quantity": 2}]
        data = {"items": dumps(items)}

        response = api_client.post(url, data)
        print(f'{response=}')

        assert response.status_code in [200, 201]


@pytest.mark.django_db
class TestPartnerUpdate:
    def test_partner_update_authenticated(self, api_client, authenticated_user):
        """
        Checks adding new items as a shop with a YAML file.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :param authenticated_user: a user with predefined credentials (first_name, email, password)
        :return:
        """
        authenticated_user.type = "shop"
        authenticated_user.save()
        api_client.force_authenticate(user=authenticated_user)
        url = reverse("backend:partner-update")
        file = open("../../data/shop1.yaml", "r").read()
        data = yaml.load(file, Loader=yaml.SafeLoader)

        response = api_client.post(url, data)

        assert response.status_code == 200 or response.status_code == 403


@pytest.mark.django_db
class TestContactView:
    def test_get_contacts_authenticated(self, api_client, authenticated_user):
        """
        Verifies that authenticated users can retrieve their contact list.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :param authenticated_user: a user with predefined credentials (first_name, email, password)
        :return:
        """
        api_client.force_authenticate(user=authenticated_user)
        url = reverse("backend:user-contact")

        response = api_client.get(url)

        assert response.status_code == 200
        assert isinstance(response.data, list)

    def test_add_contact_authenticated(self, api_client, authenticated_user):
        """
        Tests the creation of a new contact by an authenticated user.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :param authenticated_user: a user with predefined credentials (first_name, email, password)
        :return:
        """
        api_client.force_authenticate(user=authenticated_user)
        url = reverse("backend:user-contact")
        data = {"city": "City", "street": "Street", "phone": "123456789"}

        response = api_client.post(url, data)

        assert response.status_code == 200


@pytest.mark.django_db
class TestOrderView:
    def test_get_orders_authenticated(self, api_client, authenticated_user):
        """
        Confirms that authenticated users can retrieve their order history as a list.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :param authenticated_user: a user with predefined credentials (first_name, email, password)
        :return:
        """
        api_client.force_authenticate(user=authenticated_user)
        url = reverse("backend:order")

        response = api_client.get(url)

        assert response.status_code == 200
        assert isinstance(response.data, list)

    def test_place_order_authenticated(self, api_client, authenticated_user):
        """
        Tests the placement of an order by an authenticated user.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :param authenticated_user: a user with predefined credentials (first_name, email, password)
        :return:
        """
        api_client.force_authenticate(user=authenticated_user)
        url = reverse("backend:order")
        data = {"id": 1, "contact": 1}

        response = api_client.post(url, data)

        assert response.status_code in [200, 201]


@pytest.mark.django_db
class TestHomeView:
    def test_home_view(self, api_client):
        """
        Ensures the home view returns a successful response.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :return:
        """
        url = reverse("backend:success")

        response = api_client.get(url)

        assert response.status_code == 200


@pytest.mark.django_db
class TestResetPasswordFormView:
    def test_reset_password_view(self, api_client):
        """
        Tests if the password reset endpoint is accessible.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :return:
        """
        url = reverse("backend:password-reset")

        response = api_client.get(url)

        assert response.status_code == 200


@pytest.mark.django_db
class TestRegisterAccountView:
    def test_register_account_view(self, api_client):
        """
        Verifies that the user registration endpoint is accessible.
        :param api_client: an instance of APIClient. Is used to make HTTP requests in tests
        :return:
        """
        url = reverse("backend:user-register")

        response = api_client.get(url)

        assert response.status_code == 200
