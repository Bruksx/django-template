from accounts.models import Country, Industry, User, Talent
from accounts.views.admin import router as admin_router
from core.views import router, root_router
from django.test import TestCase
from factories import StateFactory, CityFactory
from ninja.testing import TestClient
from ninja_jwt.authentication import JWTAuth

from apps.factories import UserFactory


# Create your tests here.

class CommonListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.country = Country.objects.first()
        self.industry = Industry.objects.first()
        self.user_data = dict(
            first_name="Test",
            last_name="User",
            email="testuser@example.com",
            password="securepassword",
        )
        self.user = User.objects.create_user(**self.user_data)
        self.talent = Talent.objects.create(
            user=self.user,
            country=self.country
        )
        self.auth = JWTAuth()
        self.auth.authenticate = lambda r: self.user

    def test_currency_list_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/currencies", headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_language_list_endpoint(self):
        headers = {
            "authorization": f"bearer {self.user.token}"
        }
        response = self.client.get("/languages", headers=headers)
        self.assertEqual(response.status_code, 200)


class StateListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.country = Country.objects.first()
        self.state1 = StateFactory.create(country=self.country)
        self.state2 = StateFactory.create(country=self.country)

    def test_state_list_success(self):
        response = self.client.get(f"/states?country={self.country.uid}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_state_list_with_search(self):
        response = self.client.get(f"/states?country={self.country.uid}&search={self.state1.name[:5]}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_state_list_unauthorized(self):
        # Note: /states endpoint doesn't require auth, this tests that auth is optional
        response = self.client.get(f"/states?country={self.country.uid}")
        self.assertEqual(response.status_code, 200)


class CityListTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.country = Country.objects.first()
        self.state = StateFactory.create(country=self.country)
        self.city1 = CityFactory.create(state=self.state)
        self.city2 = CityFactory.create(state=self.state)

    def test_city_list_success(self):
        response = self.client.get(f"/cities?state={self.state.uid}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_city_list_with_search(self):
        response = self.client.get(f"/cities?state={self.state.uid}&search={self.city1.name[:5]}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)


class WellKnownTests(TestCase):
    def setUp(self):
        self.client = TestClient(root_router)

    def test_get_well_known_file_success(self):
        response = self.client.get("/apple-app-site-association")
        self.assertEqual(response.status_code, 200)

    def test_get_well_known_file_not_found(self):
        response = self.client.get("/nonexistent-file.json")
        self.assertEqual(response.status_code, 404)


class CollectMetricsTests(TestCase):
    def setUp(self):
        self.client = TestClient(router)
        self.user = UserFactory()

    def test_collect_metrics_success(self):
        payload = {
            "path": "/test-page",
            "duration": 1.5
        }

        response = self.client.post("/metrics", json=payload, headers={"Authorization": f"Bearer {self.user.token}"})
        self.assertEqual(response.status_code, 200)

    def test_collect_metrics_missing_fields(self):
        payload = {
            "path": "/test-page"
            # missing duration
        }
        response = self.client.post("/metrics", json=payload, headers={"Authorization": f"Bearer {self.user.token}"})
        self.assertEqual(response.status_code, 422)


    def test_unauthenticated_collect_metrics(self):
        payload = {
            "path": "/test-page",
            "duration": 1.5
        }

        response = self.client.post("/metrics", json=payload)
        self.assertEqual(response.status_code, 401)

