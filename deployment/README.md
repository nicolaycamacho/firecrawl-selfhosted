# Private self-hosted Firecrawl

Upstream: <https://github.com/firecrawl/firecrawl>, release `v2.11.162`,
commit `7666c1f9ae8720a6bba271e0f60b6a217f8a5210`.
The upstream source and AGPL license are retained. The MCP adapter is the
official `firecrawl-mcp` npm package, pinned to `3.40.0` with a lockfile.

## Deployment

`compose.yaml` builds the unmodified official API, Playwright and PostgreSQL
Dockerfiles. Redis and RabbitMQ complete the five-service upstream stack.
FoundationDB, Supabase, paid proxies and LLM services are not required here.
The API binds only to **127.0.0.1:3302** on the guest host. No dependency port
is published. The API has database authentication disabled, so keep this
loopback binding and use the existing authenticated SSH connection.

Prerequisites: Docker Engine and Compose (already installed on this host),
with permission to use the Docker socket. Admin group membership alone does
not provide unattended sudo access. Never put a sudo password in these files.

Docker's standard durable access prerequisite is for the user to run
`sudo usermod -aG docker guest` interactively, then refresh group credentials
with a new login/SSH session (or `newgrp docker`). The Docker group grants
root-level Docker access. Do not use temporary socket permissions as the
normal setup. See <https://docs.docker.com/engine/install/linux-postinstall/>.

Guest is now a Docker group member. An already-open shell with stale group
credentials can run a command as `sg docker -c 'deployment/scripts/compose ps'`.

```sh
cd /home/guest/agent-work/workspaces/firecrawl-selfhosted
deployment/scripts/setup-env
deployment/scripts/compose config --quiet
deployment/scripts/compose up -d --build
deployment/scripts/compose ps
```

All five services use `restart: unless-stopped`. Docker's system service is
enabled on this host. Named volumes hold PostgreSQL, Redis AOF and RabbitMQ
state. Normal `stop`, `restart`, and `down` retain these volumes; **`down -v`
deletes them**. Restart policies provide automatic process/daemon recovery;
they do not prove recovery from every host failure.

Upstream crawl bookkeeping expires after roughly 24 hours; the persistent
volumes preserve state across container recreation, not indefinite crawl
history. Save returned Markdown/results separately when you need an archive.

The browser allows two concurrent pages, and the API uses one scrape queue
worker for light personal use. PostgreSQL WAL bounds are reduced from
upstream defaults.
Per-service memory caps and rotating Docker logs keep the footprint bounded.
No core API implementation or browser installation patches are required.

Secrets are generated once in ignored `.local/compose.env`, mode 600. Do not
commit or display that file. The random `BULL_AUTH_KEY` protects the queue
admin path; no extra admin UI is deployed. Existing Crawl4AI, SSH, Tailscale,
and the host's existing database services are independent of this stack.

## Agent access

The official MCP package is embedded with its supported server export and
tool filter. It targets `http://127.0.0.1:3302` explicitly; it does not fall
back to Firecrawl Cloud. The four exposed tools are:

- `firecrawl_scrape`: Markdown/HTML and metadata from one URL.
- `firecrawl_map`: discover URLs on a known site.
- `firecrawl_crawl`: bounded multi-page crawl.
- `firecrawl_check_crawl_status`: progress/results for a crawl ID.

Map works with a published sitemap (use `sitemap: "only"` for that case).
The upstream implementation otherwise consults its hosted discovery/index
backend. With no such backend configured, `sitemap: "skip"` can return an
empty list even when a page contains links. Use a bounded crawl for HTML
link traversal. This deployment does not add an alternative discovery engine.

Cloud Agent, Browser/Interact, Alexandria, billing and provider tools are
excluded. Web search is not configured or validated. LLM-based JSON extraction
requires an optional compatible provider; agents can extract fields from the
returned Markdown themselves. The public stack does not include the hosted
Fire-engine anti-bot/proxy system, so site blocking remains possible.

Install the locked adapter dependencies and record the Node executable:

```sh
npm ci --prefix deployment/mcp
command -v node > .local/node-path
```

Guest Codex entry (add separately; preserve existing entries):

```toml
[mcp_servers.firecrawl-local]
command = "/home/guest/agent-work/workspaces/firecrawl-selfhosted/deployment/scripts/mcp-stdio"
startup_timeout_sec = 20
tool_timeout_sec = 240
```

Mac Codex can launch the same stdio process through the existing SSH alias:

```toml
[mcp_servers.firecrawl-local]
command = "/usr/bin/ssh"
args = ["-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=3", "wari-guest", "/home/guest/agent-work/workspaces/firecrawl-selfhosted/deployment/scripts/mcp-stdio"]
startup_timeout_sec = 30
tool_timeout_sec = 240
```

New MCP entries may require reopening/reloading Codex to appear in an existing
chat. The direct protocol checks below work without reloading the app.

## Verification and operation

```sh
python3 deployment/scripts/check-api.py
python3 deployment/scripts/check-mcp.py --full
deployment/scripts/compose restart
python3 deployment/scripts/check-api.py --after-restart
deployment/scripts/compose ps
```

The API check covers Markdown plus title metadata, bounded mapping, a crawl
limited to three pages with progress polling, delayed JavaScript content using
an 11-second wait, invalid input and DNS errors. Evidence is saved in ignored
`.local/acceptance.json`. The post-restart check confirms the recorded crawl
remains readable. The full MCP check verifies protocol initialization, the
exact tool list, a real scrape, a useful error, map, crawl and status. These
are acceptance checks for the deployed stack, not a broad reliability or
load benchmark.

Use explicit crawl limits and verify useful content. An HTTP 200 by itself
does not establish that delayed content was captured. In this pinned version,
a DNS scrape failure can return HTTP 200 with `success: false` and a useful
`SCRAPE_DNS_RESOLUTION_ERROR`; inspect the response body too.

## Setup status and earlier native attempt

The original guest-only native attempt encountered Ubuntu 26.04 browser
installer detection, Koffi packaging/execstack compatibility and relocated
Erlang launcher issues. A direct browser test subsequently returned all ten
delayed quotes, and the database/broker started. The API itself was never
built or started; no crawl-engine defect was reproduced.

The active deployment is Compose. The earlier native user units were stopped,
removed from the user service directory, and archived with their scaffolding
under ignored `.local/native-attempt`. Native state remains ignored for
diagnostic reference. `crawl4ai-mcp.service` remains active and independent.
See [VERIFICATION.md](VERIFICATION.md) for the completed acceptance checks and
the limits of that evidence.
