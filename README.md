# 🛒 ShopAgent AI — Autonomous E-Commerce Shopping Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-black.svg)](https://langchain-ai.github.io/langgraph/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg?logo=react&logoColor=black)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.0+-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?logo=docker&logoColor=white)](https://hub.docker.com/)
[![CI/CD](https://img.shields.io/badge/GitHub_Actions-Automated_Build-2088FF.svg?logo=githubactions&logoColor=white)](.github/workflows/docker-publish.yml)

An agentic shopping assistant powered by **LangGraph**, **FastAPI**, and a **Vite + React (TypeScript)** frontend. It searches across multiple marketplaces (**Walmart**, **eBay**, **Amazon**, and **Google Shopping**) via SerpAPI, manages a deterministic shopping cart, answers product inquiries, and provides **Human-in-the-Loop checkout confirmation** with strict ChatGPT-style conversation thread isolation.

---

## 📑 Table of Contents

- [Key Features](#-key-features)
- [Architecture & Workflow](#-architecture--workflow)
- [Prerequisites](#-prerequisites)
- [Repository Installation & Setup](#-repository-installation--setup)
  - [1. Clone Repository](#1-clone-repository)
  - [2. Environment Configuration](#2-environment-configuration)
  - [3. Backend Setup](#3-backend-setup)
  - [4. Frontend Setup](#4-frontend-setup)
- [Running the Application](#-running-the-application)
  - [Start Backend API](#start-backend-api)
  - [Start Frontend UI](#start-frontend-ui)
  - [(Optional) Terminal Chat CLI](#optional-terminal-chat-cli)
- [Running with Docker & Docker Compose](#-running-with-docker--docker-compose)
- [How to Use the Assistant](#-how-to-use-the-assistant)
- [API Reference](#-api-reference)
- [Running Tests](#-running-tests)
- [Project Directory Structure](#-project-directory-structure)

---

## 🌟 Key Features

1. **Multi-Marketplace Search Subgraph:**
   - Structured query extraction from user prompt (`keywords`, `max_price`, `brand`, `marketplaces`).
   - Parallel fetching across Walmart, eBay, Amazon, and Google Shopping via SerpAPI.
   - Normalization, deduplication, ranking, and TTL caching in SQLite to prevent redundant API calls.

2. **ChatGPT-Style Thread Isolation:**
   - Conversations are isolated by `thread_id` with checkpoint persistence in SQLite.
   - Sidebar thread history: browse previous sessions, create new chats, and delete conversations.

3. **Deterministic Cart Operations:**
   - Cart actions (`add`, `remove`, `update_qty`, `view`) use typed parameters rather than raw LLM SQL execution to prevent errors and unauthorized mutations.

4. **Human-in-the-Loop Checkout Interrupt:**
   - Utilizes LangGraph's native `interrupt()` breakpoint.
   - When the agent prepares an order, execution pauses and renders an interactive confirmation card on the frontend:
     - **`[✓ Approve Order]`** -> Triggers `/api/chat/resume` (`approved: true`), persists the Order & OrderItems, and clears cart.
     - **`[✕ Cancel]`** -> Triggers `/api/chat/resume` (`approved: false`), cancels purchase and retains cart items.

5. **Modern, Responsive Frontend:**
   - Built with Vite, React 18, and TypeScript.
   - Glassmorphism dark mode, live cart drawer, interactive product cards with direct store links, star ratings, and markdown rendering.

---

## 📐 Architecture & Workflow

```
                        ┌─────────────┐
          START ──────► │ load_context│  (loads cart, user profile, last viewed items)
                        └──────┬──────┘
                               ▼
                        ┌─────────────┐
                        │   router    │  (structured Pydantic intent classification)
                        └──┬──┬──┬──┬─┘
               ┌───────────┘  │  │  └────────────┐
               ▼              ▼  ▼               ▼
         ┌──────────┐  ┌─────────┐ ┌──────────┐ ┌──────────┐
         │ search   │  │ product │ │  cart    │ │ chitchat │
         │ subgraph │  │  QA     │ │ subgraph │ │ / fallback│
         └────┬─────┘  └────┬────┘ └────┬─────┘ └────┬─────┘
              │             │           │            │
              │             │      ┌────▼─────┐      │
              │             │      │ checkout │      │
              │             │      │(interrupt)│     │
              │             │      └────┬─────┘      │
              └─────────────┴───────────┴────────────┘
                               ▼
                        ┌─────────────┐
                        │  respond    │  (formats final answer & updates state)
                        └──────┬──────┘
                               ▼
                              END
```

---

## 📋 Prerequisites

Make sure the following tools are installed on your machine:

- **Python**: Version `3.10` or higher
- **Node.js**: Version `18.0` or higher (includes `npm`)
- **API Keys**:
  - `OPENAI_API_KEY`: Required for LLM routing, query rewriting, and conversational responses.
  - `SERPAPI_API_KEY`: (Recommended) For real-time Walmart, eBay, Amazon & Google Shopping live product search. *(If not provided, the search subgraph uses safe fallback handling)*.

---

## 🚀 Repository Installation & Setup

### 1. Clone Repository

```bash
git clone https://github.com/malinphy/e_repo.git
cd e_repo
```

### 2. Environment Configuration

Copy the example environment template and add your credentials:

```bash
# On Linux / macOS / Git Bash:
cp .env.example .env

# On Windows PowerShell:
Copy-Item .env.example .env
```

Open `.env` in your text editor and fill in your keys:
```env
OPENAI_API_KEY="sk-..."
SERPAPI_API_KEY="c448..."
LANGSMITH_TRACING=false
```

---

### 3. Backend Setup

1. **Create and activate a Python virtual environment:**

   - **Linux / macOS:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

   - **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

2. **Install Python dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Initialize the SQLite database:**
   ```bash
   python -m backend.app.init_db
   ```
   *(This creates `ecommerce.db` with users, chats, cart items, order tables, and indexes in `backend/data/`)*.

---

### 4. Frontend Setup

1. **Navigate to the frontend folder:**
   ```bash
   cd frontend
   ```

2. **Install Node packages:**
   ```bash
   npm install
   ```

3. **Verify `.env` configuration:**
   The `frontend/.env` file points to the backend API:
   ```env
   VITE_API_BASE_URL=http://127.0.0.1:8000
   ```

---

## 🏃 Running the Application

### Start Backend API

Run the ASGI server from the root directory:

```bash
# From repository root (with virtual environment activated):
python -m backend.main
```

The API will start at:
- **API Base:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

### Start Frontend UI

In a new terminal window, start the Vite development server:

```bash
cd frontend
npm run dev
```

Open your browser and navigate to:
👉 **[http://localhost:5173](http://localhost:5173)**

---

### (Optional) Terminal Chat CLI

You can also test the LangGraph workflow directly from your terminal without opening the browser:

```bash
python -m backend.chat_cli
```

---

## 🐳 Running with Docker & Docker Compose

The application is packaged into a **Unified Single Container** that bundles both the compiled React frontend and the FastAPI backend into an optimized multi-stage build.

### 1. Run Prebuilt Image from Docker Hub

Provide your API keys via a local `.env` file and mount a local folder for SQLite database persistence:

```bash
docker run -d \
  --name shopagent-app \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/backend/data \
  <YOUR_DOCKERHUB_USERNAME>/shopagent:latest
```

Open your browser at **[http://localhost:8000](http://localhost:8000)**!

> 🔒 **Security & Privacy:** The published Docker image contains zero hardcoded keys or credentials. Your `.env` variables (`OPENAI_API_KEY`, `SERPAPI_API_KEY`) and your SQLite cart/chat data remain entirely on your local host.

---

### 2. Run with Docker Compose

Ensure your `.env` file exists in the project root, then execute:

```bash
docker compose up -d
```

To view logs:
```bash
docker compose logs -f
```

To stop:
```bash
docker compose down
```

---

### 3. Build Image Locally

```bash
docker build -t shopagent:latest .
docker run -d -p 8000:8000 --env-file .env -v $(pwd)/data:/app/backend/data shopagent:latest
```

---

## 💡 How to Use the Assistant

Here is a recommended user journey demonstrating all capabilities:

1. **Product Search across Marketplaces:**
   - *User:* `"Find wireless noise-cancelling headphones under $100"`
   - *Agent:* Scans Walmart and eBay, extracts matching products, displays structured product cards with rating, price, and marketplace badges.

2. **Contextual Referencing & Product QA:**
   - *User:* `"Does the 2nd one support multipoint Bluetooth?"`
   - *Agent:* Inspects the details of item #2 from `last_results` state without executing a redundant web search.

3. **Adding to Cart:**
   - *User:* `"Add the second one to my cart"` *(or click the **[Ekle]** button on the product card)*
   - *Agent:* Updates the SQLite shopping cart snapshot and reflects the new count in the top-right cart badge.

4. **Inspecting Cart:**
   - Click the **"Sepetim"** button in the header or ask:
   - *User:* `"What is currently in my cart?"`
   - *Agent:* Shows line items, quantities, and subtotal.

5. **Human-in-the-Loop Checkout Approval:**
   - *User:* `"I want to checkout"`
   - *Agent:* Enters checkout subgraph, triggers `interrupt()`, and displays the approval banner:
     - Click **[Siparişi Onayla]** -> Order is confirmed and saved to SQLite `orders` table.
     - Click **[İptal Et]** -> Purchase is cancelled safely.

---

## 🔌 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/chat` | Send message to LangGraph agent with session memory |
| `POST` | `/api/chat/resume` | Resume human-in-the-loop checkout interrupt (`approved: true/false`) |
| `GET` | `/api/chat/threads` | List all conversation threads for a user |
| `POST` | `/api/chat/threads` | Create a new isolated chat thread |
| `GET` | `/api/chat/threads/{id}/messages`| Get chronological message history for a thread |
| `DELETE`| `/api/chat/threads/{id}` | Delete a thread and all associated messages |
| `GET` | `/api/cart` | Retrieve current user's active shopping cart |
| `POST` | `/api/cart/remove` | Remove an item from cart by reference or ID |
| `GET` | `/api/search` | Retrieve latest search results for a thread |
| `GET` | `/health` | Health check probe |

---

## 🧪 Running Tests

### Backend Test Suite
The backend includes unit and integration tests covering the LangGraph workflow, routers, SerpAPI adapters, checkout interrupt, and database integrity:

```bash
# Run all tests:
pytest

# Run tests with detailed console output:
pytest -v

# Run a specific test module:
pytest backend/tests/test_checkout.py
```

### Frontend Type Check & Build
Validate TypeScript types and build the production bundle:

```bash
cd frontend
npm run build
```

---

## 📁 Project Directory Structure

```text
e_repo/
├── backend/
│   ├── app/
│   │   ├── agent/                 # LangGraph workflows and nodes
│   │   │   ├── nodes/             # Router, load_context, chitchat
│   │   │   ├── subgraphs/         # Search, Cart, QA, Checkout subgraphs
│   │   │   ├── graph.py           # Main compiled StateGraph
│   │   │   └── state.py           # Shared ShopState definition
│   │   ├── api/                   # FastAPI REST routes (chat, cart, search)
│   │   ├── core/                  # Database, Settings, Config
│   │   ├── models/                # SQLAlchemy database entities (User, Cart, Order, Chat)
│   │   ├── schemas/               # Pydantic validation schemas
│   │   ├── services/              # Cache service & business helpers
│   │   └── tools/                 # SerpAPI marketplace adapters (Walmart, eBay, Amazon)
│   ├── data/                      # Local SQLite database files
│   ├── tests/                     # Pytest suite
│   ├── chat_cli.py                # Standalone CLI chat tool
│   └── main.py                    # ASGI application runner
├── frontend/
│   ├── src/
│   │   ├── components/            # UI components (Sidebar, CartDrawer, Cards, ChatArea)
│   │   ├── services/              # API HTTP client (Fetch wrapper)
│   │   ├── types/                 # TypeScript interfaces and models
│   │   ├── App.css                # Component styles & dark-mode layout
│   │   ├── App.tsx                # Main application state and coordinator
│   │   └── index.css              # Design tokens and global CSS variables
│   ├── index.html                 # Web entry HTML
│   ├── package.json               # Node dependencies and scripts
│   └── vite.config.ts             # Vite build configuration
├── .env.example                   # Environment variable template
├── pytest.ini                     # Pytest configuration
├── requirements.txt               # Python package dependencies
└── README.md                      # Project documentation (this file)
```

---

## 📄 License

This project is licensed under the MIT License.
