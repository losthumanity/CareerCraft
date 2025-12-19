"""
Integration Module - Connect Watcher with Resume Tailor
Allows seamless resume generation from discovered jobs
"""

import sqlite3
from pathlib import Path
from typing import Optional, List, Dict
import sys

# Add tailor to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'tailor'))

from resume_tailor import ResumeTailor


class JobifyIntegration:
    """Integration between job watcher and resume tailor"""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize integration

        Args:
            db_path: Path to jobs database
        """
        self.project_root = Path(__file__).parent.parent
        self.db_path = db_path or (self.project_root / "watcher" / "jobs.db")
        self.tailor = ResumeTailor()

    def get_recent_jobs(self, limit: int = 10) -> List[Dict]:
        """Get recently discovered jobs

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of job dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, company, title, description, url, first_seen
            FROM jobs
            ORDER BY first_seen DESC
            LIMIT ?
        """, (limit,))

        jobs = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jobs

    def list_jobs_interactive(self):
        """Show jobs and let user select one to tailor resume"""
        jobs = self.get_recent_jobs(20)

        if not jobs:
            print("📭 No jobs found in database yet.")
            print("Run the watcher first: python watcher/smart_watcher_v2.py")
            return

        print("\n" + "=" * 80)
        print("🎯 RECENT JOB OPPORTUNITIES")
        print("=" * 80)

        for i, job in enumerate(jobs, 1):
            print(f"\n{i}. {job['company']} - {job['title']}")
            print(f"   Found: {job['first_seen']}")
            print(f"   URL: {job['url'][:70]}...")

        print("\n" + "=" * 80)

        try:
            choice = input("\nSelect job number to tailor resume (or 'q' to quit): ").strip()

            if choice.lower() == 'q':
                return

            job_num = int(choice)
            if 1 <= job_num <= len(jobs):
                selected_job = jobs[job_num - 1]
                self.tailor_for_job(selected_job)
            else:
                print("❌ Invalid selection")

        except ValueError:
            print("❌ Please enter a valid number")
        except KeyboardInterrupt:
            print("\n\n👋 Cancelled")

    def tailor_for_job(self, job: Dict):
        """Generate tailored resume for a specific job

        Args:
            job: Job dictionary from database
        """
        print(f"\n🚀 Generating tailored resume for:")
        print(f"   {job['company']} - {job['title']}")
        print("=" * 80)

        try:
            output_path = self.tailor.generate_from_db_job(job['id'])

            print("\n" + "=" * 80)
            print("✅ SUCCESS!")
            print("=" * 80)
            print(f"\n📄 Tailored resume saved to:")
            print(f"   {output_path}")
            print(f"\n🔗 Apply here:")
            print(f"   {job['url']}")
            print("\n💡 Next steps:")
            print("   1. Review the tailored resume")
            print("   2. Compile LaTeX to PDF")
            print("   3. Apply with confidence!")

        except Exception as e:
            print(f"\n❌ Error generating resume: {e}")


def main():
    """Main entry point for integration"""
    import os

    # Check for API key
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not set!")
        print("\nSet it in your .env file or environment:")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        return

    integration = JobifyIntegration()
    integration.list_jobs_interactive()


if __name__ == "__main__":
    main()
