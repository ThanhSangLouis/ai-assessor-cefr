#!/usr/bin/env bash
# Prepare a fresh Ubuntu 24.04 server for AI Assessor CEFR (D047). Run as root:
#
#   scp deploy/vps/bootstrap.sh root@HOST:/root/ && ssh root@HOST bash /root/bootstrap.sh
#
# Idempotent: running it again changes nothing that is already in place.
# Installs Docker Engine and the compose plugin from Docker's own apt repository,
# creates the deploy user `aicefr` (docker group), opens only SSH, 80 and 443,
# turns on unattended security upgrades and adds a 4 GB swap file when the
# machine has no swap. Does not touch SSH settings: do that deliberately.
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-aicefr}"
APP_DIR="${APP_DIR:-/srv/aicefr}"
BACKUP_DIR="${BACKUP_DIR:-/srv/aicefr-backups}"
SWAP_FILE="/swapfile"
SWAP_SIZE="4G"

step() { printf '\n==> %s\n' "$*"; }

if [[ "$(id -u)" -ne 0 ]]; then
  echo "bootstrap.sh: run as root (sudo bash bootstrap.sh)" >&2
  exit 1
fi
# shellcheck source=/dev/null
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "bootstrap.sh: written for Ubuntu 24.04, found ${PRETTY_NAME:-unknown}" >&2
  exit 1
fi
if [[ "${VERSION_ID:-}" != "24.04" ]]; then
  echo "bootstrap.sh: warning: tested on Ubuntu 24.04, this is ${VERSION_ID:-unknown}" >&2
fi

export DEBIAN_FRONTEND=noninteractive

step "Base packages"
apt-get update -q
apt-get install -y -q ca-certificates curl gnupg rsync ufw unattended-upgrades python3

step "Docker's apt repository"
install -m 0755 -d /etc/apt/keyrings
if [[ ! -s /etc/apt/keyrings/docker.asc ]]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
fi
ARCH="$(dpkg --print-architecture)"
CODENAME="${UBUNTU_CODENAME:-$VERSION_CODENAME}"
echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
  >/etc/apt/sources.list.d/docker.list

step "Docker Engine and the compose plugin"
apt-get update -q
apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker --version
docker compose version

step "Deploy user '${DEPLOY_USER}' in the docker group"
if ! id -u "$DEPLOY_USER" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$DEPLOY_USER"
fi
usermod -aG docker "$DEPLOY_USER"
# The same SSH keys as root, so `deploy.sh aicefr@HOST` works straight away.
if [[ -s /root/.ssh/authorized_keys ]]; then
  install -d -m 0700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/${DEPLOY_USER}/.ssh"
  touch "/home/${DEPLOY_USER}/.ssh/authorized_keys"
  while IFS= read -r key; do
    [[ -z "$key" ]] && continue
    grep -qxF "$key" "/home/${DEPLOY_USER}/.ssh/authorized_keys" \
      || printf '%s\n' "$key" >>"/home/${DEPLOY_USER}/.ssh/authorized_keys"
  done </root/.ssh/authorized_keys
  chown "$DEPLOY_USER:$DEPLOY_USER" "/home/${DEPLOY_USER}/.ssh/authorized_keys"
  chmod 0600 "/home/${DEPLOY_USER}/.ssh/authorized_keys"
fi

step "Application and backup directories"
install -d -m 0750 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$APP_DIR"
install -d -m 0700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$BACKUP_DIR"

step "Firewall: OpenSSH, 80 and 443 only"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable
ufw status verbose
# Note: ports Docker publishes bypass ufw (Docker writes its own iptables rules).
# Only Caddy publishes ports in docker-compose.prod.yml, and only 80 and 443.

step "Unattended security upgrades"
cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF
systemctl enable --now unattended-upgrades

step "Swap"
if [[ -n "$(swapon --show --noheadings)" ]]; then
  echo "swap already present:"
  swapon --show
else
  if [[ ! -f "$SWAP_FILE" ]]; then
    fallocate -l "$SWAP_SIZE" "$SWAP_FILE" || dd if=/dev/zero of="$SWAP_FILE" bs=1M count=4096
    chmod 600 "$SWAP_FILE"
    mkswap "$SWAP_FILE"
  fi
  swapon "$SWAP_FILE"
  grep -qE "^${SWAP_FILE}[[:space:]]" /etc/fstab || echo "${SWAP_FILE} none swap sw 0 0" >>/etc/fstab
  swapon --show
fi
# Prefer RAM; swap is for the moment Whisper loads, not for steady use.
echo "vm.swappiness=10" >/etc/sysctl.d/90-aicefr-swap.conf
sysctl -q --system

step "Done"
echo "Next, from your own machine: deploy/vps/deploy.sh ${DEPLOY_USER}@<this server> ${APP_DIR}"
echo "(first create ${APP_DIR}/.env on this server from .env.production.example)"
