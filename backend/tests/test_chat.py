"""Unit tests for the Chat API endpoint — backward compatibility suite.

These tests verify that the chat endpoint still behaves correctly after
the Phase 5 Router Agent upgrade. They mock the entire LangGraph graph
to isolate the API contract from LLM inference.
"""

import json
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
            poolclass=StaticPool,
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

    def _register_and_login(self, name, email):
        self.client.post("/auth/register", json={
            "name": name, "email": email,
            "phone": "+91-9800000000", "password": "securepassword123",
        })
        login_res = self.client.post("/auth/login", json={
            "email": email, "password": "securepassword123",
        })
        return login_res.json()["access_token"], login_res.json()["customer"]["id"]

    @patch("app.agents.router.get_llm")
    @patch("app.agents.conversational.get_llm")
    def test_chat_dynamic_llm_invocation(self, mock_conv_llm, mock_router_llm):
        """
        Verifies that:
        1. The Router LLM is invoked with the actual user message
        2. The response contains the correct structure including router info
        3. customer_id and customer_name are from the authenticated token
        """
        router_json = json.dumps({
            "intent": "ORDER_RETURN",
            "confidence": 0.93,
            "needs_clarification": False,
            "required_information": [],
            "acknowledgement": "I would be happy to help you with your order status!",
        })
        mock_router_instance = MagicMock()
        mock_router_instance.invoke.return_value = MagicMock(content=router_json)
        mock_router_llm.return_value = mock_router_instance

        mock_conv_instance = MagicMock()
        mock_conv_llm.return_value = mock_conv_instance

        token, customer_id = self._register_and_login("Virat Kohli", "virat@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        chat_res = self.client.post(
            "/chat",
            json={"message": "Can I return my shoes?"},
            headers=headers,
        )
        self.assertEqual(chat_res.status_code, 200)
        data = chat_res.json()

        # Response should include the router's acknowledgement
        self.assertIn("response", data)
        self.assertTrue(len(data["response"]) > 0)

        # Router info should be present
        self.assertIn("router", data)
        self.assertEqual(data["router"]["intent"], "ORDER_RETURN")

        # Customer fields
        self.assertEqual(data["customer_id"], customer_id)
        self.assertEqual(data["customer_name"], "Virat Kohli")

        # Router LLM was called with actual message
        self.assertTrue(mock_router_instance.invoke.called)
        messages = mock_router_instance.invoke.call_args[0][0]
        self.assertEqual(messages[1].content, "Can I return my shoes?")
        # Router system prompt should contain intent-routing related text
        self.assertIn("Intent Router Agent", messages[0].content)

    @patch("app.config.settings.LLM_API_KEY", "")
    def test_chat_missing_api_key_returns_500(self):
        token, _ = self._register_and_login("Pushpak Bajanghate", "pushpak@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        res = self.client.post("/chat", json={"message": "Hello"}, headers=headers)
        self.assertEqual(res.status_code, 500)
        self.assertIn("LLM_API_KEY is not configured", res.json()["detail"])

    @patch("app.agents.router.get_llm")
    def test_chat_gemini_api_failure_gracefully_handled(self, mock_router_llm):
        """
        When the Router LLM fails completely, the graph returns UNKNOWN intent
        with an error state. The endpoint responds with 200 (UNKNOWN) or 502.
        """
        mock_router_instance = MagicMock()
        mock_router_instance.invoke.side_effect = RuntimeError("Connection timeout to Gemini")
        mock_router_llm.return_value = mock_router_instance

        token, _ = self._register_and_login("Pranav Tapdiya", "pranav@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        res = self.client.post("/chat", json={"message": "Hello"}, headers=headers)
        # Router node handles errors gracefully (UNKNOWN state) or propagates 502
        self.assertIn(res.status_code, [200, 502])

    def test_chat_unauthorized(self):
        res = self.client.post("/chat", json={"message": "Can I return my item?"})
        self.assertEqual(res.status_code, 401)

        bad_res = self.client.post(
            "/chat",
            json={"message": "Can I return my item?"},
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        self.assertEqual(bad_res.status_code, 401)

    def test_chat_empty_message_validation(self):
        token, _ = self._register_and_login("Harvey Specter", "harvey@example.com")
        headers = {"Authorization": f"Bearer {token}"}
        bad_chat = self.client.post("/chat", json={"message": ""}, headers=headers)
        self.assertEqual(bad_chat.status_code, 422)


if __name__ == "__main__":
    unittest.main()
