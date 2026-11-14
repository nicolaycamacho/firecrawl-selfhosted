import { createFirecrawlMcpServer } from "firecrawl-mcp/server";

const tools = new Set([
  "firecrawl_scrape",
  "firecrawl_map",
  "firecrawl_crawl",
  "firecrawl_check_crawl_status",
]);

const server = createFirecrawlMcpServer({
  transport: "stdio",
  apiUrl: "http://127.0.0.1:3302",
  unstable_hooks: {
    toolFilter: (name) => tools.has(name),
    instructions:
      "Private self-hosted Firecrawl core. Scrape a known URL, map published sitemap links, or run a bounded crawl and inspect its progress. Map can return no links when sitemaps are absent or skipped because hosted discovery is not configured; use crawl for HTML link traversal. Use explicit page/depth limits. For delayed JavaScript content, pass waitFor in milliseconds and verify meaningful content. Crawl IDs expire after roughly 24 hours; save returned results when needed. No paid Firecrawl account is required. Cloud Agent, Browser/Interact, provider discovery, LLM extraction, and web search are not configured. Scrape Markdown or HTML and interpret the returned content yourself.",
  },
});
await server.start({ transportType: "stdio" });
