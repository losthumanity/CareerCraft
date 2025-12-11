"""
Database utility to clean up broken/invalid job entries
"""
import sqlite3

def clean_database():
    """Remove broken or test entries from database."""
    conn = sqlite3.connect('../shared/jobs.db')
    cursor = conn.cursor()

    # Get all jobs
    cursor.execute("SELECT id, title, url FROM jobs")
    jobs = cursor.fetchall()

    print(f"Found {len(jobs)} jobs in database")
    print("\n" + "="*80)

    for job_id, title, url in jobs:
        print(f"\nID: {job_id}")
        print(f"Title: {title}")
        print(f"URL: {url}")

        # Check for broken URLs
        if not url.startswith('http'):
            print("❌ Invalid URL - Missing protocol")
        elif 'javascript:' in url.lower():
            print("❌ Invalid URL - JavaScript link")
        elif len(url) < 20:
            print("❌ Suspicious URL - Too short")
        else:
            print("✅ URL looks valid")

    print("\n" + "="*80)
    print(f"\nOptions:")
    print("1. Clear ALL jobs")
    print("2. Clear only invalid URLs")
    print("3. Cancel")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == '1':
        cursor.execute("DELETE FROM jobs")
        conn.commit()
        print(f"✅ Cleared all {cursor.rowcount} jobs")
    elif choice == '2':
        # Delete invalid URLs
        cursor.execute("""
            DELETE FROM jobs WHERE
            url NOT LIKE 'http%' OR
            url LIKE '%javascript:%' OR
            LENGTH(url) < 20
        """)
        conn.commit()
        print(f"✅ Cleared {cursor.rowcount} invalid jobs")
    else:
        print("❌ Cancelled")

    conn.close()

if __name__ == "__main__":
    clean_database()
