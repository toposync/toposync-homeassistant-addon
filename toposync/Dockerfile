ARG BUILD_ARCH
FROM python:3.12-slim-bookworm

ARG TOPOSYNC_PIP_SPEC=toposync-streaming==0.4.7
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

COPY run_addon.py /usr/local/bin/run_addon.py

EXPOSE 18756 18757 18758 18760
EXPOSE 18762/udp
VOLUME ["/data"]

ENTRYPOINT ["/usr/bin/tini", "-s", "--"]
CMD ["/opt/toposync/.venv/bin/python", "/usr/local/bin/run_addon.py"]
