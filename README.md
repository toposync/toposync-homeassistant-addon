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

## Access

The add-on is shown only to Home Assistant administrators. Access is handled by Home Assistant ingress, and direct access to the internal Toposync port is restricted.

## Storage

TopoSync stores its application data under `/data` inside the add-on container. Home Assistant manages that directory as add-on data.

## GPU Support

This add-on uses the standard CPU package. CUDA/GPU acceleration is not enabled in this add-on package.

## Project

TopoSync main project:

```text
https://github.com/toposync/toposync
```
