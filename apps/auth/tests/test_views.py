from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.auth.views import router
from ninja.testing import TestClient


User = get_user_model()

class LoginEndpointTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.login_url = '/login'

    def test_login_successful(self):
        User.objects.create_user(email='testuser@example.com', password='securepassword')
        
        data = {
            'email': 'testuser@example.com',
            'password': 'securepassword'
        }
        response = self.client.post(self.login_url, json=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['email'], 'testuser@example.com')

    def test_login_unsuccessful_with_wrong_password(self):
        User.objects.create_user(email='testuser@example.com', password='securepassword')
        
        data = {
            'email': 'testuser@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, json=data, content_type='application/json')
        
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['detail'], 'Invalid Credentials')

    def test_login_unsuccessful_with_non_existent_user(self):
        data = {
            'email': 'nonexistentuser@example.com',
            'password': 'any_password'
        }
        response = self.client.post(self.login_url, json=data, content_type='application/json')
        
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['detail'], 'Invalid Credentials')



