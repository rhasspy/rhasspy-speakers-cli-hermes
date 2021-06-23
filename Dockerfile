# -----------------------------------------------------------------------------
# Dockerfile for Rhasspy Speakers Service
# (https://github.com/rhasspy/rhasspy-speakers-cli-hermes)
#
# Requires Docker buildx: https://docs.docker.com/buildx/working-with-buildx/
# See scripts/build-docker.sh
#
# Builds a multi-arch image for amd64/armv6/armv7/arm64.
# The virtual environment from the build stage is copied over to the run stage.
# The Rhasspy source code is then copied into the run stage and executed within
# that virtual environment.
#
# Build stages are named build-$TARGETARCH$TARGETVARIANT, so build-amd64,
# build-armv6, etc. Run stages are named similarly.
#
# armv6 images (Raspberry Pi 0/1) are derived from balena base images:
# https://www.balena.io/docs/reference/base-images/base-images/#balena-base-images
# -----------------------------------------------------------------------------

FROM debian:buster as build-ubuntu

ENV LANG C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

RUN --mount=type=cache,id=apt-build,target=/var/cache/apt \
    apt-get update && \
    apt-get install --no-install-recommends --yes \
        python3 python3-setuptools python3-pip python3-venv \
        make

FROM build-ubuntu as build-amd64

FROM build-ubuntu as build-armv7

FROM build-ubuntu as build-arm64

# -----------------------------------------------------------------------------

FROM balenalib/raspberry-pi-debian-python:3.7-buster-build as build-armv6

ENV LANG C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

# -----------------------------------------------------------------------------
# Build
# -----------------------------------------------------------------------------

ARG TARGETARCH
ARG TARGETVARIANT
FROM build-$TARGETARCH$TARGETVARIANT as build

ENV APP_DIR=/usr/lib/rhasspy-speakers-cli-hermes

COPY requirements.txt Makefile ${APP_DIR}/
COPY scripts/ ${APP_DIR}/scripts/

RUN --mount=type=cache,id=pip-build,target=/root/.cache/pip \
    cd ${APP_DIR} && \
    ./configure && \
    make && \
    make install

# -----------------------------------------------------------------------------

FROM debian:buster as run-ubuntu

ENV LANG C.UTF-8

RUN --mount=type=cache,id=apt-run,target=/var/apt/cache \
    apt-get update && \
    apt-get install --yes --no-install-recommends \
        python3 alsa-utils

FROM run-ubuntu as run-amd64

FROM run-ubuntu as run-armv7

FROM run-ubuntu as run-arm64

# -----------------------------------------------------------------------------

FROM balenalib/raspberry-pi-debian-python:3.7-buster-run as run-armv6

ENV LANG C.UTF-8

RUN --mount=type=cache,id=apt-run-armv6,target=/var/apt/cache \
    install_packages alsa-utils

# -----------------------------------------------------------------------------
# Run
# -----------------------------------------------------------------------------

ARG TARGETARCH
ARG TARGETVARIANT
FROM run-$TARGETARCH$TARGETVARIANT

ENV APP_DIR=/usr/lib/rhasspy-speakers-cli-hermes
COPY --from=build ${APP_DIR}/ ${APP_DIR}/
COPY bin/ ${APP_DIR}/bin/
COPY rhasspyspeakers_cli_hermes/ ${APP_DIR}/rhasspyspeakers_cli_hermes

ENTRYPOINT ["bash", "/usr/lib/rhasspy-speakers-cli-hermes/bin/rhasspy-speakers-cli-hermes"]
