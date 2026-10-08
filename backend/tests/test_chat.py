import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

class ChatTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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

    def test_chat_authorized_fallback_flow(self):
        # 1. Register and login
        reg_payload = {
            "name": "Pushpak Bajanghate",
            "email": "pushpak@example.com",
            "phone": "+91-9823011223",
            "password": "securepassword123"
        }
        self.client.post("/auth/register", json=reg_payload)

        login_res = self.client.post("/auth/login", json={
            "email": "pushpak@example.com",
            "password": "securepassword123"
        })
        token = login_res.json()["access_token"]
        customer_id = login_res.json()["customer"]["id"]

        # 2. Send chat message (when API key is empty or default)
        headers = {"Authorization": f"Bearer {token}"}
        chat_payload = {"message": "Where is my order #1?"}
        chat_res = self.client.post("/chat", json=chat_payload, headers=headers)

        self.assertEqual(chat_res.status_code, 200)
        data = chat_res.json()
        self.assertEqual(data["customer_id"], customer_id)
        self.assertEqual(data["customer_name"], "Pushpak Bajanghate")
        self.assertIn("Pushpak Bajanghate", data["response"])
        self.assertIn("Where is my order #1?", data["response"])
        self.assertIn("timestamp", data)

    @patch("app.services.llm.get_llm")
    def test_chat_live_llm_invocation(self, mock_get_llm):
        # Mock LLM instance returning an AIMessage-like response
        mock_llm_instance = MagicMock()
        mock_ai_message = MagicMock()
        mock_ai_message.content = "I would be happy to help you with your order status!"
        mock_llm_instance.invoke.return_value = mock_ai_message
        mock_get_llm.return_value = mock_llm_instance

        # Register and login
        reg_payload = {
            "name": "Virat Kohli",
            "email": "virat@example.com",
            "phone": "+91-9811122233",
            "password": "securepassword123"
        }
        self.client.post("/auth/register", json=reg_payload)
        login_res = self.client.post("/auth/login", json={
            "email": "virat@example.com",
            "password": "securepassword123"
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Send chat message
        chat_res = self.client.post("/chat", json={"message": "Can I cancel my recent order?"}, headers=headers)
        self.assertEqual(chat_res.status_code, 200)
        data = chat_res.json()
        self.assertEqual(data["response"], "I would be happy to help you with your order status!")

        # Verify LLM invoke was called with SystemMessage and HumanMessage containing customer context
        self.assertTrue(mock_llm_instance.invoke.called)
        called_messages = mock_llm_instance.invoke.call_args[0][0]
        self.assertEqual(len(called_messages), 2)
        # Check system prompt contents
        self.assertIn("Virat Kohli", called_messages[0].content)
        self.assertIn("customer-support assistant", called_messages[0].content)
        # Check user message contents
        self.assertEqual(called_messages[1].content, "Can I cancel my recent order?")

    def test_chat_unauthorized(self):
        # Missing auth header
        chat_payload = {"message": "Can I return my item?"}
        res = self.client.post("/chat", json=chat_payload)
        self.assertEqual(res.status_code, 401)

        # Invalid token
        bad_res = self.client.post(
            "/chat",
            json=chat_payload,
            headers={"Authorization": "Bearer invalid.jwt.token"}
        )
        self.assertEqual(bad_res.status_code, 401)

    def test_chat_empty_message_validation(self):
        # Register and login
        reg_payload = {
            "name": "Harvey Specter",
            "email": "harvey@example.com",
            "phone": "+91-9822233344",
            "password": "securepassword123"
        }
        self.client.post("/auth/register", json=reg_payload)
        login_res = self.client.post("/auth/login", json={
            "email": "harvey@example.com",
            "password": "securepassword123"
        })
        token = login_res.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        # Empty message
        bad_chat = self.client.post("/chat", json={"message": ""}, headers=headers)
        self.assertEqual(bad_chat.status_code, 422)

if __name__ == "__main__":
    unittest.main()
