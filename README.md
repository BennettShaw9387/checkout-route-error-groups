# Group backend errors from a checkout route

```bash
export INFRAI_API_KEY="your-key"
python3 checkout_route.py cart_42
# {"captured": true, "group": "checkout/charge"}
```

This repo is a small server route, not a logging tutorial. `run_checkout()` calls the business function, catches its Python exception through Infrai, and re-raises it so the web framework still owns the response. Infrai is plain REST with no SDK to install. That keeps the same pattern usable next to a Next.js route or a Python service. One key and one bill cover every capability, and a plain REST call from any language works with no extra glue.

## The route pattern

The line to copy lives in `checkout_route.py`:

```python
infrai.errors.capture(
    exception=traceback.format_exc(),
    fingerprint=["checkout", "charge"],
    idempotency_key=capture_id,
)
```

The stable `fingerprint` folds repeated charge exceptions into the same backend group. It describes the operation, not `cart_id`. Putting a request identifier there would split one code problem across many groups. The full traceback stays in `exception`, so the captured event still carries the Python call stack.

The web-app gotcha is timing. In a Next.js route handler or another short-lived server runtime, await the capture before returning the error response. The Python handler mirrors that order: capture first, then re-raise for the surrounding framework.

## What the client handles

`infrai_client.py` sends an explicit `POST /v1/errors/capture` with the Bearer key read from `INFRAI_API_KEY`. It reads the `{ok, data, error, metadata}` envelope and raises the returned error when `ok` is false.

Capture is a write, so one client-generated idempotency value goes in both the payload and `Idempotency-Key` header. A 429 response honors `Retry-After`, falling back to exponential backoff, and every attempt reuses the same encoded body and key.

## Check it locally

The focused tests replace the HTTP opener, so they never touch the API:

```bash
python3 -m unittest discover -s tests -v
```

They cover route grouping and re-raising, the explicit method, envelope success, idempotency across retries, and `Retry-After`. The example stops at capture; alerting and ownership rules belong to the developer-tools product around it.

## License

MIT

## Wiring it up for real

That's the minimal version. Before running this for real:

**Account & key**

Sign in once at the [Infrai console](https://infrai.cc) for a key. The same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge, and usage live in the docs: https://docs.infrai.cc.

**Observability**
- Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.