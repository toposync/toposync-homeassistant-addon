# Toposync Home Assistant Add-on Repository

This repository contains the Home Assistant add-on package for Toposync.

Add this repository to Home Assistant:

```text
https://github.com/toposync/toposync-homeassistant-addon
```

Then install the `Toposync` add-on from the add-on store.

The add-on runs the published `toposync` Python package behind Home Assistant ingress:

- frontend and API are served by the same `toposync serve` process
- access is managed by Home Assistant ingress
- the Home Assistant extension uses the internal Supervisor Core API automatically
- persistent data lives in `/data`

The main project lives at:

```text
https://github.com/toposync/toposync
```

## Release Note

The add-on image installs `toposync==0.3.4` from PyPI by default. Publish that package version to PyPI before expecting a clean install from a user's Home Assistant instance.
