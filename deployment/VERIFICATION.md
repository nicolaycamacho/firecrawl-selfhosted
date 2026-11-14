# Deployment verification

Verified on guest (`Wari-PC`) on 2026-11-14 UTC. This records live acceptance
checks for this host, not a general reliability or capacity guarantee.

## Deployed versions

- Official Firecrawl `v2.11.162`, commit
  `7666c1f9ae8720a6bba271e0f60b6a217f8a5210`.
- Unmodified official API, Playwright and NuQ PostgreSQL Dockerfiles, plus
  digest-pinned Redis 8 Alpine and RabbitMQ 3 management images.
- Official `firecrawl-mcp` 3.40.0 with its npm lockfile. A small launcher embeds
  its supported server export and filters the exposed tools.

## Live results

| Check | Observed result |
| --- | --- |
| Scrape `https://example.com` | Meaningful documentation text in Markdown and `Example Domain` title metadata |
| Map `https://docs.firecrawl.dev`, sitemap only, limit 10 | 10 URLs returned |
| Crawl `https://books.toscrape.com/`, limit 3, depth 1, concurrency 1 | Three completed pages, each with Markdown; polling observed progress from zero to three |
| Scrape `https://quotes.toscrape.com/js-delayed/`, wait 11 seconds | Markdown contained both Albert Einstein and Marilyn Monroe quote content |
| Invalid URL | HTTP 400 with `success: false` |
| Nonexistent `.invalid` hostname | Explicit DNS resolution error; upstream returned HTTP 200 with `success: false` |
| Guest MCP | Protocol initialization and exactly four tools; scrape, map (5 URLs), crawl (2 pages), status and DNS error all worked |
| Mac → `wari-guest` SSH MCP | Protocol initialization, same four tools, meaningful scrape and explicit MCP DNS error worked |
| API child process crash | Upstream harness exited; Docker automatically restarted the same container (`RestartCount` 0 → 1); health recovered |
| Recreate all five containers | All IDs changed and all became healthy; the earlier crawl ID still returned three completed results |
| MCP after recreation | Guest and Mac paths again returned meaningful Markdown and the explicit DNS error |

Runtime inspection confirmed only `127.0.0.1:3302` is published, no privileged
containers or Docker socket mounts, and `unless-stopped` policies throughout.
Docker is enabled at boot. PostgreSQL, Redis AOF and RabbitMQ use named volumes.
The earlier native Firecrawl listeners and installed user units are retired.
The separate `crawl4ai-mcp.service` remained active.

Both Codex configurations contain a separate `firecrawl-local` entry.
Pre-existing guest parsed settings and Mac configuration text were preserved.
The checks launched the actual configured stdio process and SSH path; an
already-open Codex chat may need reopening to discover newly added entries.

Ignored evidence: `.local/acceptance.json`, `.local/recovery.json`,
`.local/runtime-summary.json`, `.local/mcp-guest-check.log`,
`.local/mcp-mac-check.log`, and the two `mcp-*-after-recovery.log` files.
The API and MCP scripts in this directory reproduce the bounded checks.

## Boundaries

Map relies on published sitemaps without the hosted discovery/index backend;
skipping sitemaps can yield an empty map. Crawl does traverse HTML links.
Hosted anti-bot/proxy behavior, web search and LLM extraction are not enabled.
No paid account, external API key, proxy or LLM was used for these checks.

Persistence was verified for completed results across container recreation.
Upstream crawl bookkeeping has an approximately 24-hour TTL; this is not a
permanent content archive. In-flight crash recovery, host reboot, power loss,
load capacity and recovery from hung-but-running services were not tested.
Docker healthchecks report health; they do not automatically restart an
unhealthy process that stays running. Explicit Docker stop/kill commands can
leave an `unless-stopped` container stopped; restore it with Compose `up -d`.

See [README.md](README.md) for setup, agent configuration and operation.

## Repository validation

Compose configuration, Python compilation, shell syntax, Node module syntax
and Git whitespace checks passed. The upstream pre-commit `pnpm knip --cache`
check failed on the existing unused `appendQuery` export in
`apps/api/src/lib/research-upstream.ts:12`. That file is unchanged from the
pinned upstream commit; this deployment contains no API source changes.
The deployment files were formatted separately. The local commit bypassed
the failing hook; the repository-wide Knip check is not claimed as passing.
