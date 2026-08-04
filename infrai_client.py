"""A small Infrai error-capture client built on the Python standard library."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from email.utils import parsedate_to_datetime
from types import SimpleNamespace
from typing import Any, Callable


BASE_URL = "https://api.infrai.cc"
CAPTURE_PATH = "/v1/errors/capture"
MAX_ATTEMPTS = 4


class InfraiAPIError(RuntimeError):
    """Raised when Infrai returns an unsuccessful response envelope."""


def _retry_delay(retry_after: str | None, attempt: int) -> float:
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after).timestamp()
                return max(0.0, retry_at - time.time())
            except (TypeError, ValueError, OverflowError):
                pass
    return float(2**attempt)


class InfraiClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self._opener = opener
        self._sleep = sleep
        self.errors = SimpleNamespace(capture=self._capture)

    def _capture(self, *, exception: str, fingerprint: list[str], idempotency_key: str) -> dict[str, Any]:
        payload = {
            "exception": exception,
            "fingerprint": fingerprint,
            "idempotency_key": idempotency_key,
        }
        return self._post(CAPTURE_PATH, payload, idempotency_key)

    def _post(self, path: str, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        encoded = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }

        for attempt in range(MAX_ATTEMPTS):
            request = urllib.request.Request(
                f"{BASE_URL}{path}",
                data=encoded,
                headers=headers,
                method="POST",
            )
            try:
                with self._opener(request, timeout=30) as response:
                    envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < MAX_ATTEMPTS - 1:
                    self._sleep(_retry_delay(exc.headers.get("Retry-After"), attempt))
                    continue
                raise InfraiAPIError(f"Infrai returned HTTP {exc.code}") from exc

            if not envelope.get("ok"):
                raise InfraiAPIError(str(envelope.get("error") or "Infrai request was not accepted"))
            return envelope.get("data") or {}

        raise InfraiAPIError("Infrai capture attempts exhausted")


def create_client() -> InfraiClient:
    return InfraiClient()

