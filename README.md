# Perplexity Clone — AI Search Engine & Startup Mentor

An intelligent, full-stack AI search engine and conversational assistant powered by Flask and Google Gemini AI. It combines real-time DuckDuckGo web searching and scraping, PDF document context extraction, multi-thread conversation history, and **BizMind** — a specialized, 5-stage startup mentorship roadmap designed specifically for entrepreneurs in India.

---

## 🌟 Features

- ⚡ **Next-Gen AI Intelligence**: Powered by Google Gemini 2.5 Flash and Gemini 2.0 Flash models via the modern Google GenAI SDK.
- 🌐 **Real-Time Web Search & Scraping**: Performs live DuckDuckGo queries and automatically scrapes top sources using BeautifulSoup to provide grounded answers with inline citations `[1]`, `[2]`, `[3]`.
- 📄 **Chat with PDFs**: Upload PDF documents (pitch decks, research papers, financial reports) and chat directly with your files using PyPDF2 text extraction.
- 🧵 **Multi-Thread Conversation Management**: Organize and revisit previous chats anytime. Conversations and document contexts are persistently saved in local storage (`threads.json`).
- 🇮🇳 **BizMind — Startup Mentor for India**: An interactive 5-module structured mentorship engine that guides founders step-by-step through:
  1. **Business Idea Validator** (TAM estimation, competitor landscape, UVP, viability score)
  2. **Market Research & Competitor Analysis** (Pricing tiers, market trends, Indian customer sentiment)
  3. **Marketing Strategy Generator** (Distribution channels, 30-60-90 day growth roadmap)
  4. **Financial Planning & Projections** (Startup costs in INR, burn rate, break-even analysis)
  5. **Legal & Compliance Checklist** (MCA registration, GST, DPIIT recognition, Indian tax laws)
- 🔒 **Zero Hardcoded Secrets**: Built following security best practices with environment variable configuration (`GEMINI_API_KEY`) and `.env` support.
- 🎨 **Clean, Responsive UI**: Modern dark/light themed interface built with HTML5, CSS3, and Vanilla JavaScript.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Python 3.10+, [Flask](https://flask.palletsprojects.com/), Flask-CORS |
| **AI & LLM** | Google Gemini API ([google-genai](https://github.com/googleapis/python-genai) SDK) |
| **Search & Web Scraping** | [duckduckgo-search](https://github.com/deedy5/duckduckgo_search), Requests, BeautifulSoup4 |
| **Document Processing** | [PyPDF2](https://pypi.org/project/PyPDF2/) |
| **Concurrency** | Python `ThreadPoolExecutor` for parallel scraping |
| **Data Persistence** | JSON file-based storage (`threads.json`) |
| **Frontend** | HTML5, CSS3, JavaScript (Fetch API, responsive layout) |

---

## 📋 Prerequisites

Before getting started, make sure you have:
1. **Python 3.10** or higher installed on your computer.
2. A **Google Gemini API Key** (Free tier available at [Google AI Studio](https://aistudio.google.com/app/apikey)).
3. **Git** installed on your system.

---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/NiharikaDesu0028/Let-s_clone_Perplexity.git
cd Let-s_clone_Perplexity
```

### 2. Create and Activate a Virtual Environment

- **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```

- **On Windows (Command Prompt):**
  ```cmd
  python -m venv venv
  .\venv\Scripts\activate.bat
  ```

- **On macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install Required Dependencies
```bash
pip install -r requirements.txt
```

---

## 🔑 Setting the `GEMINI_API_KEY`

You must provide a valid Gemini API key for the application to function. Choose whichever method suits your workflow best:

### Option A: Using a `.env` file (Recommended)
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   *(On Windows Command Prompt, run: `copy .env.example .env`)*
2. Open `.env` in any text editor and paste your key:
   ```env
   GEMINI_API_KEY=AIzaSyYourActualKeyHere...
   ```
> `.env` is already listed in `.gitignore` so your secret key will never be committed to GitHub.

### Option B: Using Environment Variables in Terminal

- **Windows (PowerShell):**
  ```powershell
  $env:GEMINI_API_KEY="AIzaSyYourActualKeyHere..."
  ```

- **Windows (Command Prompt):**
  ```cmd
  set GEMINI_API_KEY=AIzaSyYourActualKeyHere...
  ```

- **macOS / Linux (Bash/Zsh):**
  ```bash
  export GEMINI_API_KEY="AIzaSyYourActualKeyHere..."
  ```

---

## 💻 Running the Application

1. Start the Flask server:
   ```bash
   python app.py
   ```
2. Open your web browser and navigate to:
   ```
   http://localhost:5000
   ```
   *(or `http://127.0.0.1:5000`)*

---

## 📖 Usage Examples

### 1. Web-Connected AI Search
- Type any query into the search bar (e.g., *"Latest developments in quantum computing"* or *"Top EV battery manufacturers in India 2026"*).
- Enable **Web Search** mode to instruct the engine to scrape live sources and summarize findings with linked citations.

### 2. Chat with PDF Documents
1. Click the **Upload PDF** button on the interface.
2. Select a PDF document (e.g., pitch deck, balance sheet, or academic paper).
3. Ask questions such as:
   - *"Summarize key revenue projections from page 3"*
   - *"What are the primary risk factors mentioned in this document?"*

### 3. BizMind Startup Mentorship (India Edition)
1. Switch to the **BizMind** module in the sidebar.
2. Start by entering your business idea (e.g., *"Quick-commerce organic dairy delivery in Tier 2 Indian cities"*).
3. BizMind will guide you sequentially through the 5 modules:
   - **Module 1**: Computes Total Addressable Market (TAM) in ₹ Crores, analyzes Indian competitors (e.g., Country Delight, Zepto), and outputs a viability score.
   - **Module 2**: Researches consumer spending trends and pricing expectations in targeted regions.
   - **Module 3**: Generates a hyper-local customer acquisition plan (WhatsApp marketing, society activation).
   - **Module 4**: Builds estimated OPEX/CAPEX projections, working capital needs, and break-even timelines.
   - **Module 5**: Outlines registration mandates (FSSAI, Private Limited vs. LLP, GST thresholds, and DPIIT Startup India tax exemptions).

---

## 📁 Project Structure

```
Let-s_clone_Perplexity/
├── app.py              # Flask server, API endpoints, web scraper & Gemini integration
├── index.html          # Main web application interface
├── style.css           # Styling, themes, responsive layout
├── .env.example        # Template for environment variables
├── .gitignore          # Excludes secrets, cache, and virtual environments
├── requirements.txt    # Project Python dependencies
├── threads.json        # Local storage for conversation threads (auto-created)
└── README.md           # Project documentation
```

---

## 🛡️ Security Best Practices

- **Never hardcode secrets** in Python or frontend files.
- Always keep your `.env` file untracked.
- If an API key is accidentally exposed, immediately revoke it in [Google AI Studio](https://aistudio.google.com/) and issue a new one.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 License

This project is open-source and available under the [MIT License](LICENSE).
