# Toposync Home Assistant Add-on

![Toposync](toposync/logo.png)

Run Toposync inside Home Assistant with a sidebar app, ingress, supervised execution, and automatic access to the Home Assistant Core API.

## Installation

1. Open Home Assistant.
2. Go to `Settings` -> `Add-ons` -> `Add-on Store`.
3. Open the menu in the top-right corner and select `Repositories`.
4. Add this repository:

```text
https://github.com/toposync/toposync-homeassistant-addon
```

5. Find `Toposync` in the add-on store.
6. Install and start the add-on.
7. Open `Toposync` from the Home Assistant sidebar.

## What It Provides

- Toposync runs as a supervised Home Assistant add-on.
- The Toposync UI is available from the Home Assistant sidebar.
- UI and API are served through Home Assistant ingress.
- The Home Assistant extension connects to the internal Core API automatically.
- No Home Assistant host or long-lived access token needs to be configured inside Toposync.
- Persistent Toposync data is stored in the add-on data directory.
- ONVIF camera discovery can use Home Assistant Supervisor network information to scan the LAN while keeping the add-on off host networking.
- A direct local-network port is exposed for mobile apps and browser access outside the Home Assistant sidebar.
- RTSP, HLS, and WebRTC/WHEP streaming playback ports are exposed through the add-on network settings by default.

## Access

The add-on is shown only to Home Assistant administrators in the Home Assistant sidebar. Sidebar access is handled by Home Assistant ingress.

## Direct Access

The add-on exposes Toposync directly on the local network for mobile apps or browser access outside the Home Assistant sidebar.

Open Toposync at `http://homeassistant.local:18756/` or `http://<home-assistant-ip>:18756/`.

Direct access uses Toposync local authentication. The add-on runs in hybrid mode: Home Assistant ingress uses the Home Assistant user, while direct access uses Toposync users. Initial local user creation is not exposed on the direct first-access screen in hybrid mode; create/manage local users from inside Toposync through the Home Assistant sidebar or by editing the add-on data configuration.

The direct port is served through a local proxy that strips Home Assistant ingress identity headers before forwarding requests to Toposync. This prevents direct clients from spoofing the Home Assistant user headers.

## Streaming Access

The add-on installs the Toposync streaming bundle and system FFmpeg. Toposync downloads MediaMTX on demand when the streaming engine is started.

The add-on publishes the standard playback ports by default:

```yaml
18758/tcp: 18758
18759/tcp: 18759
18760/tcp: 18760
```

The add-on reserves the `18756-18761` range for Toposync services: `18756` direct access, `18757` ingress/backend, `18758` RTSP, `18759` HLS, `18760` WebRTC/WHEP, and `18761` for the internal MediaMTX API.

Open Toposync from the Home Assistant sidebar, enable the streaming engine, enable LAN exposure for the engine, and restart the engine. Use RTSP over TCP when possible.

If you do not want direct or streaming access from the local network, clear the corresponding port mappings in the add-on `Network` settings.

## Extension-Ready Builds

The image installs the current Toposync streaming bundle by default. Future extension packages can be preinstalled at build time with the `TOPOSYNC_EXTENSION_PIP_SPECS` build argument, while runtime extension auto-install remains enabled so managed extensions can be restored after add-on updates.

## Storage

TopoSync stores its application data under `/data` inside the add-on container. Home Assistant manages that directory as add-on data.

## GPU Support

This add-on uses the standard CPU package. CUDA/GPU acceleration is not enabled in this add-on package.

## Project

TopoSync main project:

```text
https://github.com/toposync/toposync
```
