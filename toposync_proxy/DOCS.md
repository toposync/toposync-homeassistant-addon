# TopoSync Remote Instance — Setup

[Guia em português](https://github.com/toposync/toposync-homeassistant-addon/blob/main/toposync_proxy/DOCS.pt-BR.md)

This add-on connects to TopoSync already installed elsewhere. It does not install the application, copy its data or manage its updates. You do not need the full application add-on. “Remote” also includes another virtual machine on the same physical host.

## Prepare the remote TopoSync server

Use TopoSync **0.10.0 or newer**, containing the authenticated ingress proxy endpoint `/api/auth/ingress-proxy`. The add-on checks this contract before forwarding each request, including WebSocket connections. A version number alone does not establish support; a build without the endpoint or without the token configuration is rejected.

Before enabling hybrid authentication, open TopoSync directly over a protected connection and create a local owner account. Keep this account for recovery when Home Assistant is unavailable. Hybrid mode disables first-time account creation through direct access.

Generate a dedicated proxy credential on a trusted computer:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Treat the output as a password. Configure the remote TopoSync process or container with:

```yaml
environment:
  TOPOSYNC_AUTH_MODE: home_assistant_hybrid
  TOPOSYNC_AUTH_INGRESS_PROXY_TOKEN: "${TOPOSYNC_INGRESS_PROXY_TOKEN}"
  TOPOSYNC_AUTH_INGRESS_TRUSTED_IPS: "${TOPOSYNC_INGRESS_PROXY_SOURCE}"
  TOPOSYNC_STREAMING_HLS_PUBLIC_MODE: proxy
  FORWARDED_ALLOW_IPS: ""
```

`TOPOSYNC_INGRESS_PROXY_TOKEN` is the generated credential. `TOPOSYNC_INGRESS_PROXY_SOURCE` is the exact peer address observed by TopoSync for this proxy connection, which may be the Home Assistant host, a Docker gateway, or a local HTTPS reverse proxy after network translation. Use only the addresses needed by this deployment, comma-separated; do not use `*` or an entire network. Token validation remains required even when several clients share that peer address.

`FORWARDED_ALLOW_IPS: ""` prevents Uvicorn from replacing the connection's peer address with a client-supplied forwarded address. If another HTTPS reverse proxy sits before TopoSync, it must route the configured remote hostname to TopoSync and preserve `X-Forwarded-Host`, `X-Forwarded-Proto`, the three Home Assistant identity headers, `X-Ingress-Path`, and `X-Toposync-Ingress-Token`, and must not log credentials or signed media queries. Configure that proxy's own trust boundary deliberately. Restrict backend network access to the intended entry points.

The Home Assistant panel is administrator-only. Ingress identities receive the existing TopoSync `owner` role by default; they are not a copy of Home Assistant's permission model. This release does not provide individual role mapping or support opening the panel to non-administrators.

## Configure the add-on

In the add-on store, install **TopoSync Remote Instance** from this repository. Open **Configuration**, fill in the two required fields below, and save before starting. Both fields start empty because the address and credential belong to your deployment.

| Option | Description |
| --- | --- |
| **Remote instance address** (`server_url`) | The server origin, for example `https://toposync.example.com:8443`. TopoSync must be served at `/`. No username, password, additional path, query or fragment. |
| **Remote instance access token** (`proxy_token`) | The same dedicated credential configured in `TOPOSYNC_AUTH_INGRESS_PROXY_TOKEN`; 32–256 letters, digits, underscores or hyphens. |
| **Allow HTTP over an encrypted private tunnel** (`allow_http`) | Default `false`. Enable only when HTTP travels through an existing encrypted private tunnel. An ordinary local network does not encrypt this credential. |

Use an address reachable **from the add-on**, not just from your browser. `localhost` refers to the proxy container, not another virtual machine or the Docker host. Running both virtual machines on the same physical server does not change this rule.

HTTPS uses the container's system certificate authorities and verifies the server name. Prefer a hostname with a trusted certificate. There is no option to disable verification or upload a custom certificate authority in this initial release. For an existing private encrypted tunnel, HTTP is available through the explicit `allow_http` option.

Start the add-on, select **Open Web UI**, and optionally enable **Show in sidebar**. Its sidebar entry is **TopoSync Remote Instance**, distinct from **TopoSync Full Application**. Configuration labels follow the Home Assistant language (English or Brazilian Portuguese); connection errors follow the browser’s primary language (Portuguese or English fallback). Home Assistant does not support translating the add-on name or sidebar title through these translation files, so both names remain in English. No host ports need to be published. The proxy accepts interface requests only from the Supervisor at `172.30.32.2`, with a valid Ingress path and user identity. It does not need Supervisor or Home Assistant API access. Home Assistant authorization headers and cookies are not forwarded; only TopoSync session cookies are retained, with cookie paths restricted to the Ingress prefix.

## Files and live video

HTTP requests, query strings, signed HLS URLs, uploads, downloads, byte ranges and WebSockets are forwarded. Uploads are limited to 1 GiB; active streams have a one-hour inactivity timeout. No application response cache is enabled. Absolute and relative redirects retain the Ingress prefix.

Use HLS for video inside Home Assistant. RTSP and WebRTC media transport require their own network configuration and are not tunneled by this HTTP add-on. The browser should reach HLS through Home Assistant, without needing direct access to the Ubuntu address. Validate live camera playback on the actual installation before relying on remote viewing.

## Errors and recovery

- **Access denied:** verify the matching proxy credential, allowed source address and current Home Assistant user. Reopen the panel after signing in to Home Assistant. Missing identity is never replaced with a default user.
- **Connection unavailable:** check the server URL, network, DNS, HTTPS certificate and authenticated ingress proxy support. A server without the required endpoint is rejected.
- **Configuration error in the add-on log:** the message names the invalid field and its requirement. Correct it in Configuration, save and restart. File access or malformed configuration produces a separate message. Option values are deliberately excluded from errors.

DNS is resolved during requests and refreshed after 30 seconds. The proxy starts even when the destination is unavailable and reconnects when it returns. The container health check tests only the local proxy, so a stopped Ubuntu server does not cause restart loops.

Request and Nginx error logs are disabled to avoid recording session credentials or signed URLs. The browser messages provide the basic connection/authentication diagnosis. Inspect the external server's protected diagnostics when more detail is needed, without enabling request logs that expose credentials.

Rotate the credential by changing it on the external server and in the add-on options, then restarting the affected services. Access through the panel will be unavailable while the values differ; direct TopoSync login remains available. Back up the add-on options securely: the backup contains the credential.

Stopping, updating or uninstalling this proxy does not stop TopoSync pipelines or remove external data. Back up the remote TopoSync data separately. Configure the TopoSync Home Assistant extension with its own Home Assistant URL and API credential; the proxy does not export the Supervisor token or configure entities. Samba, GPU setup and media servers remain part of the external deployment.
