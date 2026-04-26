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
- A direct local-network port can be enabled for mobile apps and browser access outside the Home Assistant sidebar.

## Access

The add-on is shown only to Home Assistant administrators in the Home Assistant sidebar. Sidebar access is handled by Home Assistant ingress.

## Direct Access

The add-on can expose Toposync directly on the local network for mobile apps or browser access outside the Home Assistant sidebar.

Direct access is disabled by default. To enable it, open the add-on `Network` settings and map container port `18756/tcp` to a host port, for example:

```yaml
18756/tcp: 18756
```

Then open Toposync at `http://homeassistant.local:18756/` or `http://<home-assistant-ip>:18756/`.

Direct access uses Toposync local authentication. The add-on runs in hybrid mode: Home Assistant ingress uses the Home Assistant user, while direct access uses Toposync users. Initial local user creation is not exposed on the direct first-access screen in hybrid mode; create/manage local users from inside Toposync through the Home Assistant sidebar or by editing the add-on data configuration.

The direct port is served through a local proxy that strips Home Assistant ingress identity headers before forwarding requests to Toposync. This prevents direct clients from spoofing the Home Assistant user headers.

## Storage

TopoSync stores its application data under `/data` inside the add-on container. Home Assistant manages that directory as add-on data.

## GPU Support

This add-on uses the standard CPU package. CUDA/GPU acceleration is not enabled in this add-on package.

## Project

TopoSync main project:

```text
https://github.com/toposync/toposync
```
