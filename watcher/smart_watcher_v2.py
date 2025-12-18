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
from dataclasses import dataclass, field
from typing import List, Dict, Optional
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


@dataclass
class CompanyRule:
    click_selectors: List[str] = field(default_factory=list)
    allow_text_contains: List[str] = field(default_factory=list)
    extra_job_url_patterns: List[str] = field(default_factory=list)
    bypass_title_skip: bool = False


class SmartJobScraper:
    """Semantic job matcher with targeted scraping."""

    PRIORITY_COMPANIES = {
        'LY Corporation (LINE)': 'https://www.lycorp.co.jp/en/recruit/newgrads/engineer/',
        'Rakuten Group': 'https://global.rakuten.com/corp/careers/graduates/recruit_engineer/?l-id=%2Fgraduates%2Fheader-e',
        'ByteDance (TikTok) Japan': 'https://joinbytedance.com/earlycareers',
        'Sony Group (Global Recruitment)': 'https://www.sony.com/en/SonyInfo/Careers/japan/',
        'Woven by Toyota': 'https://woven.toyota/en/careers/',
        'Mercari Japan': 'https://careers.mercari.com/en/job-categories/engineering/',
        'Preferred Networks (PFN)': 'https://www.preferred.jp/en/careers',
        'Toshiba (Global Recruitment)': 'https://www.global.toshiba/ww/recruit/corporate/university/newgraduates.html',
    }

    TECH_JOB_BOARDS = {
        'Japan Dev': 'https://japan-dev.com/jobs/machine-learning',
        'TokyoDev': 'https://tokyodev.com/jobs/machine-learning',
        'Daijob': 'https://daijob.com/en/jobs/search_result?job_types[]=614',
        'LinkedIn': 'https://www.linkedin.com/jobs/search/?keywords=AI%20Engineer%20Japan%202026&location=Japan',
        'Jobs in Japan': 'https://jobsinjapan.com/jobs/search?q=AI+Engineer&category=it',
    }

    # Keywords that MUST appear (hard filter) - at least ONE must match
    YEAR_KEYWORDS = [
        '2026', 'class of 2026'
    ]

    GRAD_KEYWORDS = [
        'graduate', 'new grad', 'fresh graduate', 'entry level', 'early career',
        '0-2 years', 'recent graduate', 'junior', 'new graduate', '卒業'
    ]

    MUST_HAVE = YEAR_KEYWORDS + GRAD_KEYWORDS

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

    # Navigation/UI elements to ALWAYS exclude (not real jobs)
    EXCLUDE_PATTERNS = [
        # Navigation/UI
        'sign up', 'sign in', 'login', 'logout', 'register', 'create account',
        'newsletter', 'subscribe', 'unsubscribe',
        'search jobs', 'browse jobs', 'view all', 'see all', 'show more',
        'filter', 'sort by', 'refine search',

        # Site sections
        'about us', 'about', 'contact', 'contact us', 'help', 'faq',
        'privacy', 'terms', 'cookie', 'legal',
        'blog', 'news', 'press', 'media',
        'pricing', 'plans', 'features',

        # Directories/Lists
        'companies', 'top companies', 'company directory',
        'resources', 'guides', 'tips', 'advice',
        'experiences', 'stories', 'testimonials',

        # Social/External
        'twitter', 'facebook', 'linkedin', 'instagram',
        'youtube', 'github', 'discord', 'slack',

        # Common false positives
        'remote companies', 'designer experiences',
        'developer jobs', 'japan developer' # Generic category pages
    ]

    SKIP_TITLE_KEYWORDS = [
        'learn more', 'guidelines for application', 'mid-career', 'kpi trends',
        'financial statement', 'analyst coverage', 'message from', 'in the spotlight',
        'story:', 'search job openings', 'employee conditions', 'manual check recommended'
    ]

    DEFAULT_MAX_LINKS = 30
    JOB_BOARD_MAX_LINKS = 12
    COMPANY_LINK_LIMITS = {
        'Woven by Toyota': 25,
        'Rakuten Group': 20,
        'LY Corporation (LINE)': 15,
    }

    COMPANY_RULES: Dict[str, CompanyRule] = {
        'Rakuten Group': CompanyRule(
            click_selectors=[
                'a:has-text("View open positions")',
                'a:has-text("View open positions from here")',
            ],
            allow_text_contains=['view open positions', 'apply'],
            extra_job_url_patterns=['/recruit', '/opportunities', '/joiners']
        ),
        'LY Corporation (LINE)': CompanyRule(
            click_selectors=['button:has-text("Apply")'],
            allow_text_contains=[
                'software engineering specialist',
                'infra engineering expert',
                'security engineering expert',
                'apply'
            ],
            extra_job_url_patterns=['/jd']
        ),
        'Sony Group (Global Recruitment)': CompanyRule(
            allow_text_contains=['apply for job opening', 'view all positions', 'sony ai'],
            extra_job_url_patterns=['myworkdayjobs.com', '/wd/', '/apply']
        ),
        'Mercari Japan': CompanyRule(
            allow_text_contains=['students & new graduates', 'engineering'],
            extra_job_url_patterns=['boards.greenhouse.io']
        ),
        'Woven by Toyota': CompanyRule(
            allow_text_contains=['learn more', 'apply'],
            extra_job_url_patterns=['/careers/', '/jobs/'],
            bypass_title_skip=True
        ),
    }

    def __init__(self, db_path='../shared/jobs.db', match_threshold: float = 0.7):
        self.db_path = db_path
        self.match_threshold = match_threshold
        self._ensure_database()
        self.seen_hashes = self._load_seen_hashes()

    def _get_company_rule(self, company: Optional[str]) -> Optional[CompanyRule]:
        if not company:
            return None
        return self.COMPANY_RULES.get(company)

    def _is_valid_job_url(self, url: str, text: str, company: Optional[str] = None) -> bool:
        """Validate if URL is likely a real job posting (STRICT MODE)."""
        url_lower = url.lower()
        text_lower = text.lower()

        if self._should_skip_title(text, company):
            return False

        rule = self._get_company_rule(company)
        allow_text_override = False
        if rule and rule.allow_text_contains:
            allow_text_override = any(token in text_lower for token in rule.allow_text_contains)

        # Exclude obvious non-job URLs
        exclude_patterns = [
            '/login', '/signin', '/signup', '/register',
            '/about', '/contact', '/privacy', '/terms',
            '/blog', '/news', '/press', '/media', '/article',
            '/people/', '/employee/', '/staff/', '/team/',  # Employee profiles
            '/companies', '/directory',
            '/search', '/filter', '/browse',
            'facebook.com', 'twitter.com', 'linkedin.com/company',
            'instagram.com', 'youtube.com',
            '.pdf', '.jpg', '.png', '.gif',
            'javascript:', 'mailto:', 'tel:', '#',
            '/financial', '/investor', '/ir/', '/coverage',  # Financial pages
            '/guidelines', '/application', '/apply-guide'  # Application guides (not jobs)
        ]

        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False

        # Check for excluded text patterns
        for pattern in self.EXCLUDE_PATTERNS:
            if pattern in text_lower:
                return False

        # Reject generic button text (not specific job titles)
        generic_buttons = [
            'learn more', 'read more', 'view', 'see all', 'apply now', 'join us',
            'explore', 'discover', 'find out', 'click here', 'details',
            'view job', 'view jobs', 'see jobs', 'browse', 'search'
        ]
        if text_lower.strip() in generic_buttons:
            return False

        # Reject category/directory pages (not specific job listings)
        category_pages = [
            'engineering', 'engineers', 'developer', 'developers',
            'new graduates', 'students', 'internship', 'internships',
            'job categories', 'all jobs', 'open positions',
            'career opportunities', 'join our team', 'work with us',
            'manager jobs', 'senior jobs', 'junior jobs'
        ]
        if text_lower.strip() in category_pages:
            return False

        # STRICT: Must have strong job URL pattern
        job_url_patterns = [
            '/job/', '/jobs/', '/position/', '/positions/',
            '/career/', '/careers/', '/opening/', '/vacancy',
            '/role/', '/opportunity', '/requisition'
        ]
        if rule and rule.extra_job_url_patterns:
            job_url_patterns.extend(rule.extra_job_url_patterns)
        has_job_pattern = any(pattern in url_lower for pattern in job_url_patterns)

        # If text looks like a real job title (contains job-related words)
        job_title_words = ['engineer', 'developer', 'scientist', 'analyst',
                          'designer', 'manager', 'specialist', 'architect',
                          'intern', 'graduate', 'AI', 'ML', 'data', 'software',
                          'backend', 'frontend', 'full stack', 'devops']
        has_job_words = allow_text_override or any(word.lower() in text_lower for word in job_title_words)

        # STRICT: Accept ONLY if both URL pattern AND job title words present
        return has_job_pattern and has_job_words

    def _ensure_database(self) -> None:
        """Ensure the SQLite schema exists before inserting."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    keywords_matched TEXT,
                    date_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    applied_status TEXT DEFAULT 'Pending',
                    notes TEXT,
                    resume_generated BOOLEAN DEFAULT 0
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scraper_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    company TEXT,
                    status TEXT,
                    jobs_found INTEGER DEFAULT 0,
                    error_message TEXT
                )
            ''')
            conn.commit()
        except Exception as exc:
            logger.error(f"Failed to initialize database: {exc}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _should_skip_title(self, text: str, company: Optional[str] = None) -> bool:
        """Return True if anchor text is clearly not a job title."""
        normalized = text.strip().lower()

        rule = self._get_company_rule(company)
        if rule:
            if rule.bypass_title_skip:
                return False
            if rule.allow_text_contains and any(token in normalized for token in rule.allow_text_contains):
                return False

        if len(normalized) < 15:
            return True

        return any(keyword in normalized for keyword in self.SKIP_TITLE_KEYWORDS)

    def _max_links_for(self, company: str, fallback: Optional[int] = None) -> int:
        """Return a sane per-company cap on how many links we inspect."""
        base_limit = fallback if fallback is not None else self.DEFAULT_MAX_LINKS
        return self.COMPANY_LINK_LIMITS.get(company, base_limit)

    async def _apply_company_actions(self, page, company: str) -> None:
        """Fire company-specific clicks (CTA buttons, tabs, etc.)."""
        rule = self._get_company_rule(company)
        if not rule or not rule.click_selectors:
            return

        for selector in rule.click_selectors:
            try:
                await page.click(selector, timeout=2500)
                await page.wait_for_timeout(1000)
            except Exception:
                continue

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

    def semantic_match_score(
        self,
        job_text: str,
        required_keywords: Optional[List[str]] = None,
    ) -> float:
        """
        Calculate semantic similarity between job and your profile.
        Returns: 0.0 to 1.0 (higher = better match)

        Args:
            job_text: The job description or link text
            required_keywords: Override the default MUST_HAVE keywords. Pass an empty list to skip.
        """
        # Quick keyword filter first (saves compute)
        job_lower = job_text.lower()

        keywords = self.MUST_HAVE if required_keywords is None else required_keywords

        if keywords:
            if not any(keyword in job_lower for keyword in keywords):
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

    async def _get_full_page_text(self, page, url: str) -> str:
        """
        Navigates to a URL and extracts the full, clean text content.
        This is our 'Level 2' scraper.
        """
        try:
            await page.goto(url, wait_until='networkidle', timeout=20000)
            await page.wait_for_timeout(1500)  # Extra wait for dynamic content
            html = await page.content()
            soup = BeautifulSoup(html, 'html.parser')

            # Attempt to find the main content area for cleaner text
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            return main_content.get_text(separator=' ', strip=True)
        except Exception as e:
            logger.warning(f"  -> Failed to get details from {url}: {str(e)}")
            return ""

    async def scrape_company_page(
        self,
        company: str,
        url: str,
        *,
        browser=None,
        max_links: Optional[int] = None,
        required_keywords: Optional[List[str]] = None,
    ) -> List[Dict]:
        """Scrape a career page using a reusable Playwright browser."""

        logger.info(f"[*] Scraping {company} (L1)...")
        link_cap = self._max_links_for(company, fallback=max_links)

        async def _run(page) -> List[Dict]:
            matches: List[Dict] = []

            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)
                await self._apply_company_actions(page, company)

                # Attempt to reveal lazy-loaded cards
                for i in range(5):
                    try:
                        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        await page.wait_for_timeout(1200)
                    except Exception:
                        break

                    if i < 3:
                        load_more_selectors = [
                            'button:has-text("Load More")',
                            'button:has-text("Show More")',
                            'a:has-text("Load More")',
                            'a:has-text("Show More")',
                            '[data-test="load-more"]'
                        ]
                        for selector in load_more_selectors:
                            try:
                                await page.click(selector, timeout=1500)
                                await page.wait_for_timeout(800)
                                break
                            except Exception:
                                continue

                soup = BeautifulSoup(await page.content(), 'html.parser')
                potential_links: List[Dict[str, str]] = []
                seen_urls = set()

                from urllib.parse import urljoin

                for link in soup.find_all('a', href=True):
                    link_text = link.get_text(strip=True) or link.get('aria-label', '').strip() or link.get('title', '').strip()
                    link_url = link['href']

                    if not link_text or not link_url:
                        continue

                    absolute_url = urljoin(url, link_url)

                    if absolute_url in seen_urls:
                        continue

                    if self._is_valid_job_url(absolute_url, link_text, company):
                        potential_links.append({'url': absolute_url, 'title': link_text})
                        seen_urls.add(absolute_url)

                if not potential_links:
                    logger.warning("  -> Found 0 job links. Site may be gated or fully dynamic.")
                    logger.warning(f"  -> Manual check recommended: {url}")
                    return matches

                if len(potential_links) > link_cap:
                    logger.warning(f"  -> Limiting to {link_cap} links (found {len(potential_links)})")
                    potential_links = potential_links[:link_cap]

                for i, link_info in enumerate(potential_links):
                    job_url = link_info['url']
                    job_title = link_info['title']

                    url_hash = hashlib.sha256(job_url.encode()).hexdigest()
                    if url_hash in self.seen_hashes:
                        continue

                    logger.info(f"  -> (L2) Analyzing [{i+1}/{len(potential_links)}]: {job_title[:60]}...")
                    full_job_text = await self._get_full_page_text(page, job_url)

                    if not full_job_text or len(full_job_text) < 200:
                        logger.debug("  -> Skipping (insufficient content)")
                        continue

                    score = self.semantic_match_score(full_job_text, required_keywords)

                    if score >= self.match_threshold:
                        matches.append({
                            'company': company,
                            'title': job_title,
                            'url': job_url,
                            'match_score': score,
                            'snippet': full_job_text[:250].strip()
                        })
                        self.seen_hashes.add(url_hash)
                        logger.info(f"  [MATCH] {company}: {job_title} (Score: {score:.2f})")

            except Exception as exc:
                logger.error(f"Error scraping {company}: {exc}")

            return matches

        async def _with_browser(active_browser) -> List[Dict]:
            page = await active_browser.new_page()
            try:
                return await _run(page)
            finally:
                await page.close()

        if browser is not None:
            return await _with_browser(browser)

        async with async_playwright() as playwright_runtime:
            temp_browser = await playwright_runtime.chromium.launch(headless=True)
            try:
                return await _with_browser(temp_browser)
            finally:
                await temp_browser.close()

    async def run_company_scrapers(self, browser) -> List[Dict]:
        """Use purpose-built scrapers for sites that break generic parsing."""

        logger.info("\n[Phase 0] Running company-specific scrapers...")
        matches: List[Dict] = []

        try:
            job_payloads = await CompanyScrapers.scrape_all_companies(browser)
        except Exception as exc:
            logger.error(f"Company-specific scrapers failed: {exc}")
            return matches

        for payload in job_payloads:
            job_url = payload.get('url')
            job_title = payload.get('title', '').strip()
            job_text = payload.get('text') or job_title

            if not job_url or not job_title or not job_text:
                continue

            url_hash = hashlib.sha256(job_url.encode()).hexdigest()
            if url_hash in self.seen_hashes:
                continue

            score = self.semantic_match_score(job_text, required_keywords=self.GRAD_KEYWORDS)
            if score < self.match_threshold:
                continue

            matches.append({
                'company': payload.get('company', 'Unknown'),
                'title': job_title,
                'url': job_url,
                'match_score': score,
                'snippet': job_text[:250].strip()
            })
            self.seen_hashes.add(url_hash)
            logger.info(f"  [MATCH] {payload.get('company', 'Unknown')}: {job_title} (Score: {score:.2f})")

        if not matches:
            logger.info("  -> Company-specific scrapers did not find any high-confidence matches.")

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

        async with async_playwright() as playwright_runtime:
            browser = await playwright_runtime.chromium.launch(headless=True)
            try:
                if use_company_scrapers:
                    matches = await self.run_company_scrapers(browser)
                    all_matches.extend(matches)

                logger.info(f"\n[Phase 1] Starting 2-Level Scan for {len(self.PRIORITY_COMPANIES)} priority companies...")
                for company, url in self.PRIORITY_COMPANIES.items():
                    matches = await self.scrape_company_page(
                        company,
                        url,
                        browser=browser,
                    )
                    all_matches.extend(matches)
                    await asyncio.sleep(2)

                if scan_job_boards:
                    logger.info(f"\n[Phase 2] Scanning {len(self.TECH_JOB_BOARDS)} job board aggregators...")
                    for board, url in self.TECH_JOB_BOARDS.items():
                        logger.info(f"  -> {board}...")
                        matches = await self.scrape_company_page(
                            board,
                            url,
                            browser=browser,
                            max_links=self.JOB_BOARD_MAX_LINKS,
                            required_keywords=self.GRAD_KEYWORDS,
                        )
                        all_matches.extend(matches)
                        await asyncio.sleep(3)
            finally:
                await browser.close()

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
        help='[EXPERIMENTAL] Scan job board aggregators - often returns false positives, not recommended'
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

    scraper = SmartJobScraper(match_threshold=args.threshold)

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
