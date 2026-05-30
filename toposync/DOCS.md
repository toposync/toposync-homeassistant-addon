# Toposync

TopoSync runs inside Home Assistant as a supervised add-on.

## What You Get

- A Toposync entry in the Home Assistant sidebar.
- UI and API access through Home Assistant ingress.
- Automatic connection to the internal Home Assistant Core API.
- Persistent application data stored in `/data`.
- Support for `amd64` and 64-bit ARM Home Assistant OS (`aarch64`).

## Usage

Start the add-on, then open `Toposync` from the sidebar. The Home Assistant extension is configured automatically by the add-on runtime.

The add-on installs `toposync-streaming==0.7.2`. The add-on version can differ from the Python package version because Home Assistant tracks add-on releases separately.

## Access

The sidebar entry is restricted to Home Assistant administrators. The internal Toposync service is intended to be accessed through Home Assistant ingress.

## ARM64 Scope

The supported ARM target is 64-bit Home Assistant OS on `aarch64`. The 32-bit architectures `armv7`, `armhf` and `i386` are outside the support target.

Raspberry Pi 5 with 8 GB RAM and NVMe storage is the practical baseline for camera and vision workloads. Use a separate Toposync processing server when multiple cameras, OpenCV-heavy processing or ONNX Runtime CPU inference become bottlenecks.
