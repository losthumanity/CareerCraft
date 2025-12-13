# Smart Job Watcher Architecture - Realistic Plan

## Target Sites (Priority Order)

### Tier 1: Company Career Pages (Direct Source)
**Focus on your target companies:**
```python
TARGET_COMPANIES = {
    "Sony": "https://www.sony.com/en/SonyInfo/CorporateInfo/Careers/",
    "Woven by Toyota": "https://woven-by-toyota.com/en/careers",
    "Rakuten": "https://global.rakuten.com/corp/careers/",
    "Mercari": "https://careers.mercari.com/",
    "Preferred Networks": "https://www.preferred.jp/en/news/",
    "LINE": "https://linecorp.com/en/career/",
}
```
**Why:** Direct from source, less noise, higher quality

### Tier 2: Tech-Focused Job Boards
1. **Japan Dev** (japan-dev.com) - English, visa support filters
2. **LinkedIn** (linkedin.com/jobs) - API access possible
3. **CareerCross** (careercross.com) - IT/Engineering bilingual

### Tier 3: Fallback/Supplementary
- Daijob (bilingual)
- WeXpats (foreigner-focused)

## Recommended Tech Stack

### Scraping Layer
```python
# Simple, effective, maintainable
- requests / httpx  (for static pages)
- playwright (for dynamic JS pages)
- beautifulsoup4 (parsing HTML)
- selectolax (faster HTML parsing)
```

### Detection & Matching
```python
# Semantic search WITHOUT full RAG
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast, free, local

# Create embeddings for job descriptions
job_embedding = model.encode(job_description)
profile_embedding = model.encode(your_profile)

# Simple cosine similarity
similarity = np.dot(job_embedding, profile_embedding) / (
    np.linalg.norm(job_embedding) * np.linalg.norm(profile_embedding)
)
```

### Change Detection
```python
import hashlib

def has_changed(url, content):
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    # Compare with stored hash
    return content_hash != stored_hashes.get(url)
```

## Architecture

```
watcher/
├── scrapers/
│   ├── base.py              # Base scraper class
│   ├── company_direct.py    # Sony, Toyota, Rakuten scrapers
│   ├── japan_dev.py         # Japan Dev specific
│   ├── linkedin.py          # LinkedIn (use API if possible)
│   └── generic.py           # Fallback scraper
├── matching/
│   ├── semantic_matcher.py  # Embedding-based matching
│   └── keyword_filter.py    # Simple keyword filtering
├── storage/
│   └── db_handler.py        # SQLite operations
├── notifications/
│   └── notifier.py          # Discord/Email alerts
└── watcher.py               # Main orchestrator
```

## Why This Beats crawl4ai + RAG

| Aspect | Your Plan | Better Approach | Winner |
|--------|-----------|-----------------|--------|
| Complexity | High (crawl4ai + RAG) | Low (BS4 + embeddings) | ✅ Better |
| Cost | LLM API costs | Free, runs locally | ✅ Better |
| Speed | Slower (LLM calls) | Fast (local inference) | ✅ Better |
| Maintenance | Complex dependencies | Simple, stable libs | ✅ Better |
| Accuracy | Overkill for structured data | Appropriate for job boards | ✅ Better |
| Learning | Black box | You understand every piece | ✅ Better |

## Implementation Priority

### Phase 1: MVP (This Weekend)
1. ✅ Fix dashboard (done)
2. ⬜ Build 1 scraper (Sony career page)
3. ⬜ Add semantic matching (sentence-transformers)
4. ⬜ Discord notification on new job

### Phase 2: Scale (Next Week)
1. ⬜ Add 3 more company scrapers
2. ⬜ Add Japan Dev scraper
3. ⬜ Implement change detection
4. ⬜ Schedule with cron/Task Scheduler

### Phase 3: Polish (Later)
1. ⬜ LinkedIn scraper (or API)
2. ⬜ Resume auto-generation on match
3. ⬜ A/B test keyword vs semantic matching

## Reality Check: What Actually Matters

**80% of your success comes from:**
1. ✅ **Applying early** when jobs open
2. ✅ **Tailored resume** for each company
3. ✅ **Direct company pages** (not aggregators)
4. ✅ **Networking** on LinkedIn
5. ✅ **Referrals** (reach out to Sony/Toyota employees)

**20% comes from:**
- Fancy scraping tech
- RAG/LLM features
- Dashboard aesthetics

## The Uncomfortable Truth

Your current watcher (`watcher.py`) is probably a placeholder. Let me check...
