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

echo "==> Local deploy-critical checksums"
(
  cd "${REPO_ROOT}"
  sha256sum Containerfile deploy/nginx.conf
)

echo "==> Remote container and deploy file state"
ssh "${REMOTE_HOST}" "
  set -euo pipefail
  cd ${REMOTE_APP_DIR}
  podman ps --filter name=${CONTAINER_NAME} --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'
  podman inspect ${CONTAINER_NAME} --format 'Name={{.Name}} Image={{.Config.Image}} Ports={{json .NetworkSettings.Ports}} Cmd={{json .Config.Cmd}}'
  sha256sum Containerfile deploy/nginx.conf
  curl -I --max-time 10 http://127.0.0.1:${HOST_PORT}
"

echo "==> Public URL"
curl -I --max-time 15 "${PUBLIC_URL}"

