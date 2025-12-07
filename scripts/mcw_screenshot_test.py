#!/usr/bin/env python3
"""
MCW Screenshot Test - Capture and analyze Mission Control Web UI

This script captures screenshots of all MCW pages for analysis.
"""

import asyncio
import sys
import io
from playwright.async_api import async_playwright
import os

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SCREENSHOTS_DIR = r"C:\Projects\claude-family\test-results\mcw-screenshots"

async def capture_mcw():
    """Capture screenshots of all MCW pages."""
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()

        pages_to_capture = [
            ("home", "http://localhost:3000/"),
            ("projects", "http://localhost:3000/projects"),
            ("sessions", "http://localhost:3000/sessions"),
            ("documents", "http://localhost:3000/documents"),
            ("feedback", "http://localhost:3000/feedback"),
            ("features", "http://localhost:3000/features"),
            ("tasks", "http://localhost:3000/tasks"),
            ("governance", "http://localhost:3000/governance"),
            ("knowledge", "http://localhost:3000/knowledge"),
        ]

        results = []

        for name, url in pages_to_capture:
            try:
                print(f"Capturing {name}...")
                response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)

                # Wait a bit for any dynamic content
                await page.wait_for_timeout(1000)

                # Get page title
                title = await page.title()

                # Get main content text (for analysis)
                content = await page.inner_text('body')

                # Take screenshot
                screenshot_path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
                await page.screenshot(path=screenshot_path, full_page=True)

                status = response.status if response else "unknown"
                results.append({
                    'name': name,
                    'url': url,
                    'status': status,
                    'title': title,
                    'screenshot': screenshot_path,
                    'content_preview': content[:500] if content else "No content"
                })
                print(f"  ✓ {name}: {status} - {title}")

            except Exception as e:
                print(f"  ✗ {name}: ERROR - {str(e)[:100]}")
                results.append({
                    'name': name,
                    'url': url,
                    'status': 'error',
                    'error': str(e)
                })

        await browser.close()

        return results


async def analyze_documents_page():
    """Deep dive into documents page to understand core vs non-core."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto("http://localhost:3000/documents", wait_until='networkidle')
        await page.wait_for_timeout(2000)

        # Get all document entries
        content = await page.inner_text('body')

        # Take full page screenshot
        screenshot_path = os.path.join(SCREENSHOTS_DIR, "documents_full.png")
        await page.screenshot(path=screenshot_path, full_page=True)

        await browser.close()

        return content


if __name__ == "__main__":
    print("=" * 60)
    print("MCW Screenshot Capture")
    print("=" * 60)

    results = asyncio.run(capture_mcw())

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    for r in results:
        status = "✓" if r.get('status') == 200 else "✗"
        print(f"{status} {r['name']}: {r.get('title', r.get('error', 'unknown'))}")

    print(f"\nScreenshots saved to: {SCREENSHOTS_DIR}")

    # Also capture documents detail
    print("\nAnalyzing documents page...")
    doc_content = asyncio.run(analyze_documents_page())
    print(f"Documents page content length: {len(doc_content)} chars")
