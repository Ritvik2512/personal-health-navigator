# 🩺 Personal Health Navigator

An AI-powered health assistant that looks up real drug and medical data, handles long conversations efficiently, and knows when to say "see a doctor."

**Stack:** FastAPI · Claude (Anthropic) · OpenFDA API · MedlinePlus · Vanilla JS

---

## Features

- 💊 **Real drug data** — looks up FDA-approved drug info (side effects, interactions, warnings)
- 🔍 **Symptom guidance** — searches MedlinePlus for reliable condition information
- 🚨 **Emergency detection** — flags life-threatening symptoms and shows a prominent alert
- 🧠 **Long conversation memory** — summarizes older context to stay within token limits
- 🛠️ **Agentic tool use** — Claude decides when to call tools based on the conversation

---

## Setup

### 1. Get an Anthropic API Key

Go to [console.anthropic.com](https://console.anthropic.com) and add credits. $5 is enough to build and demo this project.

### 2. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/health-navigator.git
cd health-navigator

cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Set environment variables

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 4. Run locally

```bash
cd backend
uvicorn main:app --reload
```

Open `http://localhost:8000` — the frontend is served from FastAPI.

---

## Project Structure

```
health-navigator/
├── backend/
│   ├── main.py          # FastAPI routes + static file serving
│   ├── agent.py         # Claude agent loop with tool use
│   ├── memory.py        # Sliding window + summarization
│   ├── tools.py         # Tool definitions for Claude
│   ├── medical_apis.py  # OpenFDA + MedlinePlus wrappers
│   ├── prompts.py       # System prompt + safety rules
│   ├── models.py        # Pydantic schemas
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Chat UI
│   └── app.js           # Frontend logic
├── railway.toml         # Deployment config
└── .env.example
```

---

## Milestones

- [x] M1 — Basic chat UI working with Claude
- [x] M2 — Tool use: OpenFDA + NIH APIs connected
- [x] M3 — Context management: summarisation + retrieval
- [x] M4 — Skills pattern: modular prompts for safety/triage
- [x] M5 — Deployed with GitHub repo + README

---

## Deployment (Railway)

1. Push to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add environment variable: `ANTHROPIC_API_KEY`
4. Railway auto-detects `railway.toml` and deploys

---

## Disclaimer

This tool is for **informational purposes only**. It is not a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider for medical concerns.

In an emergency, call **112** (India) or go to your nearest emergency room.
