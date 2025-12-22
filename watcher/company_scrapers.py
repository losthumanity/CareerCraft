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
    """LINE Corporation job scraper."""
    
    @property
    def company_name(self) -> str:
        return "LY Corporation (LINE)"
    
    async def scrape(self, browser: Browser) -> List[Dict]:
        """Scrape LINE job listings."""
        jobs = []
        company_config = self.config['companies']['line']
        page = await browser.new_page()

        try:
            for url in company_config['urls']:
                # Check cache first
                cached_jobs = self.cache.get(url)
                if cached_jobs:
                    jobs.extend(cached_jobs)
                    continue
                
                # Navigate with retry
                html = await self.navigate_with_retry(
                    page, url, company_config.get('wait_time', 3000)
                )
                soup = BeautifulSoup(html, 'html.parser')

                # Try multiple selector strategies
                job_cards = []
                for selector in company_config['selectors']['job_cards']:
                    if '[' in selector:  # CSS selector
                        job_cards = soup.select(selector)
                    else:  # Tag with class filter
                        job_cards = soup.find_all(
                            selector.split('[')[0],
                            class_=lambda x: x and 'job' in str(x).lower()
                        )
                    if job_cards:
                        break

                url_jobs = []
                for card in job_cards:
                    # Find title using multiple strategies
                    title_elem = None
                    for title_selector in company_config['selectors']['title']:
                        title_elem = card.find(title_selector)
                        if title_elem:
                            break
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    
                    # Find link
                    link_elem = card.find('a', href=True) or title_elem
                    if not link_elem or not link_elem.get('href'):
                        continue
                    
                    job_url = self.normalize_url(link_elem['href'], url)
                    card_text = card.get_text(strip=True)
                    
                    # Filter by keywords
                    if not self.filter_by_keywords(card_text, company_config.get('keywords', [])):
                        continue

                    url_jobs.append({
                        'company': self.company_name,
                        'title': title,
                        'url': job_url,
                        'text': card_text
                    })
                
                # Cache results
                self.cache.set(url, url_jobs)
                jobs.extend(url_jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Scraping error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class RakutenScraper(BaseScraper):
    """Rakuten Group job scraper."""
    
    @property
    def company_name(self) -> str:
        return "Rakuten Group"
    
    async def scrape(self, browser: Browser) -> List[Dict]:
        """Scrape Rakuten job listings."""
        jobs = []
        company_config = self.config['companies']['rakuten']
        page = await browser.new_page()

        try:
            for url in company_config['urls']:
                cached_jobs = self.cache.get(url)
                if cached_jobs:
                    jobs.extend(cached_jobs)
                    continue
                
                html = await self.navigate_with_retry(
                    page, url, company_config.get('wait_time', 3000)
                )
                soup = BeautifulSoup(html, 'html.parser')
                job_links = soup.find_all('a', href=True)

                url_jobs = []
                for link in job_links:
                    text = link.get_text(strip=True)
                    
                    if not text or len(text) < 10:
                        continue
                    
                    # Skip navigation/category links
                    href = link.get('href', '')
                    if any(skip in href.lower() for skip in ['#', 'javascript:', 'mailto:']):
                        continue
                    
                    # Only get links that look like actual job postings
                    # Skip broad category links like "NEW GRADUATE RECRUITING"
                    if any(skip in text.upper() for skip in ['RECRUITING', 'POSITIONS', 'CAREERS', 'OPPORTUNITIES', 'ENGINEER POSITIONS']):
                        continue
                    
                    # Filter by keywords - must have specific job indicators
                    if not self.filter_by_keywords(text, company_config.get('keywords', [])):
                        continue
                    
                    job_url = self.normalize_url(href, url)

                    url_jobs.append({
                        'company': self.company_name,
                        'title': text,
                        'url': job_url,
                        'text': text
                    })
                
                self.cache.set(url, url_jobs)
                jobs.extend(url_jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Scraping error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class MercariScraper(BaseScraper):
    """Mercari job scraper - Updated for new careers site."""
    
    @property
    def company_name(self) -> str:
        return "Mercari"
    
    async def scrape(self, browser: Browser) -> List[Dict]:
        """Scrape Mercari job listings from careers page."""
        jobs = []
        company_config = self.config['companies']['mercari']
        page = await browser.new_page()

        try:
            for url in company_config['urls']:
                cached_jobs = self.cache.get(url)
                if cached_jobs:
                    jobs.extend(cached_jobs)
                    continue
                
                html = await self.navigate_with_retry(
                    page, url, company_config.get('wait_time', 5000)
                )
                soup = BeautifulSoup(html, 'html.parser')

                # Try multiple selector strategies for job cards
                job_cards = []
                for selector in company_config['selectors']['job_cards'].split(', '):
                    job_cards = soup.select(selector.strip())
                    if job_cards:
                        break

                url_jobs = []
                for card in job_cards:
                    # Find title
                    title_elem = None
                    for title_selector in company_config['selectors']['title'].split(', '):
                        title_elem = card.find(title_selector.strip())
                        if title_elem:
                            break
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = card.find('a', href=True)
                    
                    if not link:
                        link = title_elem if title_elem.name == 'a' else None
                    
                    if not link:
                        continue
                    
                    job_url = self.normalize_url(link['href'], url)
                    
                    # Filter by keywords
                    card_text = card.get_text(strip=True)
                    if not self.filter_by_keywords(card_text, company_config.get('keywords', [])):
                        continue

                    url_jobs.append({
                        'company': self.company_name,
                        'title': title,
                        'url': job_url,
                        'text': card_text
                    })
                
                self.cache.set(url, url_jobs)
                jobs.extend(url_jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Scraping error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class SonyScraper(BaseScraper):
    """Sony job scraper."""
    
    @property
    def company_name(self) -> str:
        return "Sony"
    
    async def scrape(self, browser: Browser) -> List[Dict]:
        """Scrape Sony job listings."""
        jobs = []
        company_config = self.config['companies']['sony']
        page = await browser.new_page()

        try:
            for url in company_config['urls']:
                cached_jobs = self.cache.get(url)
                if cached_jobs:
                    jobs.extend(cached_jobs)
                    continue
                
                html = await self.navigate_with_retry(
                    page, url, company_config.get('wait_time', 3000)
                )
                soup = BeautifulSoup(html, 'html.parser')
                job_links = soup.find_all('a', href=True)

                url_jobs = []
                for link in job_links:
                    text = link.get_text(strip=True)
                    
                    if not text or len(text) < 5:
                        continue
                    
                    # Filter by keywords
                    if not self.filter_by_keywords(text, company_config.get('keywords', [])):
                        continue
                    
                    job_url = self.normalize_url(link['href'], url)

                    url_jobs.append({
                        'company': self.company_name,
                        'title': text,
                        'url': job_url,
                        'text': text
                    })
                
                self.cache.set(url, url_jobs)
                jobs.extend(url_jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Scraping error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class ByteDanceScraper(BaseScraper):
    """ByteDance (TikTok) job scraper."""
    
    @property
    def company_name(self) -> str:
        return "ByteDance (TikTok)"
    
    async def scrape(self, browser: Browser) -> List[Dict]:
        """Scrape ByteDance job listings."""
        jobs = []
        company_config = self.config['companies']['bytedance']
        page = await browser.new_page()

        try:
            for url in company_config['urls']:
                cached_jobs = self.cache.get(url)
                if cached_jobs:
                    jobs.extend(cached_jobs)
                    continue
                
                html = await self.navigate_with_retry(
                    page, url, company_config.get('wait_time', 5000)
                )
                soup = BeautifulSoup(html, 'html.parser')

                # Find job cards
                job_cards = soup.select(company_config['selectors']['job_cards'])

                url_jobs = []
                for card in job_cards:
                    # Find title
                    title_elem = None
                    for title_selector in company_config['selectors']['title']:
                        title_elem = card.find(title_selector)
                        if title_elem:
                            break
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = card.find('a', href=True)

                    if not link:
                        continue
                    
                    job_url = self.normalize_url(
                        link['href'],
                        'https://jobs.bytedance.com'
                    )

                    url_jobs.append({
                        'company': self.company_name,
                        'title': title,
                        'url': job_url,
                        'text': card.get_text(strip=True)
                    })
                
                self.cache.set(url, url_jobs)
                jobs.extend(url_jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Scraping error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class ToshibaScraper(BaseScraper):
    """Toshiba job scraper - Handles HRMOS redirect."""
    
    @property
    def company_name(self) -> str:
        return "Toshiba"
    
    async def scrape(self, browser: Browser) -> List[Dict]:
        """Scrape Toshiba job listings (follows HRMOS redirect)."""
        jobs = []
        company_config = self.config['companies']['toshiba']
        page = await browser.new_page()

        try:
            for url in company_config['urls']:
                cached_jobs = self.cache.get(url)
                if cached_jobs:
                    jobs.extend(cached_jobs)
                    continue
                
                html = await self.navigate_with_retry(
                    page, url, company_config.get('wait_time', 3000)
                )
                soup = BeautifulSoup(html, 'html.parser')

                # Find HRMOS/BizReach redirect link
                hrmos_link = soup.select_one(company_config['selectors']['hrmos_link'])
                
                url_jobs = []
                if hrmos_link and hrmos_link.get('href'):
                    hrmos_url = self.normalize_url(hrmos_link['href'], url)
                    
                    # Navigate to HRMOS page
                    html2 = await self.navigate_with_retry(page, hrmos_url, 5000)
                    soup2 = BeautifulSoup(html2, 'html.parser')
                    
                    # HRMOS job listings
                    job_items = soup2.select('div.job-list-item, div[class*="job"], article')
                    
                    for job in job_items:
                        title_elem = job.find(['h2', 'h3', 'a'])
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        link = job.find('a', href=True)
                        
                        if not link:
                            continue
                        
                        job_url = self.normalize_url(link['href'], hrmos_url)
                        
                        url_jobs.append({
                            'company': self.company_name,
                            'title': title,
                            'url': job_url,
                            'text': job.get_text(strip=True)
                        })
                
                self.cache.set(url, url_jobs)
                jobs.extend(url_jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Scraping error - {e}", exc_info=True)
        finally:
            await page.close()

        return jobs


class PreferredNetworksScraper(BaseScraper):
    """Preferred Networks job scraper - Talentio platform."""
    
    @property
    def company_name(self) -> str:
        return "Preferred Networks"
    
    async def scrape(self, browser: Browser) -> List[Dict]:
        """Scrape Preferred Networks job listings from Talentio."""
        jobs = []
        company_config = self.config['companies']['preferred']
        page = await browser.new_page()

        try:
            for url in company_config['urls']:
                cached_jobs = self.cache.get(url)
                if cached_jobs:
                    jobs.extend(cached_jobs)
                    continue
                
                html = await self.navigate_with_retry(
                    page, url, company_config.get('wait_time', 5000)
                )
                soup = BeautifulSoup(html, 'html.parser')

                # Try multiple selector strategies
                job_cards = []
                for selector in company_config['selectors']['job_cards'].split(', '):
                    job_cards = soup.select(selector.strip())
                    if job_cards:
                        break

                url_jobs = []
                for card in job_cards:
                    # Find title
                    title_elem = None
                    for title_selector in company_config['selectors']['title'].split(', '):
                        title_elem = card.find(title_selector.strip())
                        if title_elem:
                            break
                    
                    if not title_elem:
                        continue
                    
                    title = title_elem.get_text(strip=True)
                    link = card.find('a', href=True)
                    
                    if not link:
                        link = title_elem if title_elem.name == 'a' else None
                    
                    if not link:
                        continue
                    
                    job_url = self.normalize_url(link['href'], url)
                    
                    # Filter by keywords
                    card_text = card.get_text(strip=True)
                    if not self.filter_by_keywords(card_text, company_config.get('keywords', [])):
                        continue

                    url_jobs.append({
                        'company': self.company_name,
                        'title': title,
                        'url': job_url,
                        'text': card_text
                    })
                
                self.cache.set(url, url_jobs)
                jobs.extend(url_jobs)

        except Exception as e:
            logger.error(f"{self.company_name}: Scraping error - {e}", exc_info=True)
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
            MercariScraper(self.config),
            SonyScraper(self.config),
            ByteDanceScraper(self.config),
            ToshibaScraper(self.config),
            PreferredNetworksScraper(self.config),
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
