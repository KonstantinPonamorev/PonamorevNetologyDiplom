from django.urls import reverse, path, include
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase, URLPatternsTestCase

from backend.models import User, ConfirmEmailToken


register_data = {'email': 'testbuyer@gmail.com',
                 'password': 'TestPassword1',
                 'first_name': 'Test',
                 'last_name': 'Test',
                 'company': 'TestCompany',
                 'position': 'TestPosition'}

def create_user():
    buyer = User(email=register_data['email'],
                 password=register_data['password'],
                 first_name=register_data['first_name'],
                 last_name=register_data['last_name'],
                 company=register_data['company'],
                 position=register_data['position'])
    buyer.save()
    return buyer

def log_in_user(user, APIClient):
    user.is_active = True
    user.save()
    token, _ = Token.objects.get_or_create(user=user)
    APIClient.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
#
# def create_shop_user():
#     shop_user = User(email='testshop@gmail.com', password='test', type='shop')
#     shop_user.save()


class RegisterAccountTests(APITestCase):

    url = reverse('backend:user-register')


    def test_user_registration_correct(self):
        data = register_data.copy()
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is not None
        assert User.objects.filter(email=data['email']).first().first_name == data['first_name'] and \
               User.objects.filter(email=data['email']).first().first_name == data['last_name']

    def test_user_registration_no_company(self):
        data = register_data.copy()
        data.pop('company')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_email(self):
        data = register_data.copy()
        data.pop('email')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(first_name=data['first_name'], last_name=data['last_name'],
                                   company=data['company'], position=data['position']).first() is None

    def test_user_registration_no_first_name(self):
        data = register_data.copy()
        data.pop('first_name')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_last_name(self):
        data = register_data.copy()
        data.pop('last_name')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_position(self):
        data = register_data.copy()
        data.pop('position')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_password(self):
        data = register_data.copy()
        data.pop('password')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_invalid_password(self):
        data = register_data.copy()
        data['password'] = '1'
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None


class ConfirmAccountTests(APITestCase):

    url = reverse('backend:user-register-confirm')

    def test_confirm_token_correct(self):
        user = create_user()
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
        data = {'email': user.email,
                'token': token.key}
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert ConfirmEmailToken.objects.filter(user_id=user.id).first() is None
        assert User.objects.filter(id=user.id).first().is_active == True


    def test_confirm_token_uncorrect_token(self):
        user = create_user()
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
        data = {'email': user.email,
                'token': '123'}
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert ConfirmEmailToken.objects.filter(user_id=user.id).first() is not None
        assert User.objects.filter(id=user.id).first().is_active == False

    def test_confirm_token_uncorrect_email(self):
        user = create_user()
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
        data = {'email': 'mail@gmail.com',
                'token': token.key}
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert ConfirmEmailToken.objects.filter(user_id=user.id).first() is not None
        assert User.objects.filter(id=user.id).first().is_active == False


class AccountDetailsTests(APITestCase):

    url = reverse('backend:user-details')

    def test_view_account_details_correct(self):
        user = create_user()
        log_in_user(user, self.client)
        response = self.client.get(self.url)
        assert response.status_code == 200

    def test_view_account_details_unauthenticated(self):
        response = self.client.get(self.url)
        assert response.status_code == 403

    def test_edit_account_details_unathenticated(self):
        response = self.client.post(self.url)
        assert response.status_code == 403

    def test_edit_account_details_names_coorect(self):
        data = {
            'first_name': 'new_test',
            'last_name': 'new_test',
        }
        user = create_user()
        log_in_user(user, self.client)
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=user.email).first().first_name == data['first_name'] and \
               User.objects.filter(email=user.email).first().last_name == data['last_name']

    def test_edit_account_details_work_correct(self):
        data = {
            'company': 'new_company',
            'position': 'new_positiob'
        }
        user = create_user()
        log_in_user(user, self.client)
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=user.email).first().company == data['company'] and \
               User.objects.filter(email=user.email).first().position == data['position']

    def test_edit_account_details_unexpected_argument(self):
        data = {
            'new_argument': 'argument',
            'email': 'new_email',
        }
        user = create_user()
        log_in_user(user, self.client)
        response = self.client.post(self.url, data)
        assert response.status_code == 400
        assert User.objects.filter(email=user.email).first().email != data['email']

    def test_edit_account_details_invalid_password(self):
        data = {
            'password': '1',
        }
        user = create_user()
        log_in_user(user, self.client)
        response = self.client.post(self.url, data)
        assert response.status_code == 400
        assert User.objects.filter(email=user.email).first().password != data['password']


class LoginAccountTests(APITestCase):

    url = reverse('backend:user-login')

    # def test_correct_login(self):
    #     data = {
    #         'email': register_data['email'],
    #         'password': register_data['password'],
    #     }
    #     user = create_user()
    #     user.is_active = True
    #     user.save()
    #     response = self.client.post(self.url, data)
    #     assert response.status_code == 200
    #     # assert Token.objects.filter(user=user.id).first() is not None

