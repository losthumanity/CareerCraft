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
from company_scrapers import CompanyScrapers

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
        # Tier 1: Confirmed 2026 New Grad Programs
        'LY Corporation (LINE)': 'https://careers.linecorp.com/jobs/',
        'Rakuten Group': 'https://global.rakuten.com/corp/careers/graduates',
        'ByteDance (TikTok)': 'https://jobs.bytedance.com/en/position?keywords=graduate&category=&location=CT_222&project=7316601319918881054&type=3&job_hot_flag=&current=1&limit=10',
        'Sony': 'https://www.sony.com/en/SonyInfo/CorporateInfo/Careers/newgrads/',
        'Woven by Toyota': 'https://woven-by-toyota.com/en/careers',

        # Tier 2: Early Career AI Roles (0-2 years)
        'Rakuten International': 'https://rakuten.careers/',
        'Mercari': 'https://careers.mercari.com/',
        'Preferred Networks': 'https://www.preferred.jp/en/news/',
        'Toshiba Quantum': 'https://www.global.toshiba/ww/technology/corporate/rdc.html',
    }

    TECH_JOB_BOARDS = {
        # Curated for international tech professionals
        'Japan Dev': 'https://japan-dev.com/jobs/machine-learning',
        'TokyoDev': 'https://tokyodev.com/jobs/machine-learning',
        'Daijob': 'https://daijob.com/en/jobs/search_result?job_types[]=614',  # ML/AI category
        'LinkedIn': 'https://www.linkedin.com/jobs/search/?keywords=AI%20Engineer%20Japan%202026&location=Japan',
        'Jobs in Japan': 'https://jobsinjapan.com/jobs/search?q=AI+Engineer&category=it',
    }

    # Keywords that MUST appear (hard filter) - at least ONE must match
    MUST_HAVE = [
        '2026', 'graduate', 'new grad', 'fresh graduate', 'class of 2026',
        'entry level', 'early career', '0-2 years', 'recent graduate',
        'new graduate', 'junior', '卒業' # Japanese for graduate (some bilingual pages)
    ]

    # Positive signals for semantic matching (each adds +5% to score)
    GOOD_SIGNALS = [
        'AI', 'machine learning', 'ML engineer', 'artificial intelligence',
        'python', 'pytorch', 'tensorflow', 'computer vision', 'CV',
        'backend', 'fastapi', 'deep learning', 'neural network',
        'LLM', 'generative AI', 'data science', 'MLOps',
        'visa sponsorship', 'english', 'no japanese required'
    ]

    # Deal breakers (auto-reject if found)
    BAD_SIGNALS = [
        'PhD required', 'doctorate required',
        '5+ years', '3+ years experience', 'minimum 3 years',
        'senior', 'lead', 'principal', 'staff engineer',
        'manager', 'director', 'VP', 'head of',
        'N1 required', 'N2 required', 'Japanese fluency required',
        'business level japanese', 'native japanese'
    ]

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

    def semantic_match_score(self, job_text: str, check_must_have: bool = True) -> float:
        """
        Calculate semantic similarity between job and your profile.
        Returns: 0.0 to 1.0 (higher = better match)

        Args:
            job_text: The job description or link text
            check_must_have: If False, skips the MUST_HAVE keyword check (useful for career pages)
        """
        # Quick keyword filter first (saves compute)
        job_lower = job_text.lower()

        # Check for MUST_HAVE keywords (can be disabled for career page scanning)
        if check_must_have:
            if not any(keyword in job_lower for keyword in self.MUST_HAVE):
                return 0.0

        # Deal breakers (always check)
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

                    # Two-stage matching:
                    # Stage 1: Relaxed check for career/job pages (no MUST_HAVE required)
                    # Stage 2: Strict check if we find promising content

                    # First try strict matching (with MUST_HAVE keywords)
                    score = self.semantic_match_score(full_text, check_must_have=True)

                    # If no strict match, try relaxed (for career pages that link to grad programs)
                    if score == 0.0:
                        # Only check if it looks like a job/career link
                        if any(word in full_text.lower() for word in ['career', 'job', 'recruit', 'hiring', 'graduate', 'internship']):
                            score = self.semantic_match_score(full_text, check_must_have=False)

                    if score >= 0.5:  # Threshold: 50%+ match (lowered for discovery)
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
                            logger.info(f"[MATCH] Found: {link_text} (score: {score:.2f})")

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

    async def run_smart_scan(self, scan_job_boards: bool = False, use_company_scrapers: bool = True):
        """
        Run smart scan on all priority sites.

        Args:
            scan_job_boards: If True, also scan tech job board aggregators
            use_company_scrapers: If True, use company-specific scrapers (RECOMMENDED)
        """
        logger.info("[*] Starting Smart Job Scan (Semantic Matching)")
        logger.info(f"Target: 2026 AI/ML New Graduate roles in Japan")

        all_matches = []

        # Phase 1: Use company-specific scrapers (hits actual job pages)
        if use_company_scrapers:
            logger.info(f"\n[Phase 1] Using company-specific scrapers for accurate job discovery...")

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)

                try:
                    # Get all jobs from company-specific scrapers
                    raw_jobs = await CompanyScrapers.scrape_all_companies(browser)

                    logger.info(f"  Found {len(raw_jobs)} total job postings")

                    # Now apply semantic matching to filter
                    for job in raw_jobs:
                        score = self.semantic_match_score(job['text'], check_must_have=True)

                        if score >= 0.5:  # 50%+ match threshold
                            url_hash = hashlib.sha256(job['url'].encode()).hexdigest()
                            if url_hash not in self.seen_hashes:
                                all_matches.append({
                                    'company': job['company'],
                                    'title': job['title'],
                                    'url': job['url'],
                                    'match_score': score,
                                    'snippet': job['text'][:200]
                                })
                                self.seen_hashes.add(url_hash)
                                logger.info(f"[MATCH] {job['company']}: {job['title']} (score: {score:.2f})")

                except Exception as e:
                    logger.error(f"Error in company scrapers: {e}")
                finally:
                    await browser.close()

        else:
            # Fallback: Generic scraping (less effective)
            logger.info(f"\n[Phase 1] Scanning {len(self.PRIORITY_COMPANIES)} company career pages...")
            for company, url in self.PRIORITY_COMPANIES.items():
                logger.info(f"  -> {company}...")
                matches = await self.scrape_company_page(company, url)
                all_matches.extend(matches)
                await asyncio.sleep(3)  # Be polite

        # Optionally scan job boards
        if scan_job_boards:
            logger.info(f"\n[Phase 2] Scanning {len(self.TECH_JOB_BOARDS)} job board aggregators...")
            for board, url in self.TECH_JOB_BOARDS.items():
                logger.info(f"  -> {board}...")
                matches = await self.scrape_company_page(board, url)
                all_matches.extend(matches)
                await asyncio.sleep(3)

        # Save to database
        logger.info(f"\n[Saving] Writing results to database...")
        new_jobs = 0
        for job in all_matches:
            if self.save_to_db(job):
                new_jobs += 1

        logger.info(f"\n[SUCCESS] Scan complete!")
        logger.info(f"   Total matches found: {len(all_matches)}")
        logger.info(f"   New jobs added: {new_jobs}")
        logger.info(f"   Duplicates skipped: {len(all_matches) - new_jobs}")

        return new_jobs


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='🎯 Smart Job Watcher v2 - Semantic matching for 2026 AI/ML grad roles',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan only priority company career pages (recommended)
  python smart_watcher_v2.py

  # Scan companies + job board aggregators (slower but comprehensive)
  python smart_watcher_v2.py --include-boards

  # Change semantic matching threshold (default: 0.7)
  python smart_watcher_v2.py --threshold 0.65
        """
    )

    parser.add_argument(
        '--include-boards',
        action='store_true',
        help='Also scan job board aggregators (Japan Dev, TokyoDev, etc.)'
    )

    parser.add_argument(
        '--threshold',
        type=float,
        default=0.7,
        help='Semantic matching threshold (0.0-1.0, default: 0.7)'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging with UTF-8 encoding for Windows console
    import sys
    log_level = logging.DEBUG if args.verbose else logging.INFO

    # Configure UTF-8 output for Windows console
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('../logs/smart_watcher.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    logger.info("=" * 60)
    logger.info("[*] Smart Job Watcher v2 - Semantic Matching Edition")
    logger.info("=" * 60)
    logger.info(f"Profile: 2026 AI/ML Graduate | Python, PyTorch, CV")
    logger.info(f"Threshold: {args.threshold:.2f} | Boards: {args.include_boards}")
    logger.info("=" * 60)

    scraper = SmartJobScraper()

    # You can override the threshold if needed
    # scraper.MATCH_THRESHOLD = args.threshold

    new_jobs = await scraper.run_smart_scan(scan_job_boards=args.include_boards)

    if new_jobs > 0:
        logger.info(f"\n[*] Found {new_jobs} new opportunities!")
        logger.info(f"[*] Check the dashboard: http://localhost:8501")
    else:
        logger.info(f"\n[*] No new jobs this scan. Keep watching!")

    return new_jobs


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n[!] Scan interrupted by user")
    except Exception as e:
        logger.error(f"\n[ERROR] Fatal error: {e}", exc_info=True)
