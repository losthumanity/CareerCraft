"""
Health Check for All Company Scrapers
Tests each scraper individually and reports results
"""
import asyncio
from playwright.async_api import async_playwright
from company_scrapers import CompanyScrapers
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def health_check():
    print("=" * 80)
    print("WATCHER MODULE HEALTH CHECK")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    results = []
    total_jobs = 0
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        try:
            scrapers = CompanyScrapers()
            
            print(f"\n📊 Testing {len(scrapers.scrapers)} company scrapers...\n")
            
            for i, scraper in enumerate(scrapers.scrapers, 1):
                company_name = scraper.company_name
                print(f"[{i}/{len(scrapers.scrapers)}] Testing {company_name}...")
                
                try:
                    start_time = asyncio.get_event_loop().time()
                    jobs = await scraper.scrape(browser)
                    elapsed = asyncio.get_event_loop().time() - start_time
                    
                    status = "✅ PASS" if len(jobs) > 0 else "⚠️  WARN (0 jobs)"
                    results.append({
                        'company': company_name,
                        'status': 'PASS' if len(jobs) > 0 else 'WARN',
                        'jobs_found': len(jobs),
                        'time': f"{elapsed:.2f}s"
                    })
                    total_jobs += len(jobs)
                    
                    print(f"   {status} - Found {len(jobs)} jobs in {elapsed:.2f}s")
                    
                    # Show sample job if found
                    if jobs:
                        print(f"   Sample: {jobs[0]['title'][:60]}...")
                    
                except Exception as e:
                    results.append({
                        'company': company_name,
                        'status': 'FAIL',
                        'jobs_found': 0,
                        'time': 'N/A',
                        'error': str(e)
                    })
                    print(f"   ❌ FAIL - Error: {str(e)[:60]}...")
                
                print()
            
        finally:
            await browser.close()
    
    # Summary Report
    print("=" * 80)
    print("HEALTH CHECK SUMMARY")
    print("=" * 80)
    print(f"\n{'Company':<30} {'Status':<10} {'Jobs':<10} {'Time':<10}")
    print("-" * 80)
    
    passed = sum(1 for r in results if r['status'] == 'PASS')
    warned = sum(1 for r in results if r['status'] == 'WARN')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    
    for result in results:
        status_icon = {
            'PASS': '✅',
            'WARN': '⚠️ ',
            'FAIL': '❌'
        }[result['status']]
        
        print(f"{result['company']:<30} {status_icon} {result['status']:<8} {result['jobs_found']:<10} {result['time']:<10}")
    
    print("-" * 80)
    print(f"\n📈 OVERALL STATISTICS:")
    print(f"   Total Scrapers:   {len(results)}")
    print(f"   ✅ Passed:        {passed} ({passed/len(results)*100:.1f}%)")
    print(f"   ⚠️  Warned:        {warned} ({warned/len(results)*100:.1f}%)")
    print(f"   ❌ Failed:        {failed} ({failed/len(results)*100:.1f}%)")
    print(f"   📊 Total Jobs:    {total_jobs}")
    
    if failed > 0:
        print(f"\n❌ ISSUES DETECTED:")
        for result in results:
            if result['status'] == 'FAIL':
                print(f"   - {result['company']}: {result.get('error', 'Unknown error')}")
    
    if warned > 0:
        print(f"\n⚠️  WARNINGS:")
        for result in results:
            if result['status'] == 'WARN':
                print(f"   - {result['company']}: Found 0 jobs (may not be an error)")
    
    print("\n" + "=" * 80)
    
    # Overall health status
    if failed == 0 and warned == 0:
        print("🎉 ALL SYSTEMS OPERATIONAL - All scrapers working perfectly!")
    elif failed == 0:
        print("✅ SYSTEMS HEALTHY - All scrapers functional, some found no jobs")
    else:
        print("⚠️  ATTENTION REQUIRED - Some scrapers need investigation")
    
    print("=" * 80)
    
    return {
        'total': len(results),
        'passed': passed,
        'warned': warned,
        'failed': failed,
        'total_jobs': total_jobs
    }

if __name__ == "__main__":
    asyncio.run(health_check())
