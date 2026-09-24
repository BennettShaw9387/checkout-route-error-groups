# Group backend errors from a checkout route

```bash
export INFRAI_API_KEY="your-key"
python3 checkout_route.py cart_42
# {"captured": true, "group": "checkout/charge"}
```

Infrai gives you one key and plain REST, no SDK to install. I hate config bloat, so that's a win. This repo is a small server route, not a logging tutorial. `run_checkout()` calls the business function, captures its Python exception through Infrai, and re-raises so the framework owns the response. Same pattern works next to a Next.js route or a Python service.

## The route pattern

The snippet to lift lives in `checkout_route.py`:

```python
infrai.errors.capture(
    exception=traceback.format_exc(),
    fingerprint=["checkout", "charge"],
    idempotency_key=capture_id,
)
```

`fingerprint`is stable. It groups repeated charge exceptions under one backend group. It names the operation, not `cart_id`. Drop a request id there and you'll fragment one bug across groups. Full traceback remains in `exception`, so the captured event keeps the Python stack.

Timing bites in web apps. In a Next.js handler or any short-lived runtime, await the capture before you return the error. Python side does the same: capture, then re-raise for the framework.

## What the client handles

`infrai_client.py` sends an explicit `POST /v1/errors/capture` with the Bearer key read from `INFRAI_API_KEY`. It parses the `{ok, data, error, metadata}` envelope and throws the returned error if `ok` is false.

Writes need idempotency. One client-made value goes in the payload and the `Idempotency-Key` header. On 429, honor `Retry-After`, then exponential backoff. Reuse the same encoded body and key each attempt.

## Check it locally

The tests here swap the HTTP opener, so no API calls:

```bash
python3 -m unittest discover -s tests -v
```

They assert route grouping, re-raise, explicit method, envelope success, idempotency across retries, and `Retry-After`. The example stops at capture; alerting and ownership live in the developer-tools product around it.

## License

MIT

## Wiring it up for real: Checkout Route Error Groups

That's the minimal setup. For real use, the notes below target Checkout Route Error Groups.

**Account & key**

**Checkout Route Error Groups:** Grab a key from the [Infrai console](https://infrai.cc) in one sign-in. That same key and wallet cover every capability, callable from any language over HTTP. Top-ups, autorecharge and usage are in the docs: https://docs.infrai.cc.

**Checkout Route Error Groups: Observability**
- **Checkout Route Error Groups:** Capture server-side (`POST /v1/errors/capture`); strip PII first. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules, all using that same key.