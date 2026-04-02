# Homelab Deploy

This repo owns the container build and app rollout for `gomiyoubi`. The ingress is managed outside this repo, but
the exact required Caddy snippet is recorded in [`deploy/homelab.caddy.snippet`](../deploy/homelab.caddy.snippet).

## Live Shape

- Host: `homelab`
- Remote app dir: `~/gomiyoubi`
- Container name: `gomiyoubi`
- Image: `localhost/gomiyoubi:latest`
- Container port mapping: `0.0.0.0:8081 -> 80/tcp`
- Public URL: `https://gomiyoubi.homelab.iplusi.biz`
- Ingress file managed outside repo: `/home/podman/.config/containers/systemd/Caddyfile`

## Repo-Owned Deploy Path

Use only these commands:

```bash
./deploy/homelab-deploy.sh
./deploy/homelab-verify.sh
```

What `deploy/homelab-deploy.sh` does:

1. `rsync` the repo to `homelab:~/gomiyoubi`
2. `podman build -t localhost/gomiyoubi:latest -f Containerfile .`
3. replace the `gomiyoubi` container with:

```bash
podman run -d \
  --name gomiyoubi \
  --restart=always \
  -p 8081:80 \
  localhost/gomiyoubi:latest
```

4. verify local container HTTP on `127.0.0.1:8081`
5. verify the public URL returns `200`

## Previous Ad Hoc Deploy Path

This section distinguishes between what is proven from evidence and what is only inferred.

### Proven evidence

- Local shell history proves the working directory setup on `mini`:
  - `2026-04-01T05:11:58Z`: `mkdir gomiyoubi`
  - `2026-04-01T05:12:01Z`: `cd gomiyoubi`
- Remote file mtimes prove the first app sync landed on `homelab` around:
  - `2026-04-02 01:14:31 +0000`: `~/gomiyoubi`, `~/gomiyoubi/Containerfile`,
    `~/gomiyoubi/.dockerignore`, `~/gomiyoubi/deploy/nginx.conf`
- Remote ingress mtime proves the live Caddy change landed around:
  - `2026-04-02 01:17:45 +0000`: `/home/podman/.config/containers/systemd/Caddyfile`
- Remote image metadata proves the previously live app image was built at:
  - `2026-04-02 01:41:48 +0000`: `localhost/gomiyoubi:latest`

### Evidence-backed command sequence

The exact command sequence below is backed by prior Codex session logs for this repo and by the live machine state.
The path on `mini` was the repo root:

`/Volumes/MiniStorage/projects/gomiyoubi`

From `mini`:

```bash
rsync -az --delete \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='dist' \
  --exclude='/data' \
  --exclude='/docs' \
  --exclude='/scripts' \
  /Volumes/MiniStorage/projects/gomiyoubi/ homelab:~/gomiyoubi/
```

Then on `homelab`, from:

`~/gomiyoubi`

```bash
cd ~/gomiyoubi
podman build -t localhost/gomiyoubi:latest -f Containerfile .
podman rm -f gomiyoubi >/dev/null 2>&1 || true
podman run -d --name gomiyoubi --restart=always -p 8081:80 localhost/gomiyoubi:latest
curl -I --max-time 10 http://127.0.0.1:8081
```

And from `mini`:

```bash
curl -I --max-time 15 https://gomiyoubi.homelab.iplusi.biz
```

Ingress was manually added on the live host by editing:

`/home/podman/.config/containers/systemd/Caddyfile`

That ingress mutation was outside repo ownership. The exact live snippet is now recorded in
[`deploy/homelab.caddy.snippet`](../deploy/homelab.caddy.snippet).

### What is still inferred

- The exact shell prompt/session used for the initial `rsync`, `podman build`, `podman run`, and public `curl`
  is not recoverable from local shell history.
- The first remote container creation time before the current repo-owned redeploy is no longer recoverable because
  the container has since been replaced.
- The `rsync` exclusion list above is backed by prior session logs, not by shell history on `mini`.

## Drift Rules

- Do not edit the live app rollout by hand if the same change is not also committed here.
- If ingress must change, either move it into the infra repo that owns Caddy or update
  [`deploy/homelab.caddy.snippet`](../deploy/homelab.caddy.snippet) in the same change.
- Long term, the `gomiyoubi` ingress snippet should live in the homelab infra repo that owns the shared Caddyfile,
  not only in this app repo.
- Treat `~/gomiyoubi` on `homelab` as a deployment target, not the source of truth.
