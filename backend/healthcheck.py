"""Local authenticated API probe; token never appears in process arguments."""
import http.client
import json
import sys
from backend.app.config import load_settings


def main():
    try:
        settings = load_settings()
        host = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(settings.host, settings.host)
        connection = http.client.HTTPConnection(host, settings.port, timeout=2)
        try:
            connection.request("GET", "/api/v1/health", headers={"Authorization": f"Bearer {settings.api_token}"})
            response = connection.getresponse()
            payload = json.loads(response.read(8192))
            healthy = response.status == 200 and payload.get("status") == "ok"
        finally:
            connection.close()
        if healthy:
            print("Atlas API is healthy")
            return 0
    except Exception:
        pass
    print("Atlas API is unavailable or configuration/authentication is invalid", file=sys.stderr)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
