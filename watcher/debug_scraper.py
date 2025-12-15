"""
Debug script to see what the scraper is actually finding
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def debug_scrape(url, company_name):
    """Debug what we're actually finding on a page."""
    print(f"\n{'='*60}")
    print(f"Debugging: {company_name}")
    print(f"URL: {url}")
    print(f"{'='*60}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Find all links
            links = soup.find_all('a', href=True)
            print(f"Total links found: {len(links)}\n")

            # Look for job-related links
            job_keywords = ['2026', 'graduate', 'new grad', 'career', 'job', 'recruit', 'hiring']

            matches = []
            for link in links[:50]:  # Check first 50 links
                text = link.get_text(strip=True).lower()
                url = link['href'].lower()

                if any(keyword in text or keyword in url for keyword in job_keywords):
                    matches.append({
                        'text': link.get_text(strip=True)[:80],
                        'url': link['href'][:100]
                    })

            print(f"Potential job links found: {len(matches)}\n")

            for i, match in enumerate(matches[:10], 1):
                print(f"{i}. Text: {match['text']}")
                print(f"   URL: {match['url']}\n")

            # Check page text for keywords
            page_text = soup.get_text().lower()
            print("\nKeyword presence on page:")
            for keyword in ['2026', 'graduate', 'new grad', 'ai engineer', 'machine learning']:
                count = page_text.count(keyword)
                print(f"  '{keyword}': {count} occurrences")

            input("\nPress Enter to close browser and continue...")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()


async def main():
    # Test priority companies
    test_sites = {
        'LINE': 'https://careers.linecorp.com/jobs/',
        'Rakuten': 'https://global.rakuten.com/corp/careers/graduates',
        'Mercari': 'https://careers.mercari.com/',
    }

    for company, url in test_sites.items():
        await debug_scrape(url, company)
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
