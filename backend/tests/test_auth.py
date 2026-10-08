import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import Customer
from app.services.auth import hash_password

class AuthTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # In-memory SQLite with StaticPool so all threads/sessions share the same DB
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        cls.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=cls.engine
        )

        def override_get_db():
            db = cls.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    def setUp(self):
        Base.metadata.create_all(bind=self.engine)

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)

    def test_01_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("environment", data)

    def test_02_register_customer_success(self):
        payload = {
            "name": "Pushpak Bajanghate",
            "email": "pushpak.bajanghate@example.com",
            "phone": "+91-9823011223",
            "password": "password123"
        }
        response = self.client.post("/auth/register", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["name"], "Pushpak Bajanghate")
        self.assertEqual(data["email"], "pushpak.bajanghate@example.com")
        self.assertEqual(data["phone"], "+91-9823011223")
        self.assertIn("id", data)
        # Verify passwords and hashes are never returned
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)

    def test_03_register_customer_duplicate_email(self):
        payload = {
            "name": "Pushpak Bajanghate",
            "email": "pushpak.bajanghate@example.com",
            "phone": "+91-9823011223",
            "password": "password123"
        }
        res1 = self.client.post("/auth/register", json=payload)
        self.assertEqual(res1.status_code, 201)

        res2 = self.client.post("/auth/register", json=payload)
        self.assertEqual(res2.status_code, 400)
        self.assertIn("already exists", res2.json()["detail"])

    def test_04_register_customer_validation_error(self):
        payload = {
            "name": "P",  # too short
            "email": "invalid-email-string",
            "phone": "123",
            "password": "123"  # too short
        }
        response = self.client.post("/auth/register", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_05_login_success_and_get_me(self):
        # 1. Register
        reg_payload = {
            "name": "Virat Kohli",
            "email": "virat.kohli@example.com",
            "phone": "+91-9811122233",
            "password": "champions_password"
        }
        reg_res = self.client.post("/auth/register", json=reg_payload)
        self.assertEqual(reg_res.status_code, 201)
        customer_id = reg_res.json()["id"]

        # 2. Login
        login_payload = {
            "email": "virat.kohli@example.com",
            "password": "champions_password"
        }
        login_res = self.client.post("/auth/login", json=login_payload)
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.json()
        self.assertIn("access_token", login_data)
        self.assertEqual(login_data["token_type"], "bearer")
        self.assertEqual(login_data["customer"]["id"], customer_id)

        token = login_data["access_token"]

        # 3. Access /auth/me with Bearer token
        headers = {"Authorization": f"Bearer {token}"}
        me_res = self.client.get("/auth/me", headers=headers)
        self.assertEqual(me_res.status_code, 200)
        me_data = me_res.json()
        self.assertEqual(me_data["id"], customer_id)
        self.assertEqual(me_data["email"], "virat.kohli@example.com")
        self.assertEqual(me_data["name"], "Virat Kohli")

    def test_06_login_invalid_password(self):
        reg_payload = {
            "name": "Pranav Tapdiya",
            "email": "pranav.tapdiya@example.com",
            "phone": "+91-9876543210",
            "password": "correct_password"
        }
        self.client.post("/auth/register", json=reg_payload)

        login_payload = {
            "email": "pranav.tapdiya@example.com",
            "password": "wrong_password"
        }
        login_res = self.client.post("/auth/login", json=login_payload)
        self.assertEqual(login_res.status_code, 401)
        self.assertIn("Invalid email or password", login_res.json()["detail"])

    def test_07_login_nonexistent_user(self):
        login_payload = {
            "email": "unknown@example.com",
            "password": "some_password"
        }
        login_res = self.client.post("/auth/login", json=login_payload)
        self.assertEqual(login_res.status_code, 401)

    def test_08_get_me_unauthorized(self):
        # Missing token
        res_missing = self.client.get("/auth/me")
        self.assertEqual(res_missing.status_code, 401)

        # Malformed token
        res_bad = self.client.get("/auth/me", headers={"Authorization": "Bearer invalid.jwt.token"})
        self.assertEqual(res_bad.status_code, 401)

if __name__ == "__main__":
    unittest.main()
