#!/usr/bin/env bash

set -euo pipefail

REMOTE_HOST="${REMOTE_HOST:-homelab}"
REMOTE_APP_DIR="${REMOTE_APP_DIR:-~/gomiyoubi}"
CONTAINER_NAME="${CONTAINER_NAME:-gomiyoubi}"
IMAGE_NAME="${IMAGE_NAME:-localhost/gomiyoubi:latest}"
HOST_PORT="${HOST_PORT:-8081}"
PUBLIC_URL="${PUBLIC_URL:-https://gomiyoubi.homelab.iplusi.biz}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "==> Syncing repo to ${REMOTE_HOST}:${REMOTE_APP_DIR}"
rsync -aiz --delete \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='dist' \
  --exclude='/data' \
  --exclude='/docs' \
  --exclude='/scripts' \
  "${REPO_ROOT}/" "${REMOTE_HOST}:${REMOTE_APP_DIR}/"

echo "==> Building and restarting ${CONTAINER_NAME} on ${REMOTE_HOST}"
ssh "${REMOTE_HOST}" "
  set -euo pipefail
  cd ${REMOTE_APP_DIR}
  podman build -t ${IMAGE_NAME} -f Containerfile .
  podman rm -f ${CONTAINER_NAME} >/dev/null 2>&1 || true
  podman run -d \
    --name ${CONTAINER_NAME} \
    --restart=always \
    -p ${HOST_PORT}:80 \
    ${IMAGE_NAME}
  curl -I --max-time 10 http://127.0.0.1:${HOST_PORT}
"

echo "==> Verifying ${PUBLIC_URL}"
curl -I --max-time 15 "${PUBLIC_URL}"
