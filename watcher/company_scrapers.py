"""
Company-Specific Job Scrapers
Each company has unique job board structure - need custom scraping logic

Enhanced with:
- Retry logic with exponential backoff
- Caching to reduce redundant requests
- Data validation and normalization
- Deduplication
- Metrics tracking
- Better error handling
"""

import asyncio
import yaml
from pathlib import Path
from playwright.async_api import Browser
from bs4 import BeautifulSoup
from typing import List, Dict
import logging

from scraper_base import BaseScraper, ScraperMetrics

logger = logging.getLogger(__name__)


def load_config():
    """Load scraper configuration."""
    config_path = Path(__file__).parent / "scraper_config.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


class LINEScraper(BaseScraper):
    """LINE Corporation job scraper - LY Corp new grad engineering page."""

    @property
    def company_name(self) -> str:
        return "LY Corporation (LINE)"

    async def scrape(self, browser: Browser) -> List[Dict]:
        """Scrape LINE job listings."""
        jobs = []
        url = self.config['companies']['line']['urls'][0]
        page = await browser.new_page()

        try:
            cached_jobs = self.cache.get(url)
            if cached_jobs:
                return cached_jobs

            await self.navigate_with_retry(page, url, wait_time=3000)

            # Look for course/position entries on the recruitment page
            job_cards = await page.locator(".course-item, .position-item, section h3, .recruit-course").all()

            for card in job_cards:
                text = await card.inner_text()
                link_element = card.locator("a")

                if await link_element.count() > 0:
                    href = await link_element.first.get_attribute("href")
                    full_url = self.normalize_url(href, url)

                    # Skip navigation links
                    skip_terms = ['ABOUT', 'FAQ', 'LOGIN', 'ENTRY']
                    if any(term in text.upper() for term in skip_terms):
                        continue

                    clean_title = text.split('\n')[0].strip()

                    if len(clean_title) > 5:
                        jobs.append({
                            'company': self.company_name,
                            'title': clean_title,
                            'url': full_url,
                            'text': text
                        })

            self.cache.set(url, jobs)
        except Exception as e:
            logger.error(f"{self.company_name}: Scraping error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class RakutenScraper(BaseScraper):
    """
    Rakuten New Grad Scraper - Section-Based.
    The page lists all job positions in div containers with job descriptions inline.
    We extract each job div that contains Software Engineer positions.
    """

    @property
    def company_name(self) -> str:
        return "Rakuten Group"

    async def scrape(self, browser: Browser) -> List[Dict]:
        jobs = []
        url = "https://corp.rakuten.co.jp/careers/graduates/recruit_engineer/"
        page = await browser.new_page()

        try:
            cached_jobs = self.cache.get(url)
            if cached_jobs:
                logger.info(f"{self.company_name}: Returning {len(cached_jobs)} cached jobs")
                return cached_jobs

            logger.info(f"{self.company_name}: Loading single-page job board...")
            await self.navigate_with_retry(page, url, wait_time=3000)

            # Strategy: Find job divs that contain detailed position info
            # Based on analysis: divs with class containing 'job' contain position details
            job_containers = await page.locator('div[class*="job"]').all()

            logger.info(f"  Found {len(job_containers)} potential job containers")

            seen_titles = set()  # Deduplicate by title

            for container in job_containers:
                try:
                    container_text = await container.inner_text()

                    # Must contain "職種" (job type) or "Software Engineer"
                    if '職種' not in container_text and 'Software Engineer' not in container_text:
                        continue

                    # Must be substantial (more than 100 chars)
                    if len(container_text) < 100:
                        continue

                    # Extract company/division name if present
                    # Look for patterns like "Commerce & Marketing Company", "Rakuten Payment, Inc."
                    title_parts = []
                    lines = container_text.split('\n')

                    for line in lines[:10]:  # Check first 10 lines
                        line = line.strip()
                        if 'Company' in line or 'Inc.' in line or 'Division' in line:
                            title_parts.append(line)
                        elif line == 'Software Engineer':
                            title_parts.append(line)
                            break

                    if not title_parts:
                        # Fallback: use first substantial line
                        title_parts = [l for l in lines if l.strip() and len(l.strip()) > 10][:1]

                    if not title_parts:
                        continue

                    title = ' - '.join(title_parts[:2])  # Max 2 parts

                    # Deduplicate by title
                    if title in seen_titles:
                        continue
                    seen_titles.add(title)

                    # Look for entry link in this container
                    entry_link = container.locator('a[href*="entry"], a:has-text("エントリー")').first
                    if await entry_link.count() > 0:
                        entry_url = await entry_link.get_attribute('href')
                        entry_url = self.normalize_url(entry_url, url)
                    else:
                        entry_url = url

                    # Extract relevant description (first 500 chars)
                    description = container_text[:500].replace('\n', ' ').strip()

                    jobs.append({
                        'company': self.company_name,
                        'title': title[:100],  # Limit title length
                        'url': entry_url,
                        'text': description
                    })

                    logger.info(f"  Found position: {title[:60]}...")

                except Exception as e:
                    logger.debug(f"Error processing job container: {e}")
                    continue

            # Fallback: If no job containers found, add general entry
            if not jobs:
                logger.warning(f"{self.company_name}: No job containers found, adding general entry.")
                jobs.append({
                    'company': self.company_name,
                    'title': "Rakuten Engineering New Grad (All Positions)",
                    'url': url,
                    'text': "Open recruitment for Software Engineer positions across all companies and divisions. Visit page for specific position details and requirements."
                })

            self.cache.set(url, jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class GreenhouseScraper(BaseScraper):
    """Generic Scraper for companies using Greenhouse (Mercari, Woven)."""

    def __init__(self, config, company_key):
        super().__init__(config)
        self.company_key = company_key

    @property
    def company_name(self) -> str:
        return self.config['companies'][self.company_key]['name']

    async def scrape(self, browser: Browser) -> List[Dict]:
        jobs = []
        url = self.config['companies'][self.company_key]['urls'][0]
        page = await browser.new_page()

        try:
            cached_jobs = self.cache.get(url)
            if cached_jobs:
                return cached_jobs

            await self.navigate_with_retry(page, url, wait_time=3000)

            # Greenhouse standard structure: div.opening represents a job row
            openings = await page.locator("div.opening").all()

            for opening in openings:
                title_elem = opening.locator("a")
                location_elem = opening.locator("span.location")

                if await title_elem.count() > 0:
                    title = await title_elem.inner_text()
                    href = await title_elem.get_attribute("href")
                    location = await location_elem.inner_text() if await location_elem.count() > 0 else ""

                    # Filter for Engineering/New Grad keywords
                    target_keywords = ['Engineer', 'Developer', 'New Grad', '2026', 'Intern']
                    if not any(k.lower() in title.lower() for k in target_keywords):
                        continue

                    jobs.append({
                        'company': self.company_name,
                        'title': title,
                        'url': self.normalize_url(href, url),
                        'location': location,
                        'text': f"{title} - {location}"
                    })

            self.cache.set(url, jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class SonyWorkdayScraper(BaseScraper):
    """Sony Scraper - Direct Workday ATS feed (real-time, no marketing fluff)."""

    @property
    def company_name(self) -> str:
        return "Sony Group"

    async def scrape(self, browser: Browser) -> List[Dict]:
        jobs = []
        url = self.config['companies']['sony']['urls'][0]  # Direct ATS: sonyglobal.wd1.myworkdayjobs.com
        page = await browser.new_page()

        try:
            cached_jobs = self.cache.get(url)
            if cached_jobs:
                return cached_jobs

            await self.navigate_with_retry(page, url, wait_time=5000)

            # Workday uses AJAX - wait for job list to load
            # Multiple selector strategies for Workday's dynamic structure
            try:
                await page.wait_for_selector('li[class*="css-"], ul[role="list"] li, a[data-automation-id="jobTitle"]', timeout=15000)
            except:
                logger.warning(f"{self.company_name}: Workday ATS list did not load.")

            # Workday lists jobs in <li> elements with dynamic CSS classes
            job_items = await page.locator('li[class*="css-"]').all()

            for item in job_items:
                # Workday job title is typically in <a> with data-automation-id="jobTitle"
                title_el = item.locator('a[data-automation-id="jobTitle"], h3 a, a[class*="jobTitle"]')

                if await title_el.count() > 0:
                    title = await title_el.first.inner_text()
                    href = await title_el.first.get_attribute("href")

                    if title and href:
                        # Get additional metadata (location, job ID) if available
                        metadata = await item.inner_text()

                        jobs.append({
                            'company': self.company_name,
                            'title': title.strip(),
                            'url': self.normalize_url(href, url),
                            'text': metadata[:300]  # Keep snippet for semantic matching
                        })

            self.cache.set(url, jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class ByteDanceScraper(BaseScraper):
    """ByteDance Scraper - hits the Search Portal directly."""

    @property
    def company_name(self) -> str:
        return "ByteDance (TikTok)"

    async def scrape(self, browser: Browser) -> List[Dict]:
        jobs = []
        url = self.config['companies']['bytedance']['urls'][0]
        page = await browser.new_page()

        try:
            cached_jobs = self.cache.get(url)
            if cached_jobs:
                return cached_jobs

            # Wait for the JS job cards to load (they are dynamic)
            await self.navigate_with_retry(page, url, wait_time=5000)
            try:
                await page.wait_for_selector('a[class*="jobTitle"]', timeout=10000)
            except:
                logger.warning(f"{self.company_name}: No job cards loaded (or timeout).")

            # Extract job cards
            cards = await page.locator('div[class*="jobCard"]').all()

            if not cards:
                logger.warning(f"{self.company_name}: No job cards found on page.")
                self.cache.set(url, [])
                return jobs

            for card in cards:
                title_el = card.locator('a[class*="jobTitle"]')

                if await title_el.count() > 0:
                    title = await title_el.inner_text()
                    href = await title_el.get_attribute("href")

                    # Filter for Engineering/Research
                    if 'Engineer' not in title and 'Research' not in title:
                        continue

                    jobs.append({
                        'company': self.company_name,
                        'title': title,
                        'url': href,  # Usually absolute
                        'text': await card.inner_text()
                    })

            self.cache.set(url, jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class ToshibaScraper(BaseScraper):
    """Toshiba scraper - Targets HRMOS jobs page directly."""

    @property
    def company_name(self) -> str:
        return "Toshiba"

    async def scrape(self, browser: Browser) -> List[Dict]:
        """Scrape Toshiba job listings directly from HRMOS jobs page."""
        jobs = []
        # Go directly to the jobs listing page
        url = "https://hrmos.co/pages/toshiba/jobs"
        page = await browser.new_page()

        try:
            cached_jobs = self.cache.get(url)
            if cached_jobs:
                return cached_jobs

            # Navigate to HRMOS jobs listing
            await self.navigate_with_retry(page, url, wait_time=5000)

            # Wait for job listings to load (any link with /jobs/ in URL)
            try:
                await page.wait_for_selector('a[href*="/jobs/"]', timeout=10000)
            except:
                logger.warning(f"{self.company_name}: HRMOS job listings did not load.")

            # Extract job links - HRMOS uses simple anchor tags
            job_links = await page.locator('a[href*="/jobs/"][href*="toshiba"]').all()

            for job_link in job_links:
                try:
                    # Get job text and URL
                    text = await job_link.inner_text()
                    href = await job_link.get_attribute('href')

                    if not href or not text or len(text) < 20:
                        continue

                    # Skip the search button and company link
                    if '件の検索結果' in text or 'www.global.toshiba' in href:
                        continue

                    # Extract title (first line of text, usually the position name)
                    title = text.split('\n')[0].strip()
                    if len(title) < 10:
                        title = text[:80].strip()

                    job_url = self.normalize_url(href, url)

                    jobs.append({
                        'company': self.company_name,
                        'title': title,
                        'url': job_url,
                        'text': text[:300]  # Keep snippet of full text
                    })

                except Exception as e:
                    logger.debug(f"Error parsing job item: {e}")
                    continue

            self.cache.set(url, jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class PreferredNetworksScraper(BaseScraper):
    """Preferred Networks scraper - Simplified for their careers page."""

    @property
    def company_name(self) -> str:
        return "Preferred Networks"

    async def scrape(self, browser: Browser) -> List[Dict]:
        """Scrape Preferred Networks job listings from careers page."""
        jobs = []
        url = self.config['companies']['preferred']['urls'][0]
        page = await browser.new_page()

        try:
            cached_jobs = self.cache.get(url)
            if cached_jobs:
                return cached_jobs

            await self.navigate_with_retry(page, url, wait_time=5000)

            # Look for any links related to recruitment/careers
            job_links = await page.locator('a[href*="recruit"], a[href*="career"], a[href*="job"]').all()

            if not job_links:
                logger.warning(f"{self.company_name}: No recruitment links found.")
                self.cache.set(url, [])
                return jobs

            for link in job_links:
                try:
                    title = await link.inner_text()
                    href = await link.get_attribute('href')

                    if title and href and len(title) > 10:
                        # Skip navigation/footer links
                        if any(skip in title.lower() for skip in ['about', 'contact', 'privacy', 'top page']):
                            continue

                        jobs.append({
                            'company': self.company_name,
                            'title': title.strip(),
                            'url': self.normalize_url(href, url),
                            'text': title
                        })
                except Exception as e:
                    logger.debug(f"Error parsing link: {e}")
                    continue

            self.cache.set(url, jobs)

            self.cache.set(url, jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class CompanyScrapers:
    """Orchestrates all company scrapers with robust error handling."""

    def __init__(self):
        self.config = load_config()
        self.metrics = ScraperMetrics()
        self.scrapers = self._initialize_scrapers()

    def _initialize_scrapers(self) -> List[BaseScraper]:
        """Initialize all scraper instances."""
        return [
            LINEScraper(self.config),
            RakutenScraper(self.config),
            ByteDanceScraper(self.config),
            SonyWorkdayScraper(self.config),
            # Reusing the Greenhouse Logic for efficiency
            GreenhouseScraper(self.config, 'mercari'),
            GreenhouseScraper(self.config, 'woven'),
            PreferredNetworksScraper(self.config),
            ToshibaScraper(self.config),
        ]

    async def scrape_all_companies(self, browser: Browser) -> List[Dict]:
        """Run all company scrapers with metrics tracking."""
        logger.info(f"Starting scrape of {len(self.scrapers)} companies...")

        # Run scrapers in parallel
        tasks = [
            scraper.scrape_with_validation(browser)
            for scraper in self.scrapers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs = []
        for scraper, result in zip(self.scrapers, results):
            if isinstance(result, list):
                all_jobs.extend(result)
                self.metrics.record_run(scraper.company_name, True, len(result))
            elif isinstance(result, Exception):
                logger.error(f"{scraper.company_name}: Failed - {result}")
                self.metrics.record_run(scraper.company_name, False, 0)

        # Save metrics
        self.metrics.save('../logs/scraper_metrics.json')

        # Log summary
        summary = self.metrics.get_summary()
        logger.info(
            f"Scraping complete: {summary['total_jobs_found']} jobs found, "
            f"Success rate: {summary['success_rate']:.1%}"
        )

        return all_jobs

    def clear_cache(self):
        """Clear expired cache entries for all scrapers."""
        for scraper in self.scrapers:
            scraper.cache.clear_expired()


# Backwards compatibility
async def scrape_all_companies(browser: Browser) -> List[Dict]:
    """Legacy function for compatibility."""
    scrapers = CompanyScrapers()
    return await scrapers.scrape_all_companies(browser)
