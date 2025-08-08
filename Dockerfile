##################################################
# Stage: uv
# From: ghcr.io/astral-sh/uv:python3.13-alpine
##################################################
FROM ghcr.io/astral-sh/uv:python3.13-alpine@sha256:30b0d0f67eb7a5f79325709fff1bb0a93c991674b0caf04ef4017e7ee5b44be4 AS uv

##################################################
# Stage: builder
# From: docker.io/python:3.13-alpine3.22
##################################################
FROM docker.io/python:3.13-alpine3.22@sha256:f196fd275fdad7287ccb4b0a85c2e402bb8c794d205cf6158909041c1ee9f38d AS builder

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

FROM docker.io/python:3.13-alpine3.22@sha256:f196fd275fdad7287ccb4b0a85c2e402bb8c794d205cf6158909041c1ee9f38d AS final

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
