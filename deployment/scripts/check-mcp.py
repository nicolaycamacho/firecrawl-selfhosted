#!/usr/bin/env python3
"""Exercise the real stdio protocol locally or through an SSH command."""
import argparse
import json
from pathlib import Path
import queue
import subprocess
import threading

parser = argparse.ArgumentParser()
parser.add_argument('--live', action='store_true', help='Also fetch a real page')
parser.add_argument('--full', action='store_true', help='Also map, crawl and read crawl status')
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
command = args.command or [str(root / 'deployment/scripts/mcp-stdio')]
if command[0] == '--':
    command = command[1:]
messages = queue.Queue()
with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                      stderr=subprocess.PIPE, text=True, bufsize=1) as process:
    def read_output():
        for line in process.stdout:
            try:
                messages.put(json.loads(line))
            except json.JSONDecodeError:
                messages.put({'unexpected_stdout': line[:200]})
        messages.put({'closed': True})

    threading.Thread(target=read_output, daemon=True).start()

    def send(message):
        process.stdin.write(json.dumps(message) + '\n')
        process.stdin.flush()

    def call(number, method, params):
        send({'jsonrpc': '2.0', 'id': number, 'method': method, 'params': params})
        while True:
            result = messages.get(timeout=120)
            if result.get('id') == number:
                assert 'error' not in result, result
                return result['result']
            assert 'closed' not in result and 'unexpected_stdout' not in result, result

    try:
        init = call(1, 'initialize', {'protocolVersion': '2025-06-18',
                    'capabilities': {}, 'clientInfo': {'name': 'local-firecrawl-check', 'version': '1'}})
        send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        listed = call(2, 'tools/list', {})
        names = sorted(tool['name'] for tool in listed['tools'])
        assert names == sorted(['firecrawl_scrape', 'firecrawl_map', 'firecrawl_crawl',
                                'firecrawl_check_crawl_status']), names
        summary = {'protocol': init['protocolVersion'], 'tools': names}
        if args.live or args.full:
            result = call(3, 'tools/call', {'name': 'firecrawl_scrape', 'arguments': {
                'url': 'https://example.com', 'formats': ['markdown'], 'maxAge': 0}})
            assert not result.get('isError'), result
            assert 'Example Domain' in json.dumps(result) and 'documentation examples' in json.dumps(result), result
            summary['scrape'] = 'Example Domain content returned'
            failure = call(4, 'tools/call', {'name': 'firecrawl_scrape', 'arguments': {
                'url': 'https://firecrawl-check.invalid/', 'timeout': 15000}})
            assert failure.get('isError') and 'DNS resolution failed' in json.dumps(failure), failure
            summary['dns_error'] = 'Reported through MCP'
        if args.full:
            def tool(number, name, arguments):
                result = call(number, 'tools/call', {'name': name, 'arguments': arguments})
                assert not result.get('isError'), result
                return result.get('structuredContent') or json.loads(result['content'][0]['text'])

            mapped = tool(5, 'firecrawl_map', {'url': 'https://docs.firecrawl.dev',
                          'limit': 5, 'sitemap': 'only'})
            assert mapped.get('links') and len(mapped['links']) <= 5, mapped
            crawled = tool(6, 'firecrawl_crawl', {'url': 'https://books.toscrape.com/',
                'limit': 2, 'maxDiscoveryDepth': 1, 'maxConcurrency': 1, 'sitemap': 'skip',
                'scrapeOptions': {'formats': ['markdown']}})
            assert crawled['status'] == 'completed' and 1 <= crawled['completed'] <= 2, crawled
            assert crawled['data'] and all(page.get('markdown') for page in crawled['data']), crawled
            checked = tool(7, 'firecrawl_check_crawl_status', {'id': crawled['id']})
            assert checked['status'] == 'completed' and checked['completed'] == crawled['completed'], checked
            summary.update(map_links=len(mapped['links']), crawl_id=crawled['id'],
                           crawl_completed=crawled['completed'], crawl_status=checked['status'])
        print(json.dumps(summary, indent=2))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
