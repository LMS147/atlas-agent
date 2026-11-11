"""Local authenticated probe; credentials never appear in process arguments."""
import http.client
import json
import sys
from backend.atlas.app.config import load_settings


def probe(expected_pid=None):
    try:
        settings = load_settings()
        host = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(settings.host, settings.host)
        connection = http.client.HTTPConnection(host, settings.port, timeout=2)
        try:
            connection.request("GET", "/api/v1/health", headers={"Authorization": f"Bearer {settings.api_token}"})
            response = connection.getresponse()
            payload = json.loads(response.read(8192))
            healthy = response.status == 200 and payload.get("status") == "ok"
            if expected_pid is not None:
                healthy = healthy and payload.get("pid") == expected_pid
            return healthy, payload
        finally:
            connection.close()
    except Exception:
        return False, None


def main():
    healthy, _ = probe()
    if healthy:
        print("Atlas API is healthy")
        return 0
    print("Atlas API is unavailable or configuration/authentication is invalid", file=sys.stderr)
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
