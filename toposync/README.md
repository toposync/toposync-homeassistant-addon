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
- Expose a direct Toposync port for mobile apps and local-network access.
- Expose RTSP, HLS, and WebRTC/WHEP streaming outputs by default.

## After Installation

Start the add-on and open `Toposync` from the Home Assistant sidebar. The Home Assistant connection is managed automatically; no manual host or long-lived access token is required.

## Access

The add-on is visible to Home Assistant administrators in the Home Assistant sidebar. Sidebar access is handled by Home Assistant ingress.

## Direct Access

Toposync is available through Home Assistant ingress and directly on the local network at `http://homeassistant.local:18756/` or `http://<home-assistant-ip>:18756/`.

Direct access uses Toposync local authentication. The initial local user is not created from the public first-access screen while the add-on runs in hybrid mode; create/manage local users from inside Toposync through the Home Assistant sidebar or by editing the add-on data configuration.

The direct port is served through a local proxy that strips Home Assistant ingress identity headers before forwarding requests to Toposync.

## Streaming Access

The add-on includes the Toposync streaming bundle and system FFmpeg. MediaMTX is downloaded on demand by Toposync when the streaming engine is started.

Streaming playback ports are published by default:

```yaml
18758/tcp: 18758
18759/tcp: 18759
18760/tcp: 18760
```

The add-on keeps Toposync services in the `18756-18761` range: `18756` direct access, `18757` ingress/backend, `18758` RTSP, `18759` HLS, `18760` WebRTC/WHEP, and `18761` for the internal MediaMTX API.

Open Toposync from the Home Assistant sidebar, enable the streaming engine, enable LAN exposure for the engine, and restart the engine. RTSP clients should prefer TCP transport.

If you do not want direct or streaming access from the local network, clear the corresponding port mappings in the add-on `Network` settings.
