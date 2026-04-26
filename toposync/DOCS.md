# Toposync

TopoSync runs inside Home Assistant as a supervised add-on.

## What You Get

- A Toposync entry in the Home Assistant sidebar.
- UI and API access through Home Assistant ingress.
- Automatic connection to the internal Home Assistant Core API.
- Persistent application data stored in `/data`.

## Usage

Start the add-on, then open `Toposync` from the sidebar. The Home Assistant extension is configured automatically by the add-on runtime.

## Access

The sidebar entry is restricted to Home Assistant administrators. The internal Toposync service is intended to be accessed through Home Assistant ingress.
