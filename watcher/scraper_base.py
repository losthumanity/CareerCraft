"""
Base Scraper Infrastructure
Provides robust scraping capabilities with retry logic, caching, and validation
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse

import yaml
from bs4 import BeautifulSoup
from playwright.async_api import Page, Browser, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class ScraperCache:
    """Simple file-based cache for scraping results."""

    def __init__(self, cache_dir: str = "../logs/cache", ttl: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key from URL."""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path."""
        return self.cache_dir / f"{key}.json"

    def get(self, url: str) -> Optional[Dict]:
        """Retrieve cached data if valid."""
        key = self._get_cache_key(url)
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if cache is still valid
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time > timedelta(seconds=self.ttl):
                cache_path.unlink()  # Delete expired cache
                return None

            logger.debug(f"Cache hit for {url}")
            return data['content']
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None

    def set(self, url: str, content: Any):
        """Store data in cache."""
        key = self._get_cache_key(url)
        cache_path = self._get_cache_path(key)

        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'content': content
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Cached result for {url}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")

    def clear_expired(self):
        """Clear all expired cache entries."""
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                cached_time = datetime.fromisoformat(data['timestamp'])
                if datetime.now() - cached_time > timedelta(seconds=self.ttl):
                    cache_file.unlink()
                    count += 1
            except Exception:
                pass
        if count:
            logger.info(f"Cleared {count} expired cache entries")


class RetryHandler:
    """Handles retry logic with exponential backoff."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay

    async def execute(self, func, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except PlaywrightTimeout as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.base_delay)

        logger.error(f"All {self.max_retries} attempts failed")
        raise last_exception


class JobValidator:
    """Validates and normalizes job data."""

    @staticmethod
    def validate_job(job: Dict) -> bool:
        """Check if job data is valid."""
        required_fields = ['company', 'title', 'url']

        # Check required fields
        if not all(field in job and job[field] for field in required_fields):
            return False

        # Validate URL
        try:
            result = urlparse(job['url'])
            if not all([result.scheme, result.netloc]):
                return False
        except Exception:
            return False

        # Check title length
        if len(job['title']) < 3 or len(job['title']) > 300:
            return False

        return True

    @staticmethod
    def normalize_job(job: Dict) -> Dict:
        """Normalize job data."""
        # Trim whitespace
        job['title'] = job['title'].strip()
        job['company'] = job['company'].strip()
        job['url'] = job['url'].strip()

        # Add metadata
        job['scraped_at'] = datetime.now().isoformat()

        # Generate unique ID
        job['id'] = hashlib.md5(
            f"{job['company']}|{job['url']}".encode()
        ).hexdigest()

        return job

    @staticmethod
    def deduplicate_jobs(jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on URL."""
        seen = set()
        unique_jobs = []

        for job in jobs:
            if job['url'] not in seen:
                seen.add(job['url'])
                unique_jobs.append(job)

        return unique_jobs


class BaseScraper(ABC):
    """Base class for all company scrapers."""

    def __init__(self, config: Dict):
        self.config = config
        self.global_config = config.get('scraping', {})
        self.cache = ScraperCache(ttl=self.global_config.get('cache_ttl', 3600))
        self.retry_handler = RetryHandler(
            max_retries=self.global_config.get('max_retries', 3),
            base_delay=self.global_config.get('retry_delay', 2)
        )
        self.validator = JobValidator()
        self.rate_limit_delay = self.global_config.get('rate_limit_delay', 1)

    async def navigate_with_retry(self, page: Page, url: str, wait_time: int = 3000):
        """Navigate to URL with retry logic."""
        async def _navigate():
            await page.goto(url, timeout=self.global_config.get('timeout', 30000))
            await page.wait_for_timeout(wait_time)
            return await page.content()

        return await self.retry_handler.execute(_navigate)

    def normalize_url(self, url: str, base_url: str) -> str:
        """Normalize relative URLs to absolute."""
        if not url:
            return ""

        if url.startswith('http'):
            return url

        if url.startswith('//'):
            return f"https:{url}"

        return urljoin(base_url, url)

    def filter_by_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords."""
        if not keywords:
            return True
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

    @abstractmethod
    async def scrape(self, browser: Browser) -> List[Dict]:
        """Scrape jobs from company. Must be implemented by subclass."""
        pass

    async def scrape_with_validation(self, browser: Browser) -> List[Dict]:
        """Scrape with validation and normalization."""
        start_time = time.time()

        try:
            # Add rate limiting
            await asyncio.sleep(self.rate_limit_delay)

            # Scrape jobs
            jobs = await self.scrape(browser)

            # Validate and normalize
            valid_jobs = []
            for job in jobs:
                if self.validator.validate_job(job):
                    normalized_job = self.validator.normalize_job(job)
                    valid_jobs.append(normalized_job)
                else:
                    logger.warning(f"Invalid job data: {job}")

            # Deduplicate
            unique_jobs = self.validator.deduplicate_jobs(valid_jobs)

            elapsed = time.time() - start_time
            logger.info(
                f"{self.company_name}: Found {len(unique_jobs)} valid jobs "
                f"(filtered {len(jobs) - len(unique_jobs)}) in {elapsed:.2f}s"
            )

            return unique_jobs

        except Exception as e:
            logger.error(f"{self.company_name}: Scraping failed - {e}", exc_info=True)
            return []

    @property
    @abstractmethod
    def company_name(self) -> str:
        """Company name for logging."""
        pass


class ScraperMetrics:
    """Track scraping metrics and performance."""

    def __init__(self):
        self.metrics = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'total_jobs_found': 0,
            'companies': {}
        }

    def record_run(self, company: str, success: bool, jobs_count: int):
        """Record a scraping run."""
        self.metrics['total_runs'] += 1

        if success:
            self.metrics['successful_runs'] += 1
            self.metrics['total_jobs_found'] += jobs_count
        else:
            self.metrics['failed_runs'] += 1

        if company not in self.metrics['companies']:
            self.metrics['companies'][company] = {
                'runs': 0,
                'successes': 0,
                'failures': 0,
                'jobs_found': 0
            }

        comp_metrics = self.metrics['companies'][company]
        comp_metrics['runs'] += 1
        if success:
            comp_metrics['successes'] += 1
            comp_metrics['jobs_found'] += jobs_count
        else:
            comp_metrics['failures'] += 1

    def get_summary(self) -> Dict:
        """Get metrics summary."""
        return {
            **self.metrics,
            'success_rate': (
                self.metrics['successful_runs'] / self.metrics['total_runs']
                if self.metrics['total_runs'] > 0 else 0
            )
        }

    def save(self, filepath: str):
        """Save metrics to file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.get_summary(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
