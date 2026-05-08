from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import LoginToken, UserSetting, WxUser
from apps.users.services import login_with_code


class UserSettingsTests(TestCase):
    def setUp(self):
        self.user = WxUser.objects.create(openid="test_openid_001", nickname="Tester")
        self.token = LoginToken.issue_for_user(self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.token}")

    def test_settings_include_personalized_rag_fields(self):
        response = self.client.get("/api/v1/users/settings")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertIn("personalized_rag_enabled", payload)
        self.assertIn("personalized_rag_status", payload)
        self.assertIn("personalized_rag_chunk_count", payload)

    def test_rebuild_personalized_rag_requires_opt_in(self):
        response = self.client.post("/api/v1/users/settings/personalized-rag/rebuild")
        self.assertEqual(response.status_code, 400)

    @mock.patch("apps.users.views.sync_personalized_rag_for_user")
    def test_rebuild_personalized_rag_returns_latest_settings(self, mocked_sync):
        setting, _ = UserSetting.objects.get_or_create(user=self.user)
        setting.personalized_rag_enabled = True
        setting.personalized_rag_status = "ready"
        setting.personalized_rag_chunk_count = 6
        setting.save()

        mocked_sync.return_value = {
            "mode": "manual_rebuild",
            "user_id": self.user.id,
            "total_chunks": 6,
            "upserted_count": 6,
            "indexed_count_after_sync": 6,
            "source_type_breakdown": {"personalized_plan": 1},
        }

        response = self.client.post("/api/v1/users/settings/personalized-rag/rebuild")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["settings"]["personalized_rag_enabled"], True)


class MockLoginTests(TestCase):
    def test_mock_login_with_same_debug_code_reuses_same_user(self):
        first = login_with_code("debug_local_tester", nickname="Tester A")
        second = login_with_code("debug_local_tester", nickname="Tester B")

        self.assertEqual(first["user"]["id"], second["user"]["id"])
        self.assertEqual(WxUser.objects.filter(openid="mock_debug_local_tester").count(), 1)
