ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.13-alpine3.22
FROM ${BUILD_FROM}

ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /opt/bridge

COPY app/requirements.txt /tmp/requirements.txt
RUN apk add --no-cache bash \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY app /opt/bridge/app
COPY rootfs/run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
