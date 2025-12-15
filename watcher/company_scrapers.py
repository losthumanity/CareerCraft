"""
Company-Specific Job Scrapers
Each company has unique job board structure - need custom scraping logic
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class CompanyScrapers:
    """Collection of company-specific scraping strategies."""

    @staticmethod
    async def scrape_line(browser) -> List[Dict]:
        """
        LINE Corporation new graduate positions.
        They use a dedicated careers portal.
        """
        jobs = []
        page = await browser.new_page()

        try:
            # Real job listing page (not just the landing page)
            await page.goto('https://careers.linecorp.com/jobs/', timeout=30000)
            await page.wait_for_timeout(3000)

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # LINE uses specific job card structure
            job_cards = soup.find_all(['div', 'article'], class_=lambda x: x and 'job' in str(x).lower())

            for card in job_cards:
                title_elem = card.find(['h2', 'h3', 'a'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link_elem = card.find('a', href=True) or title_elem

                    if link_elem and link_elem.get('href'):
                        url = link_elem['href']
                        if not url.startswith('http'):
                            url = f"https://linecorp.com{url}"

                        # Get full text of card for matching
                        card_text = card.get_text(strip=True)

                        jobs.append({
                            'company': 'LY Corporation (LINE)',
                            'title': title,
                            'url': url,
                            'text': card_text
                        })

            logger.info(f"  LINE: Found {len(jobs)} job listings")

        except Exception as e:
            logger.error(f"  LINE: Error - {e}")
        finally:
            await page.close()

        return jobs

    @staticmethod
    async def scrape_rakuten(browser) -> List[Dict]:
        """
        Rakuten new graduate program.
        Uses external Axol recruiting platform.
        """
        jobs = []
        page = await browser.new_page()

        try:
            # Rakuten's actual job portal (English)
            await page.goto('https://global.rakuten.com/corp/careers/opportunities/', timeout=30000)
            await page.wait_for_timeout(3000)

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Look for job listings
            job_links = soup.find_all('a', href=True)

            for link in job_links:
                text = link.get_text(strip=True)
                url = link['href']

                # Filter for relevant jobs
                if any(word in text.lower() for word in ['graduate', 'engineer', 'developer', 'ai', 'ml', 'data']):
                    if not url.startswith('http'):
                        url = f"https://global.rakuten.com{url}"

                    jobs.append({
                        'company': 'Rakuten Group',
                        'title': text,
                        'url': url,
                        'text': text
                    })

            logger.info(f"  Rakuten: Found {len(jobs)} job listings")

        except Exception as e:
            logger.error(f"  Rakuten: Error - {e}")
        finally:
            await page.close()

        return jobs

    @staticmethod
    async def scrape_mercari(browser) -> List[Dict]:
        """
        Mercari careers page.
        Uses Greenhouse.io for job listings.
        """
        jobs = []
        page = await browser.new_page()

        try:
            # Mercari's Greenhouse job board
            await page.goto('https://boards.greenhouse.io/mercari', timeout=30000)
            await page.wait_for_timeout(3000)

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Greenhouse uses specific structure
            job_sections = soup.find_all('div', class_='opening')

            for job in job_sections:
                title_elem = job.find('a')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')

                    if not url.startswith('http'):
                        url = f"https://boards.greenhouse.io{url}"

                    jobs.append({
                        'company': 'Mercari',
                        'title': title,
                        'url': url,
                        'text': job.get_text(strip=True)
                    })

            logger.info(f"  Mercari: Found {len(jobs)} job listings")

        except Exception as e:
            logger.error(f"  Mercari: Error - {e}")
        finally:
            await page.close()

        return jobs

    @staticmethod
    async def scrape_sony(browser) -> List[Dict]:
        """
        Sony new graduate recruitment.
        """
        jobs = []
        page = await browser.new_page()

        try:
            # Sony's new grad page
            await page.goto('https://www.sony.com/en/SonyInfo/CorporateInfo/Careers/newgrads/', timeout=30000)
            await page.wait_for_timeout(3000)

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Sony structure varies by region
            job_links = soup.find_all('a', href=True)

            for link in job_links:
                text = link.get_text(strip=True)
                url = link['href']

                if any(word in text.lower() for word in ['graduate', 'recruitment', 'application', 'career']):
                    if not url.startswith('http'):
                        if url.startswith('//'):
                            url = f"https:{url}"
                        else:
                            url = f"https://www.sony.com{url}"

                    jobs.append({
                        'company': 'Sony',
                        'title': text,
                        'url': url,
                        'text': text
                    })

            logger.info(f"  Sony: Found {len(jobs)} job listings")

        except Exception as e:
            logger.error(f"  Sony: Error - {e}")
        finally:
            await page.close()

        return jobs

    @staticmethod
    async def scrape_bytedance(browser) -> List[Dict]:
        """
        ByteDance (TikTok) graduate program.
        """
        jobs = []
        page = await browser.new_page()

        try:
            # ByteDance career site with graduate filter
            await page.goto('https://jobs.bytedance.com/en/position?keywords=&category=&location=&project=&type=2', timeout=30000)
            await page.wait_for_timeout(5000)  # JS-heavy site

            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # ByteDance uses job cards
            job_cards = soup.find_all(['div', 'article'], class_=lambda x: x and 'job' in str(x).lower())

            for card in job_cards:
                title_elem = card.find(['h3', 'h4', 'a'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = card.find('a', href=True)

                    if link:
                        url = link['href']
                        if not url.startswith('http'):
                            url = f"https://jobs.bytedance.com{url}"

                        jobs.append({
                            'company': 'ByteDance (TikTok)',
                            'title': title,
                            'url': url,
                            'text': card.get_text(strip=True)
                        })

            logger.info(f"  ByteDance: Found {len(jobs)} job listings")

        except Exception as e:
            logger.error(f"  ByteDance: Error - {e}")
        finally:
            await page.close()

        return jobs

    @staticmethod
    async def scrape_all_companies(browser) -> List[Dict]:
        """Run all company scrapers in parallel."""
        tasks = [
            CompanyScrapers.scrape_line(browser),
            CompanyScrapers.scrape_rakuten(browser),
            CompanyScrapers.scrape_mercari(browser),
            CompanyScrapers.scrape_sony(browser),
            CompanyScrapers.scrape_bytedance(browser),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs = []
        for result in results:
            if isinstance(result, list):
                all_jobs.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Scraper failed: {result}")

        return all_jobs
