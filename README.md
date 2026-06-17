# 🩺 Personal Health Navigator

An AI-powered health assistant that looks up real drug and medical data, remembers you across sessions, and knows when to say "see a doctor."

**Stack:** FastAPI · Claude (Anthropic) · OpenFDA · MedlinePlus · SQLite · Vanilla JS

---

## Features

- 💊 **Real drug data** — looks up FDA-approved drug info (side effects, warnings, interactions)
- 🔍 **Symptom guidance** — searches MedlinePlus for reliable condition information
- 🚨 **Emergency detection** — flags life-threatening symptoms with location-aware emergency numbers
- 🧠 **Persistent memory** — remembers your allergies, medications, and conditions across sessions
- 💾 **Session history** — full conversation history saved to SQLite, survives browser restarts
- 🔌 **Provider abstraction** — swap Claude for Gemini or GPT by changing one line

---

## Setup

### 1. Get an Anthropic API Key

Go to [console.anthropic.com](https://console.anthropic.com) and add credits.

### 2. Clone & install

```bash
git clone https://github.com/Ritvik2512/personal-health-navigator.git
cd personal-health-navigator

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

Open `http://localhost:8000`

---

## Project Structure
personal-health-navigator/
├── backend/
│   ├── main.py            # FastAPI routes + static file serving
│   ├── agent.py           # Core agent loop (model-agnostic)
│   ├── llm_provider.py    # Provider abstraction — swap models here
│   ├── memory.py          # Two-layer memory: patient context + sliding window
│   ├── tools.py           # Tool definitions in neutral format
│   ├── medical_apis.py    # OpenFDA + MedlinePlus wrappers
│   ├── prompts.py         # System prompt + safety rules
│   ├── models.py          # Pydantic schemas
│   ├── database.py        # SQLite session + history persistence
│   └── requirements.txt
├── frontend/
│   ├── index.html         # Chat UI
│   └── app.js             # Frontend logic
├── railway.toml           # Deployment config
└── .env.example
---

## Memory Architecture

Two-layer system:

**Layer 1 — Patient context:** allergies, medications, conditions, age. Extracted automatically from conversation and injected into every prompt. Never summarized away.

**Layer 2 — Sliding window:** conversation history with summarization when it gets long. Keeps context efficient without losing flow.

---

## Switching AI Models

All SDK-specific code is in `llm_provider.py`. To switch:

```python
def get_provider():
    return ClaudeProvider()   # currently using Claude
    # return GeminiProvider() # swap to Gemini — free tier
```

`tools.py`, `memory.py`, and `agent.py` require zero changes.

---

## Milestones

- [x] M1 — Basic chat UI working with Claude
- [x] M2 — Tool use: OpenFDA + NIH APIs connected
- [x] M3 — Context management: summarisation + sliding window
- [x] M4 — Skills pattern: modular prompts for safety/triage
- [x] M5 — Deployed with GitHub repo + README

---

## Deployment (Railway)

1. Push to GitHub
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Add environment variable: `ANTHROPIC_API_KEY`
4. Railway auto-detects `railway.toml` and deploys

---

## ⚠️ Disclaimer

This tool is for **informational purposes only**. It is not a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider.

In an emergency, call **112** (India) or **911** (US) or go to your nearest emergency room.