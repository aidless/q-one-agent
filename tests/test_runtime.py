import json
import unittest
import httpx
from qone_agent.runtime import ProviderError, public_context, run_model

DECISION = {"question": "今天先学什么？", "success_criterion": "完成练习", "domain": "learning",
    "deadline": "2030-01-01T00:00:00Z", "risk": "low", "reversible": True, "context": "30分钟",
    "options": [{"id": "a", "label": "练习"}, {"id": "b", "label": "看书"}],
    "events": [{"private": "secret history"}], "baseline": {"private": "initial choice"}}
CONFIG = {"cloud_url": "https://example.invalid/v1", "cloud_model": "test", "cloud_key": "secret-key"}
GOOD = {"option_id": "a", "confidence": .7, "rationale": "练习可核查，仍需自行确认"}


class AdapterTests(unittest.TestCase):
    def transport(self, answer=GOOD):
        def handler(request):
            self.assertEqual(request.headers["authorization"], "Bearer secret-key")
            context = json.loads(json.loads(request.content)["messages"][1]["content"])
            self.assertNotIn("events", context)
            self.assertNotIn("baseline", context)
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(answer)}}]})
        return httpx.MockTransport(handler)

    def test_cloud_contract_without_live_provider(self):
        result = run_model(DECISION, "cloud", CONFIG, remote_confirmed=True, transport=self.transport())
        self.assertEqual(result.recommendation["option_id"], "a")
        self.assertIsNone(result.recommendation["success_probability"])
        self.assertNotIn("recommendation", result.receipt())
        self.assertTrue(result.recommendation["requires_human"])

    def test_remote_cannot_send_without_confirmation(self):
        with self.assertRaises(ProviderError):
            run_model(DECISION, "cloud", CONFIG, transport=self.transport())

    def test_unknown_option_or_invalid_strength_rejected(self):
        for change in ({"option_id": "other"}, {"option_id": []}, {"confidence": True}, {"confidence": -1}, {"confidence": float("nan")}, {"rationale": ""}):
            with self.subTest(change=change), self.assertRaises(ProviderError):
                run_model(DECISION, "cloud", CONFIG, remote_confirmed=True, transport=self.transport(GOOD | change))

    def test_errors_do_not_expose_service_body_or_key(self):
        transport = httpx.MockTransport(lambda r: httpx.Response(401, text="secret-key raw detail"))
        with self.assertRaises(ProviderError) as raised:
            run_model(DECISION, "cloud", CONFIG, remote_confirmed=True, transport=transport)
        self.assertNotIn("secret-key", str(raised.exception))
        self.assertIn("401", str(raised.exception))

    def test_ollama_contract(self):
        def handler(request):
            body = json.loads(request.content)
            self.assertFalse(body["stream"])
            self.assertEqual(body["keep_alive"], 0)
            return httpx.Response(200, json={"message": {"content": json.dumps(GOOD)}})
        result = run_model(DECISION, "ollama", {}, transport=httpx.MockTransport(handler))
        self.assertEqual(result.provider, "ollama")

    def test_allowlist(self):
        self.assertNotIn("events", public_context(DECISION))
        self.assertNotIn("baseline", public_context(DECISION))

    def test_laya_truncated_result_is_rejected_without_fallback(self):
        from unittest.mock import patch
        from subprocess import CompletedProcess
        response = CompletedProcess([], 0, stdout=json.dumps({"error": "Laya输入超出完整比较的预算"}))
        with patch("qone_agent.runtime.subprocess.run", return_value=response):
            with self.assertRaisesRegex(ProviderError, "超出"):
                run_model(DECISION, "laya", {})
