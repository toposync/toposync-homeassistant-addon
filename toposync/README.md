# Toposync Home Assistant Add-on

![Toposync](logo.png)

Run Toposync inside Home Assistant with a sidebar app and automatic access to the Home Assistant Core API.

## Features

- Open Toposync from the Home Assistant sidebar.
- Use Home Assistant ingress for UI and API access.
- Connect to the internal Home Assistant Core API automatically.
- Store persistent Toposync data in the add-on data directory.
- Run under Home Assistant supervision and watchdog health checks.

## After Installation

Start the add-on and open `Toposync` from the Home Assistant sidebar. The Home Assistant connection is managed automatically; no manual host or long-lived access token is required.

## Access

The add-on is visible to Home Assistant administrators. Direct access to the internal Toposync service is restricted to Home Assistant ingress.
