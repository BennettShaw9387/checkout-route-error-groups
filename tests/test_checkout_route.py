"""Focused transport and route tests; no network access is used."""

from __future__ import annotations

import io
import json
import unittest
import urllib.error

from checkout_route import run_checkout
from infrai_client import InfraiClient


class FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class CaptureTests(unittest.TestCase):
    def test_route_captures_a_stable_group_and_reraises(self) -> None:
        requests = []

        def open_ok(request, timeout):
            requests.append((request, timeout))
            return FakeResponse({"ok": True, "data": {"event_id": "evt_42"}, "error": None, "metadata": {}})

        client = InfraiClient("test-key", opener=open_ok)

        def charge(_cart_id):
            raise ValueError("payment method missing")

        with self.assertRaisesRegex(ValueError, "payment method missing"):
            run_checkout("cart_42", charge, client)

        request, timeout = requests[0]
        body = json.loads(request.data)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(timeout, 30)
        self.assertEqual(body["fingerprint"], ["checkout", "charge"])
        self.assertIn("ValueError: payment method missing", body["exception"])
        self.assertEqual(request.get_header("Idempotency-key"), body["idempotency_key"])

    def test_429_honors_retry_after_and_reuses_the_key(self) -> None:
        requests = []
        delays = []

        def open_then_accept(request, timeout):
            requests.append(request)
            if len(requests) == 1:
                raise urllib.error.HTTPError(
                    request.full_url,
                    429,
                    "rate limited",
                    {"Retry-After": "3"},
                    io.BytesIO(b""),
                )
            return FakeResponse({"ok": True, "data": {}, "error": None, "metadata": {}})

        client = InfraiClient("test-key", opener=open_then_accept, sleep=delays.append)
        client.errors.capture(
            exception="ValueError: payment method missing",
            fingerprint=["checkout", "charge"],
            idempotency_key="capture-42",
        )

        self.assertEqual(delays, [3.0])
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0].data, requests[1].data)
        self.assertEqual(requests[0].get_header("Idempotency-key"), "capture-42")


if __name__ == "__main__":
    unittest.main()

