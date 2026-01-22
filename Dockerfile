##################################################
# Stage: uv
# From: ghcr.io/astral-sh/uv:python3.13-alpine
##################################################
FROM ghcr.io/astral-sh/uv:python3.13-alpine@sha256:77ea271de1d3b0a7f2cfbfd5d127a576f8545301fc23e1d1e9b5e79cbdf186d9 AS uv

##################################################
# Stage: builder
# From: docker.io/python:3.13-alpine3.22
##################################################
FROM docker.io/python:3.14-alpine3.22@sha256:91859223a313a4407c239afb3a8e68bddc3dbfb0d24ddc5bdeb029136b55b150 AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE="copy"

WORKDIR /app

COPY --from=uv /usr/local/bin/uv /usr/local/bin/uv

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
<<EOF
uv sync --locked --no-install-project --no-editable --no-dev
EOF

##################################################
# Stage: final
# From: docker.io/python:3.13-alpine3.22
##################################################
#checkov:skip=CKV_DOCKER_2: HEALTHCHECK not required for one-time execution container running a Python script

FROM docker.io/python:3.14-alpine3.22@sha256:91859223a313a4407c239afb3a8e68bddc3dbfb0d24ddc5bdeb029136b55b150 AS final

LABEL org.opencontainers.image.vendor="Ministry of Justice" \
      org.opencontainers.image.authors="Analytical Platform <analytical-platform@justice.gov.uk>" \
      org.opencontainers.image.title="PagerDuty Rota Notifier" \
      org.opencontainers.image.description="Notifies a Slack channel who is on-call" \
      org.opencontainers.image.url="https://github.com/ministryofjustice/pagerduty-rota-notifier"

ENV CONTAINER_USER="nonroot" \
    CONTAINER_UID="65532" \
    CONTAINER_GROUP="nonroot" \
    CONTAINER_GID="65532" \
    APP_HOME="/app" \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN <<EOF
addgroup -g ${CONTAINER_GID} ${CONTAINER_GROUP}

adduser -D -H -u ${CONTAINER_UID} -G ${CONTAINER_GROUP} ${CONTAINER_USER}

install --directory --mode=0755 --owner="${CONTAINER_USER}" --group="${CONTAINER_GROUP}" "${APP_HOME}"
EOF

WORKDIR ${APP_HOME}
COPY --from=builder --chown=${CONTAINER_UID}:${CONTAINER_GID} /app/.venv /app/.venv
COPY --chown=${CONTAINER_UID}:${CONTAINER_GID} main.py /app

USER ${CONTAINER_UID}

ENTRYPOINT ["python", "main.py"]
