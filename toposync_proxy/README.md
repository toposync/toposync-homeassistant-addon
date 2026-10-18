# Toposync Remote Instance

[English setup](https://github.com/toposync/toposync-homeassistant-addon/blob/main/toposync_proxy/DOCS.md) · [Guia em português](https://github.com/toposync/toposync-homeassistant-addon/blob/main/toposync_proxy/DOCS.pt-BR.md)

Open a remote Toposync instance from the Home Assistant sidebar. Toposync keeps running on your Ubuntu server, another computer, or another virtual machine on the same host.

This add-on installs only the connection to your remote instance. You do not need **Toposync Full Application** alongside it.

Install this add-on from the existing Toposync repository, configure the server address and proxy credential, then select **Open Web UI**. See [Setup](https://github.com/toposync/toposync-homeassistant-addon/blob/main/toposync_proxy/DOCS.md) for the required server authentication settings.

- Ingress authenticates Home Assistant administrators and preserves each user's identity.
- HTTPS certificate verification is always enabled.
- Interface, files, HLS, continuous events and WebSockets pass through the proxy.
- No Toposync package, inference engine, camera configuration or application data is installed here.
- Supported architectures: `amd64` and `aarch64`.

The remote instance requires Toposync **0.10.0 or newer** with authenticated ingress proxy support. Older builds are rejected rather than trusted by source address alone. Installing this add-on does not upgrade or configure the external server.
