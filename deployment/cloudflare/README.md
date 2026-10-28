# HTTPS access for the Atlas API

Start the API locally with `python -m backend.app` and verify `python -m backend.healthcheck`. Its default bind is http://127.0.0.1:8000. Every data route requires the separate ATLAS_API_TOKEN bearer credential.

For a temporary development URL, install cloudflared for your platform, then run in another terminal:

```sh
cloudflared tunnel --url http://127.0.0.1:8000
```

Use the resulting `https://...trycloudflare.com` URL in Android's Server URL field. Enter your ATLAS_API_TOKEN in the app's Atlas access-token field. The tunnel provides HTTPS; the API validates the bearer token. Keep the API and cloudflared processes running. A Quick Tunnel URL is temporary and may change on restart; it is not a configured permanent deployment.

For a stable hostname, follow [Cloudflare's named tunnel setup](https://developers.cloudflare.com/tunnel/get-started/), with the origin set to http://127.0.0.1:8000. This change does not create a Cloudflare account, DNS record, tunnel, or running service for you. Cloudflare Access service-token headers are not implemented in the current Android client.

Official [Quick Tunnel documentation](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).
