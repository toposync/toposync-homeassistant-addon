# Toposync Home Assistant Add-on

![Toposync](logo.png)

Run Toposync inside Home Assistant with a sidebar app and automatic access to the Home Assistant Core API.

## Features

- Open Toposync from the Home Assistant sidebar.
- Use Home Assistant ingress for UI and API access.
- Connect to the internal Home Assistant Core API automatically.
- Store persistent Toposync data in the add-on data directory.
- Run under Home Assistant supervision and watchdog health checks.
- Use Home Assistant Supervisor network information for ONVIF LAN discovery without requiring host networking.
- Enable a direct Toposync port for mobile apps and local-network access when needed.
- Enable RTSP and WebRTC/WHEP streaming outputs through add-on network settings when needed. HLS for the web/mobile app uses the main Toposync port through an internal proxy.

## After Installation

Start the add-on and open `Toposync` from the Home Assistant sidebar. The Home Assistant connection is managed automatically; no manual host or long-lived access token is required.

## Access

The add-on is visible to Home Assistant administrators in the Home Assistant sidebar. Sidebar access is handled by Home Assistant ingress.

## Direct Access

By default, Toposync is available through Home Assistant ingress only. To expose it directly on the local network, map the direct access port in the add-on `Network` settings:

```yaml
18756/tcp: 18756
```

Then open `http://homeassistant.local:18756/` or `http://<home-assistant-ip>:18756/`.

Direct access uses Toposync local authentication. The initial local user is not created from the public first-access screen while the add-on runs in hybrid mode; create/manage local users from inside Toposync through the Home Assistant sidebar or by editing the add-on data configuration.

The direct port is served through a local proxy that strips Home Assistant ingress identity headers before forwarding requests to Toposync.

## Streaming Access

The add-on includes the Toposync streaming bundle and system FFmpeg. MediaMTX is downloaded on demand by Toposync when the streaming engine is started.

By default, HLS playback is served through the Toposync direct/API port (`18756`) at `/api/streams/media/hls/...`. The MediaMTX HLS listener stays internal for the signed proxy and server-side probes, so `18759/tcp` is not part of the public add-on port contract.

For mobile browsers or direct-IP access, keep the dashboard transport on `Auto` or `HLS` unless you specifically need low latency. This uses stable signed HLS through `18756/tcp` and does not require browser cookies, `18759/tcp`, WHEP, or UDP media transport.

To expose direct streaming protocols on the local network, map only the protocols you need in the add-on `Network` settings:

```yaml
18758/tcp: 18758
18760/tcp: 18760
18762/udp: 18762
```

Recommended add-on ports stay in the `18756-18762` range when enabled: `18756` direct access and proxied HLS, `18757` ingress/backend, `18758` RTSP diagnostics, `18760` WebRTC/WHEP signaling, `18761` for the internal MediaMTX API, and `18762/udp` for WebRTC media transport. The MediaMTX HLS/API ports are internal and are not published through default add-on network settings.

Open Toposync from the Home Assistant sidebar, enable the streaming engine, enable LAN exposure for the engine, map the direct Toposync port for app/web HLS, and map RTSP/WebRTC ports only when those protocols are needed. Mobile browsers and direct-IP access should stay stable through signed HLS on `18756/tcp`. RTSP clients should prefer TCP transport. WebRTC is only needed for low-latency dashboard/PTZ usage; playback from the LAN needs `18760/tcp` for WHEP signaling, `18762/udp` for media transport, and the browser host/IP covered by `TOPOSYNC_STREAMING_WEBRTC_ADDITIONAL_HOSTS` or `TOPOSYNC_ADDON_PUBLIC_HOSTS`.

Leave the corresponding host ports empty in the add-on `Network` settings when you do not want direct or streaming access from the local network.
