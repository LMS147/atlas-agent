# Cloudflare connectivity (planned)

The Android client requires authenticated HTTPS. Before creating a tunnel, implement the API described in ../../docs/api.md, enforce bearer-token checks on every endpoint (including health), and keep Groq and Telegram keys on the server.

No tunnel is configured by this change. The FastAPI app is a scaffold with no data endpoints. Do not expose it as a working Atlas API yet. When implemented, bind the local server to loopback and tunnel to it; configure your own hostname in the Android connection screen. Cloudflare Access service-token headers are not implemented by the Android client.

See Cloudflare's current official documentation when setting up a named tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/ .
