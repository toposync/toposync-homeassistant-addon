ARG BUILD_ARCH
FROM python:3.12-slim-bookworm

ARG BUILD_ARCH
ARG TARGETARCH
ARG GO2RTC_VERSION=
ARG TOPOSYNC_PIP_SPEC=toposync-streaming==0.7.7
ARG TOPOSYNC_ADDON_PIP_SPECS="fastapi httpx uvicorn"
ARG TOPOSYNC_EXTENSION_PIP_SPECS=
ARG TOPOSYNC_PIP_INDEX_URL=https://pypi.org/simple
ARG TOPOSYNC_EXTRA_INDEX_URL=
ARG TOPOSYNC_APT_PACKAGES=ffmpeg

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV VIRTUAL_ENV=/opt/toposync/.venv
ENV PATH="/opt/toposync/.venv/bin:${PATH}"
ENV TOPOSYNC_STREAMING_FFMPEG_PATH=/usr/bin/ffmpeg
ENV TOPOSYNC_STREAMING_GO2RTC_PATH=/usr/local/bin/go2rtc
ENV TOPOSYNC_EXTENSION_AUTO_INSTALL_ON_STARTUP=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates tini ${TOPOSYNC_APT_PACKAGES} \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv "${VIRTUAL_ENV}" \
 && "${VIRTUAL_ENV}/bin/python" -m pip install --upgrade pip

RUN set -e; \
  pip_index_args="--index-url ${TOPOSYNC_PIP_INDEX_URL}"; \
  if [ -n "${TOPOSYNC_EXTRA_INDEX_URL}" ]; then \
    pip_index_args="${pip_index_args} --extra-index-url ${TOPOSYNC_EXTRA_INDEX_URL}"; \
  fi; \
  "${VIRTUAL_ENV}/bin/python" -m pip install ${pip_index_args} "${TOPOSYNC_PIP_SPEC}" ${TOPOSYNC_ADDON_PIP_SPECS}; \
  if [ -n "${TOPOSYNC_EXTENSION_PIP_SPECS}" ]; then \
    "${VIRTUAL_ENV}/bin/python" -m pip install ${pip_index_args} ${TOPOSYNC_EXTENSION_PIP_SPECS}; \
  fi; \
  "${VIRTUAL_ENV}/bin/python" - <<'PY'
import fastapi
import httpx
import starlette.responses
import toposync
import uvicorn
PY

RUN set -e; \
  build_arch="${BUILD_ARCH:-${TARGETARCH:-$(uname -m)}}"; \
  case "${build_arch}" in \
    amd64|x86_64) go2rtc_arch="amd64" ;; \
    aarch64|arm64) go2rtc_arch="arm64" ;; \
    *) echo "Unsupported architecture for go2rtc: ${build_arch}" >&2; exit 1 ;; \
  esac; \
  GO2RTC_ARCH="${go2rtc_arch}" GO2RTC_VERSION="${GO2RTC_VERSION}" "${VIRTUAL_ENV}/bin/python" - <<'PY'
import os
import shutil
import stat
import urllib.request

from toposync_ext_streaming.streaming import GO2RTC_VERSION as DEFAULT_GO2RTC_VERSION

arch = os.environ["GO2RTC_ARCH"]
version = os.environ.get("GO2RTC_VERSION") or DEFAULT_GO2RTC_VERSION
target = "/usr/local/bin/go2rtc"
temp_path = f"{target}.download"
url = f"https://github.com/AlexxIT/go2rtc/releases/download/{version}/go2rtc_linux_{arch}"
request = urllib.request.Request(
    url,
    headers={"user-agent": "toposync-homeassistant-addon/1.0", "accept": "*/*"},
    method="GET",
)
with urllib.request.urlopen(request, timeout=60.0) as response, open(temp_path, "wb") as writer:
    shutil.copyfileobj(response, writer)
os.replace(temp_path, target)
mode = os.stat(target).st_mode
os.chmod(target, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
PY

COPY run_addon.py /usr/local/bin/run_addon.py

EXPOSE 18756 18757 18758 18760
EXPOSE 18762/udp
VOLUME ["/data"]

ENTRYPOINT ["/usr/bin/tini", "-s", "--"]
CMD ["/opt/toposync/.venv/bin/python", "/usr/local/bin/run_addon.py"]
