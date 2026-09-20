"""Quick test of the web search + scraping pipeline."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app import search_duckduckgo, scrape_urls, build_web_search_prompt

# Step 1: Search
print("=== SEARCHING DuckDuckGo ===")
sources = search_duckduckgo("what is python programming", max_results=2)
for s in sources:
    print(f"  [{s['title']}] {s['url']}")

if not sources:
    print("  (No results - may be a network issue, trying with different query...)")
    sources = search_duckduckgo("python language", max_results=2)
    for s in sources:
        print(f"  [{s['title']}] {s['url']}")

# Step 2: Scrape
print("\n=== SCRAPING URLs ===")
urls = [s["url"] for s in sources]
scraped = scrape_urls(urls)
for r in scraped:
    preview = r["content"][:200].replace('\n', ' ') if r["content"] else "(empty)"
    print(f"  {r['url']}: {len(r['content'])} chars")
    print(f"    Preview: {preview}...")

# Step 3: Build prompt
print("\n=== BUILT PROMPT (first 400 chars) ===")
prompt = build_web_search_prompt("what is python programming", sources, scraped)
print(prompt[:400])

print("\nPipeline test complete!")
