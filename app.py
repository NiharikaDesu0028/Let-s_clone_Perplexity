from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from google import genai
from google.genai import types
import logging
import traceback
import PyPDF2
import io
import time
import os
import json
import uuid
import asyncio
from duckduckgo_search import DDGS
import requests as http_requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
# How to set the GEMINI_API_KEY environment variable:
#   - Windows (PowerShell): $env:GEMINI_API_KEY = "your-api-key-here"
#   - Windows (Command Prompt): set GEMINI_API_KEY="your-api-key-here"
#   - Linux/macOS: export GEMINI_API_KEY="your-api-key-here"
#   - Or create a .env file in the project root (see .env.example)
API_KEY = os.getenv("GEMINI_API_KEY")

# Optional fallback: load GEMINI_API_KEY from local .env file if not already set
if not API_KEY and os.path.exists(".env"):
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "GEMINI_API_KEY":
                        API_KEY = v.strip().strip("'\"")
                        os.environ["GEMINI_API_KEY"] = API_KEY
                        break
    except Exception:
        pass

THREADS_FILE = "threads.json"

# State
current_thread_id = None
threads_data = {} # {id: {title: str, history: [], pdf_context: str, pdf_filename: str, pdf_filesize: str}}

def get_human_readable_size(num):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} TB"

def load_threads_from_disk():
    global threads_data
    if os.path.exists(THREADS_FILE):
        try:
            with open(THREADS_FILE, "r") as f:
                threads_data = json.load(f)
        except Exception as e:
            logger.error(f"Error loading threads.json: {e}")
            threads_data = {}

def save_threads_to_disk():
    try:
        with open(THREADS_FILE, "w") as f:
            json.dump(threads_data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving threads.json: {e}")

# Initialize
load_threads_from_disk()
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Gemini Client: {e}")

def extract_text_from_pdf(file_stream):
    try:
        reader = PyPDF2.PdfReader(file_stream)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""


# ─── WEB SEARCH FUNCTIONS ───────────────────────────────────────────────

def search_duckduckgo(query, max_results=3):
    """Search DuckDuckGo and return top results with title, URL, and snippet."""
    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=max_results))
        sources = []
        for r in results:
            sources.append({
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", "")
            })
        return sources
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        return []


def scrape_single_url(url, max_chars=2000):
    """Scrape a single URL using requests + BeautifulSoup."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    try:
        resp = http_requests.get(url, headers=headers, timeout=6, allow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'iframe']):
            tag.decompose()
            
        main = soup.find('main') or soup.find('article') or soup.find('div', {'role': 'main'})
        text = main.get_text(separator='\n', strip=True) if main else soup.get_text(separator='\n', strip=True)
        
        # Clean up: collapse multiple newlines, trim
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = '\n'.join(lines)
        
        return {"url": url, "content": clean_text[:max_chars]}
    except Exception as e:
        logger.warning(f"Scrape failed for {url}: {e}")
        return {"url": url, "content": ""}

def scrape_urls(urls, max_chars_per_page=2000):
    """Scrape multiple URLs in parallel."""
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_map = {executor.submit(scrape_single_url, url, max_chars_per_page): url for url in urls}
        for future in as_completed(future_map):
            results.append(future.result())
    return results



def build_web_search_prompt(user_message, sources, scraped_contents):
    """Build a prompt that includes web search results for the AI to cite."""
    prompt_parts = []
    
    # System instruction
    prompt_parts.append(
        "You are a helpful AI search assistant. You have been given web search results "
        "to help answer the user's question. Use the information from these sources to "
        "provide a comprehensive, accurate answer.\n\n"
        "IMPORTANT RULES:\n"
        "1. Cite your sources using [1], [2], [3] notation inline in your answer.\n"
        "2. Only cite information that actually comes from the sources provided.\n"
        "3. If the sources don't contain enough information, say so honestly.\n"
        "4. Format your answer in clear, readable markdown.\n"
        "5. Be concise but thorough."
    )
    
    # Add source context
    source_context = "\n\nWEB SEARCH RESULTS:\n"
    for i, source in enumerate(sources):
        source_context += f"\n--- SOURCE [{i+1}] ---\n"
        source_context += f"Title: {source['title']}\n"
        source_context += f"URL: {source['url']}\n"
        source_context += f"Snippet: {source['snippet']}\n"
        
        # Add scraped content if available
        matching_scrape = next((s for s in scraped_contents if s["url"] == source["url"]), None)
        if matching_scrape and matching_scrape["content"]:
            source_context += f"Full Content:\n{matching_scrape['content']}\n"
    
    prompt_parts.append(source_context)
    prompt_parts.append(f"\nUSER QUESTION: {user_message}")
    
    return "\n\n---\n\n".join(prompt_parts)


# ─── ROUTES ──────────────────────────────────────────────────────────────

@app.route('/threads', methods=['GET'])
def get_threads():
    summary = []
    for tid, data in threads_data.items():
        summary.append({
            "id": tid,
            "title": data.get("title", "Untitled Thread"),
            "has_pdf": bool(data.get("pdf_context")),
            "pdf_filename": data.get("pdf_filename", ""),
            "pdf_filesize": data.get("pdf_filesize", ""),
            "is_bizmind": data.get("is_bizmind", False)
        })
    return jsonify(summary)

@app.route('/threads/<thread_id>', methods=['GET'])
def load_thread(thread_id):
    global current_thread_id
    if thread_id in threads_data:
        current_thread_id = thread_id
        return jsonify(threads_data[thread_id])
    return jsonify({"error": "Thread not found"}), 404

@app.route('/threads/<thread_id>', methods=['DELETE'])
def delete_thread(thread_id):
    global current_thread_id, threads_data
    if thread_id in threads_data:
        del threads_data[thread_id]
        if current_thread_id == thread_id:
            current_thread_id = None
        save_threads_to_disk()
        return jsonify({"message": "Thread deleted"})
    return jsonify({"error": "Thread not found"}), 404

@app.route('/upload', methods=['POST'])
def upload():
    global current_thread_id, threads_data
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        file.seek(0, os.SEEK_END)
        size_bytes = file.tell()
        file.seek(0)
        readable_size = get_human_readable_size(size_bytes)
        
        pdf_text = extract_text_from_pdf(io.BytesIO(file.read()))
        if not pdf_text.strip():
            return jsonify({"error": "Could not extract text from PDF"}), 400
        
        if not current_thread_id:
            current_thread_id = str(uuid.uuid4())
            threads_data[current_thread_id] = {"title": file.filename, "history": [], "pdf_context": "", "pdf_filename": "", "pdf_filesize": ""}
            
        threads_data[current_thread_id]["pdf_context"] = pdf_text
        threads_data[current_thread_id]["pdf_filename"] = file.filename
        threads_data[current_thread_id]["pdf_filesize"] = readable_size
        save_threads_to_disk()
        
        return jsonify({
            "message": "PDF context loaded into current thread.",
            "thread_id": current_thread_id,
            "filename": file.filename,
            "filesize": readable_size
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/clear_context', methods=['POST'])
def clear_context():
    global current_thread_id
    current_thread_id = None
    return jsonify({"message": "Starting a new fresh thread pointer."})


@app.route('/chat', methods=['POST'])
def chat():
    global current_thread_id, threads_data
    try:
        data = request.json
        user_message = data.get('message', '')
        web_search = data.get('web_search', False)
        bizmind = data.get('bizmind', False)
        
        # Auto-trigger web search for the last 4 BizMind modules when starting them
        if bizmind and "Let's start the " in user_message and "module." in user_message:
            if "Business Idea Validator" not in user_message:
                web_search = True
        
        if not user_message:
            return jsonify({"error": "No message"}), 400
        
        # Ensure we have a thread
        is_new_thread = False
        if not current_thread_id:
            current_thread_id = str(uuid.uuid4())
            title = (user_message[:30] + '...') if len(user_message) > 30 else user_message
            threads_data[current_thread_id] = {
                "title": title, 
                "history": [], 
                "pdf_context": "", 
                "pdf_filename": "", 
                "pdf_filesize": "",
                "is_bizmind": bizmind # Store the mode
            }

        thread = threads_data[current_thread_id]
        sources = []
        
        # ── PROMPT CONSTRUCTION ──
        prompt_parts = []
        
        if bizmind:
            prompt_parts.append("""Your job is to act as BizMind, an expert startup mentor helping users build a business in India.
You must guide the user strictly step-by-step through a 5-module roadmap. Do not skip modules.

--- THE 5 MODULES ---
1. Business Idea Validator (TAM estimate, competitor landscape, UVP suggestions, GTM direction, risk factors, viability score)
2. Market Research & Competitor Analysis (Pricing tiers, market trends, gap analysis, customer sentiment)
3. Marketing Strategy Generator (Channel recommendations, content strategy, growth hacks, 30-60-90 day roadmap)
4. Financial Planning & Projections (Startup cost breakdown, burn rate, revenue scenarios, break-even point)
5. Legal & Compliance Checklist (Registration requirements, licenses, tax obligations, IP basics, employment law)

--- SEQUENTIAL RULES ---
- The user may start a specific module or ask to start from the beginning.
- When generating a module report, produce a highly structured, bolded, easy-to-read report based strictly on the required outputs in the parentheses above.
- NEVER move to the next module until the user explicitly confirms they are ready. Wait for them to digest the current step. 
- Ask guiding questions if you need more information before finalizing a module report.
- The workflow takes about 5-6 steps total. 

--- RESPONSE RULES ---
1. Keep conversation crisp. If not generating a full module report, keep answers to 5 lines maximum.
2. If generating a Module report, structure it beautifully with Markdown headings.
3. End EVERY response with exactly 3 options like this:
What would you like to do next?
[ 🔍 Option 1 ] [ 💡 Option 2 ] [ 🔄 Option 3 ]

--- RULES ---
- Simple English only, no jargon.
- India-specific advice always.
- Actively use any contextual data from uploaded PDF files.
""")
        elif not thread["pdf_context"]:
            prompt_parts.append("You are a helpful AI assistant.")
            
        if thread["pdf_context"]:
            prompt_parts.append(f"DOCUMENT CONTEXT:\n{thread['pdf_context']}\n\nUse this context.")
        
        if thread["history"]:
            hist_str = "\n".join([f"{r.upper()}: {m}" for r, m in thread["history"][-10:]])
            prompt_parts.append(f"HISTORY:\n{hist_str}")

        # ── WEB SEARCH MODE ──
        if web_search and not thread["pdf_context"]:
            logger.info(f"🌐 Web search for: {user_message}")
            sources = search_duckduckgo(user_message, max_results=3)
            
            if sources:
                urls_to_scrape = [s["url"] for s in sources]
                logger.info(f"📄 Scraping {len(urls_to_scrape)} URLs...")
                scraped = scrape_urls(urls_to_scrape)
                
                web_content = "\n\nWEB SEARCH RESULTS:\n"
                for i, source in enumerate(sources):
                    web_content += f"\n--- SOURCE [{i+1}] ---\nTitle: {source['title']}\nURL: {source['url']}\nSnippet: {source['snippet']}\n"
                    matching_scrape = next((s for s in scraped if s["url"] == source["url"]), None)
                    if matching_scrape and matching_scrape["content"]:
                        web_content += f"Full Content:\n{matching_scrape['content']}\n"
                
                prompt_parts.append(web_content)
        
        prompt_parts.append(f"USER: {user_message}")
        full_prompt = "\n\n---\n\n".join(prompt_parts)

        # ── GEMINI CALL ──
        max_retries = 3
        retry_delay = 3
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash"]
        
        for model_name in models_to_try:
            for attempt in range(max_retries):
                try:
                    logger.info(f"Trying model: {model_name} (attempt {attempt + 1}/{max_retries})")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=full_prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.7,
                        )
                    )
                    
                    if not response or not response.text:
                        return jsonify({"response": "Empty response from Gemini. Try again."})
                    
                    # Update memory
                    thread["history"].append(("user", user_message))
                    thread["history"].append(("model", response.text))
                    save_threads_to_disk()
                    
                    # Return response with sources if web search was used
                    result = {
                        "response": response.text, 
                        "thread_id": current_thread_id
                    }
                    if sources:
                        result["sources"] = sources
                    
                    return jsonify(result)

                except Exception as api_err:
                    error_str = str(api_err).lower()
                    
                    # 503 / UNAVAILABLE — retry then fallback to next model
                    if "503" in error_str or "unavailable" in error_str:
                        logger.warning(f"Model {model_name} unavailable (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        else:
                            logger.warning(f"All retries exhausted for {model_name}, trying next model...")
                            break  # break inner loop, try next model
                    
                    # 429 / Rate limit — retry with delay
                    if "429" in error_str or "resource_exhausted" in error_str:
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay + 2)
                            continue
                        return jsonify({
                            "error": "You've hit the API rate limit. Please wait 15 seconds.", 
                            "thread_id": current_thread_id 
                        }), 429
                    
                    if "404" in error_str:
                        logger.warning(f"Model {model_name} not found, trying next model...")
                        break  # try next model
                    
                    logger.error(f"Gemini API Error: {api_err}")
                    return jsonify({"error": f"Gemini Error: {str(api_err)}", "thread_id": current_thread_id}), 500
        
        # If all models failed
        return jsonify({
            "error": "All models are currently unavailable. Please try again in a minute.",
            "thread_id": current_thread_id
        }), 503
                
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"error": "Server error"}), 500

@app.route('/')
def serve_index():
    return send_file('index.html')

if __name__ == '__main__':
    app.run(port=5000, debug=True)
