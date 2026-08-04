"""A server-route-shaped checkout handler that captures backend exceptions."""

from __future__ import annotations

import argparse
import json
import traceback
import uuid
from collections.abc import Callable
from typing import Any

from infrai_client import InfraiClient, create_client


def run_checkout(
    cart_id: str,
    charge: Callable[[str], dict[str, Any]],
    infrai: InfraiClient,
) -> dict[str, Any]:
    """Run checkout work, capturing and re-raising any backend exception."""
    try:
        return charge(cart_id)
    except Exception:
        # Keep grouping stable across carts while retaining the useful Python stack.
        exception_payload = traceback.format_exc()
        infrai.errors.capture(
            exception=exception_payload,
            fingerprint=["checkout", "charge"],
            idempotency_key=f"checkout-error:{uuid.uuid4()}",
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one checkout route invocation")
    parser.add_argument("cart_id")
    args = parser.parse_args()

    def charge(cart_id: str) -> dict[str, Any]:
        raise ValueError(f"Cart {cart_id} has no payment method")

    try:
        run_checkout(args.cart_id, charge, create_client())
    except ValueError:
        print(json.dumps({"captured": True, "group": "checkout/charge"}))


if __name__ == "__main__":
    main()

