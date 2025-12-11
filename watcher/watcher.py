"""
The Watcher - Job Monitoring Module
Monitors career pages for new job postings matching specified keywords.
Stores results in SQLite database for dashboard integration.
"""

import requests
from bs4 import BeautifulSoup
import yaml
import os
import sqlite3
from datetime import datetime
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv
import time
import logging

# Load environment variables from parent directory
load_dotenv('../.env')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/watcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class JobWatcher:
    """Monitors job boards for new postings."""

    def __init__(self, config_path='../shared/config.yaml'):
        """Initialize the watcher with configuration."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.user_agent = os.getenv('USER_AGENT', 'Mozilla/5.0')
        self.db_path = '../shared/jobs.db'
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for storing job postings."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create jobs table
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

        # Create scraper logs table
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
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")

    def _save_job_to_db(self, company, title, url, keywords):
        """Save a job posting to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR IGNORE INTO jobs (company, title, url, keywords_matched, applied_status)
                VALUES (?, ?, ?, ?, 'Pending')
            ''', (company, title, url, ', '.join(keywords)))

            if cursor.rowcount > 0:
                logger.info(f"Saved to database: {title}")

            conn.commit()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Database error: {e}")
            return False

    def _log_scraper_run(self, company, status, jobs_found=0, error_message=None):
        """Log scraper run to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO scraper_logs (company, status, jobs_found, error_message)
                VALUES (?, ?, ?, ?)
            ''', (company, status, jobs_found, error_message))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log scraper run: {e}")

    def send_discord_alert(self, message):
        """Send notification to Discord webhook."""
        if not self.discord_webhook:
            logger.warning("Discord webhook not configured")
            return

        try:
            webhook = DiscordWebhook(url=self.discord_webhook, content=message)
            response = webhook.execute()
            logger.info(f"Discord notification sent: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")

    def _normalize_url(self, url, base_url):
        """Normalize and validate URLs."""
        from urllib.parse import urljoin, urlparse

        # Handle relative URLs
        if not url.startswith(('http://', 'https://', '//')):
            url = urljoin(base_url, url)
        elif url.startswith('//'):
            url = 'https:' + url

        # Validate URL structure
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None

        # Remove fragments and clean query strings
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            clean_url += f"?{parsed.query}"

        return clean_url

    def _is_valid_job_link(self, url, text, company_name):
        """Validate if a link is likely a valid job posting."""
        # Exclude common non-job pages
        exclude_patterns = [
            'javascript:', 'mailto:', 'tel:', '#',
            '/about', '/contact', '/privacy', '/terms',
            '/login', '/signin', '/signup', '/register',
            'facebook.com', 'twitter.com', 'linkedin.com',
            'instagram.com', '.pdf', '.jpg', '.png', '.gif'
        ]

        url_lower = url.lower()
        for pattern in exclude_patterns:
            if pattern in url_lower:
                return False

        # Must have meaningful text (at least 10 chars)
        if len(text) < 10:
            return False

        # Job-related URL patterns (positive signals)
        job_patterns = ['job', 'career', 'position', 'opening', 'recruit', 'hiring']
        url_text = url_lower + ' ' + text.lower()

        # If URL or text contains job-related terms, it's more likely valid
        has_job_indicator = any(pattern in url_text for pattern in job_patterns)

        return True  # Let keyword matching be the primary filter

    def check_company(self, company):
        """Check a single company's job board."""
        logger.info(f"Checking {company['name']}...")
        jobs_found = 0

        try:
            headers = {
                'User-Agent': self.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            response = requests.get(
                company['url'],
                headers=headers,
                timeout=self.config['scraping']['timeout_seconds'],
                allow_redirects=True
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract job links with better targeting
            # Try specific job listing containers first
            job_containers = soup.find_all(['article', 'div'], class_=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['job', 'position', 'career', 'opening']
            ))

            # If no specific containers, search all links
            if not job_containers:
                job_containers = [soup]

            matches_found = []
            seen_urls = set()

            for container in job_containers:
                links = container.find_all('a', href=True)

                for link in links:
                    link_text = link.get_text().strip()
                    link_url = link.get('href', '')

                    # Skip empty or invalid links
                    if not link_text or not link_url:
                        continue

                    # Normalize URL
                    full_url = self._normalize_url(link_url, company['url'])
                    if not full_url:
                        continue

                    # Skip duplicates in this scan
                    if full_url in seen_urls:
                        continue

                    # Validate job link
                    if not self._is_valid_job_link(full_url, link_text, company['name']):
                        continue

                    # Check if any keyword appears in the link text or surrounding context
                    matched_keywords = []

                    # Get parent context for better matching
                    parent_text = link.parent.get_text() if link.parent else ''
                    combined_text = f"{link_text} {parent_text}".lower()

                    for keyword in company['keywords']:
                        if keyword.lower() in combined_text:
                            matched_keywords.append(keyword)

                    if matched_keywords:
                        seen_urls.add(full_url)

                        # Try to save to database (will skip if duplicate)
                        if self._save_job_to_db(company['name'], link_text, full_url, matched_keywords):
                            matches_found.append({
                                'keywords': matched_keywords,
                                'title': link_text,
                                'url': full_url
                            })
                            jobs_found += 1

            # Send alerts for new matches
            for match in matches_found:
                alert_msg = (
                    f"🚨 **NEW JOB MATCH FOUND!**\n"
                    f"**Company:** {company['name']}\n"
                    f"**Keywords:** {', '.join(match['keywords'])}\n"
                    f"**Title:** {match['title']}\n"
                    f"**URL:** {match['url']}\n"
                    f"**Found:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                logger.info(f"Match found: {match['title']}")
                self.send_discord_alert(alert_msg)

            if not matches_found:
                logger.info(f"No new matches for {company['name']}")

            # Log successful run
            self._log_scraper_run(company['name'], 'Success', jobs_found)

        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking {company['name']}: {e}")
            self._log_scraper_run(company['name'], 'Error', 0, str(e))
        except Exception as e:
            logger.error(f"Unexpected error for {company['name']}: {e}")
            self._log_scraper_run(company['name'], 'Error', 0, str(e))

    def run(self, test_mode=False):
        """Run the watcher for all configured companies."""
        logger.info("=" * 50)
        logger.info("Job Watcher Started")
        logger.info("=" * 50)

        for company in self.config['companies']:
            self.check_company(company)

            # Respect rate limiting
            if not test_mode:
                delay = self.config['scraping']['delay_between_requests']
                logger.info(f"Waiting {delay} seconds before next check...")
                time.sleep(delay)

        logger.info("Job Watcher Completed")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Job Watcher - Monitor career pages')
    parser.add_argument('--test', action='store_true', help='Run in test mode (no delays)')
    args = parser.parse_args()

    watcher = JobWatcher()
    watcher.run(test_mode=args.test)


if __name__ == "__main__":
    main()
