"""
Smart Job Watcher v2 - Semantic Matching Edition
Target: 2026 AI/ML Graduate roles in Japan

Why this beats crawl4ai:
- Simpler, faster, free
- Better suited for structured job boards
- Semantic matching without RAG complexity
- Easy to maintain and debug
"""

import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import numpy as np
import sqlite3
from datetime import datetime
import logging
from typing import List, Dict
import hashlib

# Initialize semantic model (runs locally, no API costs)
model = SentenceTransformer('all-MiniLM-L6-v2')  # 80MB, fast

# Your profile embedding (compute once)
YOUR_PROFILE = """
2026 Graduate seeking AI Engineer / ML Engineer position in Japan.
Experience: 6-month AI internship at Johnson Controls (Fortune 500).
Skills: Python, PyTorch, TensorFlow, FastAPI, Computer Vision, Industrial AI.
Looking for: New graduate program, English-speaking role, visa sponsorship.
"""
profile_embedding = model.encode(YOUR_PROFILE)

logger = logging.getLogger(__name__)


class SmartJobScraper:
    """Semantic job matcher with targeted scraping."""

    PRIORITY_COMPANIES = {
        'Sony': 'https://www.sony.com/en/SonyInfo/CorporateInfo/Careers/',
        'Woven by Toyota': 'https://woven-by-toyota.com/en/careers',
        'Rakuten': 'https://global.rakuten.com/corp/careers/',
        'Mercari': 'https://careers.mercari.com/',
        'Preferred Networks': 'https://www.preferred.jp/en/news/',
    }

    TECH_JOB_BOARDS = {
        'Japan Dev': 'https://japan-dev.com/',
        'LinkedIn': 'https://www.linkedin.com/jobs/search/?keywords=AI%20Engineer%20Japan%202026',
    }

    # Keywords that MUST appear (hard filter)
    MUST_HAVE = ['2026', 'graduate', 'new grad', 'fresh graduate', 'class of 2026']

    # Positive signals for semantic matching
    GOOD_SIGNALS = ['AI', 'machine learning', 'ML engineer', 'python', 'computer vision', 'backend']

    # Deal breakers
    BAD_SIGNALS = ['PhD required', '5+ years', 'senior', 'lead', 'manager', 'Japanese fluency required']

    def __init__(self, db_path='../shared/jobs.db'):
        self.db_path = db_path
        self.seen_hashes = self._load_seen_hashes()

    def _load_seen_hashes(self) -> set:
        """Load previously seen job hashes to avoid duplicates."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT url FROM jobs')
            urls = [row[0] for row in cursor.fetchall()]
            conn.close()
            return {hashlib.sha256(url.encode()).hexdigest() for url in urls}
        except:
            return set()

    def semantic_match_score(self, job_text: str) -> float:
        """
        Calculate semantic similarity between job and your profile.
        Returns: 0.0 to 1.0 (higher = better match)
        """
        # Quick keyword filter first (saves compute)
        job_lower = job_text.lower()

        # Must have at least one "2026/graduate" keyword
        if not any(keyword in job_lower for keyword in self.MUST_HAVE):
            return 0.0

        # Deal breakers
        if any(bad in job_lower for bad in self.BAD_SIGNALS):
            return 0.0

        # Compute semantic similarity
        job_embedding = model.encode(job_text)
        similarity = np.dot(job_embedding, profile_embedding) / (
            np.linalg.norm(job_embedding) * np.linalg.norm(profile_embedding)
        )

        # Boost score if contains good signals
        boost = sum(0.05 for signal in self.GOOD_SIGNALS if signal.lower() in job_lower)

        return min(1.0, similarity + boost)

    async def scrape_company_page(self, company: str, url: str) -> List[Dict]:
        """
        Scrape a company career page using Playwright (handles dynamic content).
        Returns list of matched jobs.
        """
        matches = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until='networkidle', timeout=30000)

                # Wait for content to load (adjust selector per site)
                await page.wait_for_timeout(2000)

                # Get page HTML
                html = await page.content()
                soup = BeautifulSoup(html, 'html.parser')

                # Find all links
                for link in soup.find_all('a', href=True):
                    link_text = link.get_text(strip=True)
                    link_url = link['href']

                    # Make absolute URL
                    if not link_url.startswith('http'):
                        from urllib.parse import urljoin
                        link_url = urljoin(url, link_url)

                    # Get surrounding context (parent element text)
                    context = link.parent.get_text(strip=True) if link.parent else ''
                    full_text = f"{link_text} {context}"

                    # Semantic matching
                    score = self.semantic_match_score(full_text)

                    if score >= 0.7:  # Threshold: 70%+ match
                        # Check if already seen
                        url_hash = hashlib.sha256(link_url.encode()).hexdigest()
                        if url_hash not in self.seen_hashes:
                            matches.append({
                                'company': company,
                                'title': link_text,
                                'url': link_url,
                                'match_score': score,
                                'snippet': full_text[:200]
                            })
                            self.seen_hashes.add(url_hash)
                            logger.info(f"✅ Found match: {link_text} (score: {score:.2f})")

            except Exception as e:
                logger.error(f"Error scraping {company}: {e}")
            finally:
                await browser.close()

        return matches

    def save_to_db(self, job: Dict):
        """Save matched job to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO jobs
                (company, title, url, keywords_matched, applied_status, notes)
                VALUES (?, ?, ?, ?, 'Pending', ?)
            ''', (
                job['company'],
                job['title'],
                job['url'],
                f"Semantic Match: {job['match_score']:.2f}",
                f"AI-matched. Score: {job['match_score']:.2f}\n{job['snippet']}"
            ))
            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"DB error: {e}")
            return False

    async def run_smart_scan(self):
        """Run smart scan on all priority sites."""
        logger.info("🎯 Starting Smart Job Scan (Semantic Matching)")

        all_matches = []

        # Scan priority companies
        for company, url in self.PRIORITY_COMPANIES.items():
            logger.info(f"Scanning {company}...")
            matches = await self.scrape_company_page(company, url)
            all_matches.extend(matches)
            await asyncio.sleep(3)  # Be polite

        # Save to database
        new_jobs = 0
        for job in all_matches:
            if self.save_to_db(job):
                new_jobs += 1

        logger.info(f"✅ Scan complete. Found {new_jobs} new matches.")
        return new_jobs


async def main():
    scraper = SmartJobScraper()
    await scraper.run_smart_scan()


if __name__ == "__main__":
    asyncio.run(main())
