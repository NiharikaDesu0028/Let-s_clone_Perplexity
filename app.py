from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
import logging
import traceback
import PyPDF2
import io
import time
import json
import os
import uuid

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
API_KEY = "AIzaSyAhXf5A4pqav__eQt6eknUsmEpgltNF-rY"
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

@app.route('/threads', methods=['GET'])
def get_threads():
    # Return list of thread metadata for the sidebar
    summary = []
    for tid, data in threads_data.items():
        summary.append({
            "id": tid,
            "title": data.get("title", "Untitled Thread"),
            "has_pdf": bool(data.get("pdf_context")),
            "pdf_filename": data.get("pdf_filename", ""),
            "pdf_filesize": data.get("pdf_filesize", "")
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
        
        # Calculate human-readable size
        file.seek(0, os.SEEK_END)
        size_bytes = file.tell()
        file.seek(0) # Reset to beginning
        readable_size = get_human_readable_size(size_bytes)
        
        pdf_text = extract_text_from_pdf(io.BytesIO(file.read()))
        if not pdf_text.strip():
            return jsonify({"error": "Could not extract text from PDF"}), 400
        
        # If no active thread, create one
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
    # On "New Thread", we just clear the active pointer
    current_thread_id = None
    return jsonify({"message": "Starting a new fresh thread pointer."})

@app.route('/chat', methods=['POST'])
def chat():
    global current_thread_id, threads_data
    try:
        data = request.json
        user_message = data.get('message', '')
        if not user_message:
            return jsonify({"error": "No message"}), 400
        
        # Ensure we have a thread
        is_new_thread = False
        if not current_thread_id:
            current_thread_id = str(uuid.uuid4())
            is_new_thread = True
            # Use first message as title (truncated)
            title = (user_message[:30] + '...') if len(user_message) > 30 else user_message
            threads_data[current_thread_id] = {"title": title, "history": [], "pdf_context": "", "pdf_filename": "", "pdf_filesize": ""}

        thread = threads_data[current_thread_id]
        
        # Build Prompt
        prompt_parts = []
        if thread["pdf_context"]:
            prompt_parts.append(f"DOCUMENT CONTEXT:\n{thread['pdf_context']}\n\nUse this context.")
        else:
            prompt_parts.append("You are a helpful AI assistant.")
        
        if thread["history"]:
            hist_str = "\n".join([f"{r.upper()}: {m}" for r, m in thread["history"][-10:]])
            prompt_parts.append(f"HISTORY:\n{hist_str}")
            
        prompt_parts.append(f"USER: {user_message}")
        full_prompt = "\n\n---\n\n".join(prompt_parts)

        # Gemini Call with improved 429 and 404 Handling
        max_retries = 3
        retry_delay = 5 
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
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
                
                return jsonify({"response": response.text, "thread_id": current_thread_id})

            except Exception as api_err:
                error_str = str(api_err).lower()
                
                # Rate Limit
                if "429" in error_str or "resource_exhausted" in error_str:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return jsonify({
                        "error": "You've hit the API rate limit. Please wait 15 seconds.", 
                        "thread_id": current_thread_id 
                    }), 429
                
                # Model Not Found (404) fallback or message
                if "404" in error_str:
                    return jsonify({
                        "error": "Model not found or not available for this API key. Please check your project settings.",
                        "thread_id": current_thread_id
                    }), 404
                
                logger.error(f"Gemini API Error: {api_err}")
                return jsonify({"error": f"Gemini Error: {str(api_err)}", "thread_id": current_thread_id}), 500
                
    except Exception as e:
        logger.error(traceback.format_exc())
        return jsonify({"error": "Server error"}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
