import sys

with open('backend/api/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = 'app.add_middleware(PrometheusMiddleware)\n\n\n\n\n\n# Anti-scraping UA blocking removed: rate limiting + API key auth (slowapi /\n# verify_public_key) already protect data endpoints without breaking legitimate\n# programmatic clients such as the Python SDK, curl, or httpx.\n\n# Mount Administrative & Control Router (protected by JWT & API Key)\napp.include_router(admin_router)'

new = '''app.add_middleware(PrometheusMiddleware)


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Add API-Version header to all responses for client version detection."""

    API_VERSION = "2.0.0"

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("API-Version", self.API_VERSION)
        if request.headers.get("Accept-Version"):
            response.headers.setdefault(
                "API-Version-Requested", request.headers["Accept-Version"]
            )
        return response


app.add_middleware(APIVersionMiddleware)


# Mount Administrative & Control Router (protected by JWT & API Key)
app.include_router(admin_router)'''

if old in content:
    content = content.replace(old, new, 1)
    with open('backend/api/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS')
else:
    print('NOT FOUND')
    idx = content.find('app.add_middleware(PrometheusMiddleware)')
    if idx >= 0:
        print(repr(content[idx:idx+250]))