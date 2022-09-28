from django.urls import reverse, path, include
from rest_framework.test import APIClient, APITestCase, URLPatternsTestCase

from backend.models import User


from pprint import pprint


# def create_buyer():
#     buyer = User(email='testbuyer@gmail.com', password='test', type='buyer')
#     buyer.save()
#
# def create_shop_user():
#     shop_user = User(email='testshop@gmail.com', password='test', type='shop')
#     shop_user.save()


class RegisterAccountTests(APITestCase):

    url = reverse('backend:user-register')
    register_data = {'email': 'testbuyer@gmail.com',
                     'password': 'TestPassword1',
                     'first_name': 'Test',
                     'last_name': 'Test',
                     'company': 'TestCompany',
                     'position': 'TestPosition'}

    def test_user_registration_correct(self):
        data = self.register_data.copy()
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is not None
        assert User.objects.filter(email=data['email']).first().first_name == data['first_name'] and \
               User.objects.filter(email=data['email']).first().first_name == data['last_name']

    def test_user_registration_no_company(self):
        data = self.register_data.copy()
        data.pop('company')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_email(self):
        data = self.register_data.copy()
        data.pop('email')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(first_name=data['first_name'], last_name=data['last_name'],
                                   company=data['company'], position=data['position']).first() is None

    def test_user_registration_no_first_name(self):
        data = self.register_data.copy()
        data.pop('first_name')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_last_name(self):
        data = self.register_data.copy()
        data.pop('last_name')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_position(self):
        data = self.register_data.copy()
        data.pop('position')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_no_password(self):
        data = self.register_data.copy()
        data.pop('password')
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None

    def test_user_registration_invalid_password(self):
        data = self.register_data.copy()
        data['password'] = '1'
        response = self.client.post(self.url, data)
        assert response.status_code == 200
        assert User.objects.filter(email=data['email']).first() is None


# class ConfirmAccountTests(APITestCase):
#
#     def setUp(self):
#