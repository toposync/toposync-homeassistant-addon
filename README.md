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
- The add-on supports `amd64` and 64-bit ARM Home Assistant OS (`aarch64` / `linux/arm64`).
- The Home Assistant extension connects to the internal Core API automatically.
- No Home Assistant host or long-lived access token needs to be configured inside Toposync.
- Persistent Toposync data is stored in the add-on data directory.
- ONVIF camera discovery can use Home Assistant Supervisor network information to scan the LAN while keeping the add-on off host networking.
- A direct local-network port can be enabled for mobile apps and browser access outside the Home Assistant sidebar.
- RTSP and WebRTC/WHEP streaming playback ports can be enabled through the add-on network settings. HLS for the web/mobile app uses the main Toposync port through an internal proxy.

## Access

The add-on is shown only to Home Assistant administrators in the Home Assistant sidebar. Sidebar access is handled by Home Assistant ingress.

## Direct Access

By default, the add-on exposes Toposync through Home Assistant ingress only. To expose Toposync directly on the local network for mobile apps or browser access outside the Home Assistant sidebar, map the direct access port in the add-on `Network` settings:

```yaml
18756/tcp: 18756
```

Open Toposync at `http://homeassistant.local:18756/` or `http://<home-assistant-ip>:18756/`.

Direct access uses Toposync local authentication. The add-on runs in hybrid mode: Home Assistant ingress uses the Home Assistant user, while direct access uses Toposync users. Initial local user creation is not exposed on the direct first-access screen in hybrid mode; create/manage local users from inside Toposync through the Home Assistant sidebar or by editing the add-on data configuration.

The direct port is served through a local proxy that strips Home Assistant ingress identity headers before forwarding requests to Toposync. This prevents direct clients from spoofing the Home Assistant user headers.

## Streaming Access

The add-on installs the Toposync streaming bundle and system FFmpeg. Toposync downloads MediaMTX on demand when the streaming engine is started.

By default, HLS playback is served through the Toposync direct/API port (`18756`) at `/api/streams/media/hls/...`. The MediaMTX HLS listener stays internal for the signed proxy and server-side probes, so `18759/tcp` is not part of the public add-on port contract.

For mobile browsers or direct-IP access, keep the dashboard transport on `Auto` or `HLS` unless you specifically need low latency. This uses stable signed HLS through `18756/tcp` and does not require browser cookies, `18759/tcp`, WHEP, or UDP media transport.

To expose direct streaming protocols on the local network, map only the protocols you need in the add-on `Network` settings:

```yaml
18758/tcp: 18758
18760/tcp: 18760
18762/udp: 18762
```

`18758/tcp` is RTSP and is optional. Camera ingest paths are never anonymous: Toposync generates a `toposync_ingest` password and keeps it out of diagnostics/logs. Use **Streaming > Camera ingest access > Reveal credentials** to copy URLs such as `rtsp://toposync_ingest:<password>@<host>:18758/ingest-<camera>` for Frigate or development instances. After rotating ingest credentials in Toposync, update those external consumers.

Recommended add-on ports stay in the `18756-18762` range when enabled: `18756` direct access and proxied HLS, `18757` ingress/backend, `18758` RTSP diagnostics, `18760` WebRTC/WHEP signaling, `18761` for the internal MediaMTX API, and `18762/udp` for WebRTC media transport. The MediaMTX HLS/API ports are internal and are not published through default add-on network settings.

Open Toposync from the Home Assistant sidebar, enable the streaming engine, enable LAN exposure for the engine, map the direct Toposync port for app/web HLS, and map RTSP/WebRTC ports only when those protocols are needed. Mobile browsers and direct-IP access should stay stable through signed HLS on `18756/tcp`; WebRTC is only needed for low-latency dashboard/PTZ usage. WebRTC playback from the LAN needs `18760/tcp` for WHEP signaling, `18762/udp` for media transport, and the browser host/IP covered by `TOPOSYNC_STREAMING_WEBRTC_ADDITIONAL_HOSTS` or `TOPOSYNC_ADDON_PUBLIC_HOSTS`.

Leave the corresponding host ports empty in the add-on `Network` settings when you do not want direct or streaming access from the local network.

## Extension-Ready Builds

The image installs `toposync-streaming==0.7.3` by default. The Home Assistant add-on has its own version number, currently `0.7.4`, because Home Assistant tracks the add-on package separately from the Python package installed inside the image.

Future extension packages can be preinstalled at build time with the `TOPOSYNC_EXTENSION_PIP_SPECS` build argument, while runtime extension auto-install remains enabled so managed extensions can be restored after add-on updates.

## ARM64 Notes

The supported ARM target is 64-bit Home Assistant OS on `aarch64`. The unsupported 32-bit architectures `armv7`, `armhf` and `i386` are outside the Toposync add-on support target.

Raspberry Pi 5 with 8 GB RAM and NVMe storage is the practical baseline for a modern camera/vision deployment. Raspberry Pi 4 and SD-card installs are best-effort for compatibility. Delegate multiple cameras, OpenCV-heavy processing and ONNX Runtime CPU inference to a separate Toposync processing server when possible.

## Storage

TopoSync stores its application data under `/data` inside the add-on container. Home Assistant manages that directory as add-on data.

## GPU Support

This add-on uses the standard CPU package. CUDA/GPU acceleration is not enabled in this add-on package.

## Project

TopoSync main project:

```text
https://github.com/toposync/toposync
```
