#!/usr/bin/env python3
"""Bounded live acceptance checks; write evidence into ignored local state."""
import argparse
import json
from pathlib import Path
import time
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--after-restart', action='store_true')
args = parser.parse_args()
base = 'http://127.0.0.1:3302'

def request(path, data=None):
    req = urllib.request.Request(base + path,
        data=None if data is None else json.dumps(data).encode(),
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=75) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())

evidence = root / '.local/acceptance.json'
if args.after_restart:
    previous = json.loads(evidence.read_text())
    status, result = request('/v2/crawl/' + previous['crawl_id'])
    assert status == 200 and result['status'] == 'completed', result
    assert result['completed'] == previous['crawl_completed'], result
    print(json.dumps({'persisted_crawl': previous['crawl_id'], 'status': result['status'],
                      'completed': result['completed']}))
    raise SystemExit(0)

report = {'checked_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
status, result = request('/v2/scrape', {'url': 'https://example.com',
    'formats': ['markdown'], 'maxAge': 0})
assert status == 200 and result['success'], result
assert 'documentation examples' in result['data']['markdown'], result
assert result['data']['metadata']['title'] == 'Example Domain', result
report['scrape'] = {'title': result['data']['metadata']['title'],
                    'markdown_chars': len(result['data']['markdown'])}
print('PASS scrape: Markdown and title metadata', flush=True)

status, result = request('/v2/map', {'url': 'https://docs.firecrawl.dev',
    'limit': 10, 'sitemap': 'only'})
assert status == 200 and result['success'] and result['links'], result
assert len(result['links']) <= 10, result
report['map'] = {'links': len(result['links'])}
print('PASS map: bounded URL discovery', flush=True)

status, result = request('/v2/crawl', {'url': 'https://books.toscrape.com/',
    'limit': 3, 'maxDiscoveryDepth': 1, 'maxConcurrency': 1, 'sitemap': 'skip',
    'scrapeOptions': {'formats': ['markdown']}})
assert status == 200 and result['success'], result
crawl_id = result['id']
states = []
deadline = time.monotonic() + 180
while time.monotonic() < deadline:
    status, result = request('/v2/crawl/' + crawl_id)
    assert status == 200, result
    state = {'status': result['status'], 'completed': result['completed'], 'total': result['total']}
    if not states or state != states[-1]:
        states.append(state)
        print('Crawl progress: ' + json.dumps(state), flush=True)
    if result['status'] in ('completed', 'failed', 'cancelled'):
        break
    time.sleep(2)
assert result['status'] == 'completed' and 1 <= result['completed'] <= 3, result
assert result['data'] and all(page.get('markdown') for page in result['data']), result
report.update(crawl_id=crawl_id, crawl_completed=result['completed'], crawl_progress=states)
print('PASS bounded crawl and progress', flush=True)

status, result = request('/v2/scrape', {'url': 'https://quotes.toscrape.com/js-delayed/',
    'formats': ['markdown'], 'waitFor': 11000, 'timeout': 45000, 'maxAge': 0})
assert status == 200 and result['success'], result
markdown = result['data']['markdown']
assert 'Albert Einstein' in markdown and 'Marilyn Monroe' in markdown, markdown
report['delayed_javascript'] = {'wait_ms': 11000, 'markdown_chars': len(markdown),
                               'Einstein': True, 'Monroe': True}
print('PASS delayed JavaScript: meaningful quote content', flush=True)

status, result = request('/v2/scrape', {'url': 'not a valid URL'})
assert status == 400 and not result['success'], result
report['invalid_url'] = {'http_status': status, 'error': result.get('error')}
status, result = request('/v2/scrape', {'url': 'https://firecrawl-check.invalid/', 'timeout': 15000})
assert not result['success'] and result.get('error') and result.get('code') == 'SCRAPE_DNS_RESOLUTION_ERROR', result
report['dns_error'] = {'http_status': status, 'code': result['code'], 'error': result['error']}
print('PASS invalid URL and DNS error reporting', flush=True)
evidence.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
