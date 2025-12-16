Note: use this two command in terminal to run the project
. .\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --host 0.0.0.0 --port 8001 --app-dir .



# Lyftr AI Universal Website Scraper

This is the MVP solution for the Full-stack Assignment, built using **FastAPI** (Python) for the backend and **React/Vite** (with Chakra UI) for the frontend.

## ⚙️ Setup and Running Instructions

The project is designed to be run using a single shell script: `run.sh`.

1.  **Prerequisites:** Ensure you have Python 3.10+, Node.js, and npm/yarn/pnpm installed.
2.  **Make executable:**
    ```bash
    chmod +x run.sh
    ```
3.  **Run the project:**
    ```bash
    ./run.sh
    ```
    This script will:
    * Create and activate a Python virtual environment (`.venv`).
    * Install Python dependencies (`fastapi`, `playwright`, etc.).
    * Install necessary Playwright browsers (`playwright install`).
    * Install Node dependencies and build the React frontend (`npm install && npm run build` in the `frontend` folder).
    * Start the FastAPI server using `uvicorn` on `http://localhost:8000`.

## 🧪 Testing URLs

These URLs were used for primary testing and cover all major requirements:

-   **Static Page:** `https://en.wikipedia.org/wiki/Artificial_intelligence`
    * **Note:** Tests static fetching, meta-data extraction, and semantic section grouping.
-   **JS-Heavy Page with Tabs:** `https://mui.com/material-ui/react-tabs/`
    * **Note:** Tests JS rendering fallback and the tab-clicking interaction flow.
-   **Pagination/Infinite Scroll:** `https://news.ycombinator.com/` (for pagination) or `https://dev.to/t/javascript` (for scroll)
    * **Note:** Tests navigation depth $\ge 3$ via pagination links.

## 🛑 Known Limitations

* **Anti-Bot Detection:** Highly aggressive sites (e.g., those using Cloudflare or Akamai bot protection) may block the Playwright session. The scraper will return a generic error in `errors[]` in this case.
* **Table Parsing:** Table content is currently returned as raw HTML strings (`content.tables: array of strings`) rather than structured JSON.
* **Link Clicks:** The interaction logic is non-recursive. It only performs initial clicks/scrolls and does not follow links to different origins.
