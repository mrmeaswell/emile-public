# Deploying Emile to a remote server

This guide sets Emile up as a remote MCP server in an **unprivileged Proxmox LXC** on the bknown cluster, reachable over **streamable HTTP** through **Cloudflare Tunnel with authentication**.

**Analogy: three locks on one door.**
1. **Cloudflare Tunnel** is a private hallway. The server has no open port on the internet; Cloudflare walks visitors in.
2. **Cloudflare Access** is the front desk. It checks who someone is before they reach the hallway.
3. **Emile's token** is the key to the room itself. Even someone who gets past the desk still needs it.

Any one lock can fail without the room being exposed.

```
Claude Code / Copilot Studio
        │  HTTPS + Access credentials + token
        ▼
Cloudflare edge ── Access policy
        │  tunnel (outbound-only from your side)
        ▼
cloudflared ──► emile LXC :8765  (server.py --transport http, systemd, non-root)
                  └─ no outbound network needed
```

---

## 1. Create the LXC (on the Proxmox host)

Resource limits keep a runaway process from starving the node. `unprivileged=1` means root in the container isn't root on the host.

```bash
pveam update && pveam available | grep debian-12      # pick the current Debian 12 template
pveam download local debian-12-standard_12.*_amd64.tar.zst

pct create 160 local:vztmpl/debian-12-standard_12.*_amd64.tar.zst \
  --hostname emile --unprivileged 1 --features nesting=1 \
  --cores 1 --memory 512 --swap 0 --rootfs local-lvm:4 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp,firewall=1 \
  --onboot 1
pct start 160
```

Replace `160` with a free CT ID. Don't add bind mounts; Emile needs nothing from the host.

## 2. Install Emile (inside the LXC)

```bash
pct enter 160
apt-get update && apt-get install -y git
git clone https://github.com/mrmeaswell/emile-public.git /root/emile
cd /root/emile
./deploy/install.sh
```

The script:
- creates a non-root `emile` system user
- copies the code to `/opt/emile` (owned by root, read-only to the service)
- builds a venv and installs dependencies with `--require-hashes`, so a tampered package fails to install
- writes `/etc/emile/emile.env` (settings) and `/etc/emile/token` (a random 32-byte token, `0600`)
- installs and starts the hardened `emile.service` unit
- checks `http://127.0.0.1:8765/healthz`

**To update later:** `cd /root/emile && git pull && ./deploy/install.sh`. The script never overwrites your token or env file.

**Read the token** (to give to clients over a secure channel): `cat /etc/emile/token`

## 3. Choose where cloudflared runs

| | **A. Same LXC** | **B. Separate tunnel host** (recommended) |
|---|---|---|
| `EMILE_HOST` in `/etc/emile/emile.env` | `127.0.0.1` | this LXC's LAN IP |
| Install command | `./deploy/install.sh` | `EMILE_TUNNEL_IP=<tunnel-host-ip> ./deploy/install.sh` |
| Egress deny for the whole LXC | ❌ cloudflared needs outbound | ✅ Emile's LXC can drop all outbound |

**Why B is recommended:** the security baseline says Emile's egress is *deny all*. cloudflared needs outbound connections to Cloudflare, so putting it in the same container means the container can't fully deny egress. The systemd unit still restricts the Emile *service* to localhost (`IPAddressDeny=any`). However, these BPF filters may not work inside an unprivileged LXC; systemd logs a warning and continues. A container-level firewall rule is the guarantee.

After editing `/etc/emile/emile.env`: `systemctl restart emile`.

## 4. Deny egress with the Proxmox firewall (option B)

On the Proxmox host, create `/etc/pve/firewall/160.fw`:

```ini
[OPTIONS]
enable: 1
policy_in: DROP
policy_out: DROP

[RULES]
IN ACCEPT -source <tunnel-host-ip> -p tcp -dport 8765 -log nolog
IN ACCEPT -source <admin-subnet> -p tcp -dport 22 -log nolog
```

This drops all outbound traffic from the container, including DNS. Temporarily allow outbound (or use a local apt mirror) when you run `install.sh` for updates, then re-close it.

## 5. Cloudflare Tunnel + Access

1. **Tunnel.** On the tunnel host, `cloudflared tunnel create emile`, then use [`deploy/cloudflared-config.example.yml`](deploy/cloudflared-config.example.yml) as `/etc/cloudflared/config.yml`. Point `service:` at `http://<emile-lxc-ip>:8765` (B) or `http://127.0.0.1:8765` (A). Then run `cloudflared tunnel route dns emile emile.example.com`.
2. **Tell Emile its public name.** In `/etc/emile/emile.env`, set `EMILE_ALLOWED_HOSTS=emile.example.com`. Requests with any other `Host` header get `421`, which blocks DNS-rebinding tricks.
3. **Access application.** In Zero Trust → Access → Applications, add a self-hosted app for `emile.example.com`:
   - People (browser-based clients): an Allow policy for your identity provider's group.
   - Programs (Claude Code, Copilot Studio): create a **Service Token** and add a *Service Auth* policy for it. Clients then send `CF-Access-Client-Id` and `CF-Access-Client-Secret` headers.
   - Leave `/healthz` behind Access too, unless an external monitor needs it.

**Never** expose port 8765 directly or run the tunnel without Access. An open endpoint is out of bounds even with the token.

## 6. Connect clients

**Claude Code** (`.mcp.json`; keep secrets in environment variables, not in the file):

```json
{
  "mcpServers": {
    "emile": {
      "type": "http",
      "url": "https://emile.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${EMILE_TOKEN}",
        "CF-Access-Client-Id": "${CF_ACCESS_CLIENT_ID}",
        "CF-Access-Client-Secret": "${CF_ACCESS_CLIENT_SECRET}"
      }
    }
  }
}
```

**Copilot Studio (Lane 2):** add an MCP server tool with URL `https://emile.example.com/mcp`, choose **API key** auth, header name `X-API-Key`, and paste the token. Cloudflare Access service-token headers may need a custom connector; verify in your tenant (see DECISIONS.md #4). Paste `data/emile-system.md` into the agent's instructions.

## 7. Verify

```bash
# inside the LXC
systemctl status emile
journalctl -u emile -n 50
curl -s http://127.0.0.1:8765/healthz                         # ok
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8765/mcp   # 401 (no token)

# from your laptop, through Cloudflare
curl -s -o /dev/null -w '%{http_code}\n' https://emile.example.com/mcp       # 302/403 from Access
```

Then in Claude Code run `/mcp`. You should see `emile` with 7 tools.

## Security baseline checklist

| Control | How it's met |
|---|---|
| Least privilege | All tools read-only; no Canvas, file-write, or shell tools; service runs as `emile` with no capabilities |
| Secrets | None for outbound calls (thin server). The inbound token is a systemd credential in `/etc/emile/token` (`0600`), never in git or the environment |
| Supply chain | Every dependency pinned **with hashes**; no `npx`/`uvx` launchers; CI actions pinned by commit SHA |
| Isolation | Unprivileged LXC with core/memory limits; `ProtectSystem=strict`, `ReadOnlyPaths=/opt/emile`, `NoNewPrivileges`, no bind mounts |
| Egress | Denied at the Proxmox firewall (option B) and, where supported, by the systemd unit |
| Exposure | Only via Cloudflare Tunnel + Access + token; Host header allowlist |
| Data | Instructor-facing only; FERPA note appears in the server instructions and validator tool descriptions |
| Injection | Pasted vendor docs are treated as data; tool descriptions are short and factual |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Service exits with "HTTP mode needs a token of 32+ characters" | `/etc/emile/token` is missing or short; re-run `install.sh` |
| `421 Misdirected Request` | Public hostname not listed in `EMILE_ALLOWED_HOSTS` |
| `401 unauthorized` | Missing or wrong `Authorization: Bearer` / `X-API-Key` header |
| Tunnel shows 502 | `EMILE_HOST` is `127.0.0.1` but cloudflared is on another host (set the LAN IP), or the firewall is blocking 8765 |
| `IPAddressDeny` warning in the journal | BPF filters are unavailable in an unprivileged LXC; rely on the Proxmox firewall (step 4) |
