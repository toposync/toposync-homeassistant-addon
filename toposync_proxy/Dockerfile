FROM ghcr.io/home-assistant/base:3.24

ARG BUILD_VERSION=0.1.1
LABEL io.hass.version="${BUILD_VERSION}" \
      io.hass.type="app" \
      io.hass.arch="amd64|aarch64" \
      org.opencontainers.image.title="TopoSync Remote Instance" \
      org.opencontainers.image.description="Connect Home Assistant to an existing TopoSync instance." \
      org.opencontainers.image.source="https://github.com/toposync/toposync-homeassistant-addon"

RUN apk add --no-cache nginx python3 ca-certificates
COPY run_proxy.py nginx.conf.template /usr/local/bin/
EXPOSE 8099
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1:8098/ || exit 1
ENTRYPOINT []
CMD ["python3", "/usr/local/bin/run_proxy.py"]
