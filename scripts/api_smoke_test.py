#!/usr/bin/env python3
"""
API Smoke Test Script

Hits all registered API endpoints and verifies they return expected status codes.
Designed for Next.js API routes but works with any HTTP API.

Usage:
    python api_smoke_test.py --base-url http://localhost:3000
    python api_smoke_test.py --config endpoints.json

Exit codes:
    0 = All endpoints passed
    1 = Some endpoints failed
"""

import json
import sys
import argparse
import time
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# Default endpoints for MCW (mission-control-web)
DEFAULT_ENDPOINTS = {
    'mission-control-web': [
        {'method': 'GET', 'path': '/api/projects', 'expected': 200},
        {'method': 'GET', 'path': '/api/sessions', 'expected': 200},
        {'method': 'GET', 'path': '/api/documents', 'expected': 200},
        {'method': 'GET', 'path': '/api/feedback', 'expected': 200},
        {'method': 'GET', 'path': '/api/features', 'expected': 200},
        {'method': 'GET', 'path': '/api/health', 'expected': 200},
    ]
}


def test_endpoint(base_url: str, endpoint: dict, timeout: int = 10) -> dict:
    """Test a single endpoint."""
    url = f"{base_url.rstrip('/')}{endpoint['path']}"
    method = endpoint.get('method', 'GET')
    expected = endpoint.get('expected', 200)

    result = {
        'method': method,
        'path': endpoint['path'],
        'url': url,
        'expected': expected,
        'passed': False,
        'actual': None,
        'time_ms': None,
        'error': None
    }

    start = time.time()

    try:
        req = Request(url, method=method)
        req.add_header('Accept', 'application/json')

        with urlopen(req, timeout=timeout) as response:
            result['actual'] = response.status
            result['passed'] = response.status == expected

    except HTTPError as e:
        result['actual'] = e.code
        result['passed'] = e.code == expected
        if not result['passed']:
            try:
                result['error'] = e.read().decode('utf-8')[:200]
            except:
                result['error'] = str(e)

    except URLError as e:
        result['error'] = f"Connection failed: {e.reason}"

    except Exception as e:
        result['error'] = str(e)

    result['time_ms'] = round((time.time() - start) * 1000)

    return result


def run_smoke_test(base_url: str, endpoints: list, timeout: int = 10) -> dict:
    """Run smoke test against all endpoints."""
    results = {
        'tested_at': datetime.now().isoformat(),
        'base_url': base_url,
        'total': len(endpoints),
        'passed': 0,
        'failed': 0,
        'endpoints': []
    }

    for endpoint in endpoints:
        result = test_endpoint(base_url, endpoint, timeout)
        results['endpoints'].append(result)

        if result['passed']:
            results['passed'] += 1
        else:
            results['failed'] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description='API Smoke Test')
    parser.add_argument('--base-url', default='http://localhost:3000',
                        help='Base URL for API (default: http://localhost:3000)')
    parser.add_argument('--config', help='JSON file with endpoint definitions')
    parser.add_argument('--project', default='mission-control-web',
                        help='Project name for default endpoints')
    parser.add_argument('--timeout', type=int, default=10,
                        help='Request timeout in seconds (default: 10)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    # Load endpoints
    if args.config:
        try:
            with open(args.config) as f:
                config = json.load(f)
                endpoints = config.get('endpoints', [])
        except Exception as e:
            print(f"ERROR: Failed to load config: {e}", file=sys.stderr)
            return 1
    else:
        endpoints = DEFAULT_ENDPOINTS.get(args.project, [])
        if not endpoints:
            print(f"WARNING: No default endpoints for project '{args.project}'")
            print(f"Available projects: {list(DEFAULT_ENDPOINTS.keys())}")
            return 1

    # Run tests
    results = run_smoke_test(args.base_url, endpoints, args.timeout)

    # Output
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print("=" * 60)
        print("API Smoke Test Results")
        print(f"Base URL: {args.base_url}")
        print("=" * 60)

        for ep in results['endpoints']:
            if ep['passed']:
                status = "[PASS]"
            else:
                status = "[FAIL]"

            time_str = f"({ep['time_ms']}ms)" if ep['time_ms'] else ""
            print(f"{status} {ep['method']} {ep['path']} - {ep['actual'] or 'N/A'} {time_str}")

            if ep['error']:
                # Truncate long errors
                error = ep['error'][:100] + "..." if len(ep['error']) > 100 else ep['error']
                print(f"       Error: {error}")

        print("\n" + "=" * 60)
        print(f"Summary: {results['passed']}/{results['total']} passed")
        if results['failed'] > 0:
            print(f"         {results['failed']} FAILED")
        print("=" * 60)

    return 1 if results['failed'] > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
