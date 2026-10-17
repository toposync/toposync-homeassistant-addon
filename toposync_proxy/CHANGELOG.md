# Changelog

## 0.1.1 - 2026-10-17

- Use absolute setup-guide links so English and Portuguese documentation opens from the Home Assistant store and Documentation tab.

## 0.1.0 - 2026-10-17

- Add an ingress-only proxy for a remote TopoSync instance on amd64 and aarch64.
- Require authenticated ingress proxy support, preserve Home Assistant user identity and retain direct TopoSync login.
- Forward files, HLS, streaming responses and WebSockets with verified HTTPS.
- Distinguish the remote instance from the full application in the store and sidebar.
- Translate configuration and connection errors into English and Portuguese.
- Support HTTPS virtual hosts and give actionable startup errors without exposing option values.
