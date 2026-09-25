#!/usr/bin/env bash
# Install or update Emile inside a Debian 12 LXC. Run as root from a checkout of the repo:
#
#   sudo ./deploy/install.sh                        # cloudflared in the same LXC
#   sudo EMILE_TUNNEL_IP=10.0.0.5 ./deploy/install.sh   # cloudflared on another host
#
# Idempotent: re-run after `git pull` to update. Never overwrites an existing token or env file.
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEST=/opt/emile
ETC=/etc/emile

[[ $EUID -eq 0 ]] || { echo "Run as root." >&2; exit 1; }

echo "==> Packages"
apt-get update -qq
apt-get install -y -qq python3 python3-venv rsync curl >/dev/null

echo "==> Service user"
id emile &>/dev/null || useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin emile

echo "==> Code -> $DEST (owned by root, read-only to the service)"
mkdir -p "$DEST"
rsync -a --delete --exclude .git --exclude .venv --exclude '__pycache__' --exclude tests "$SRC"/ "$DEST"/
python3 -m venv "$DEST/.venv"
"$DEST/.venv/bin/pip" install -q --upgrade pip
"$DEST/.venv/bin/pip" install -q --require-hashes -r "$DEST/requirements.txt"
chown -R root:root "$DEST"
chmod -R go-w "$DEST"

echo "==> Config in $ETC"
install -d -m 0755 "$ETC"
[[ -f $ETC/emile.env ]] || install -m 0644 "$SRC/deploy/emile.env.example" "$ETC/emile.env"
if [[ ! -f $ETC/token ]]; then
  ( umask 077; "$DEST/.venv/bin/python" -c 'import secrets; print(secrets.token_urlsafe(32))' > "$ETC/token" )
  echo "    Generated a new token in $ETC/token (root-only). Give it to clients over a secure channel."
fi
chmod 0600 "$ETC/token"

echo "==> systemd"
install -m 0644 "$SRC/deploy/emile.service" /etc/systemd/system/emile.service
if [[ -n ${EMILE_TUNNEL_IP:-} ]]; then
  install -d /etc/systemd/system/emile.service.d
  printf '[Service]\nIPAddressAllow=%s\n' "$EMILE_TUNNEL_IP" > /etc/systemd/system/emile.service.d/tunnel.conf
  echo "    Allowing traffic from tunnel host $EMILE_TUNNEL_IP. Set EMILE_HOST to this LXC's IP in $ETC/emile.env."
fi
systemctl daemon-reload
systemctl enable --now emile
systemctl restart emile
sleep 2
systemctl --no-pager --lines=5 status emile || true

PORT=$(grep -E '^EMILE_PORT=' "$ETC/emile.env" | cut -d= -f2); PORT=${PORT:-8765}
HOST=$(grep -E '^EMILE_HOST=' "$ETC/emile.env" | cut -d= -f2); HOST=${HOST:-127.0.0.1}
echo "==> Health: $(curl -fsS "http://$HOST:$PORT/healthz" || echo 'FAILED — check: journalctl -u emile')"
