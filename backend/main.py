import os
import time
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from models import ChatRequest, ChatResponse
from agent import run_agent
from database import init_db, load_session, save_session, log_usage, get_daily_usage, get_daily_cost

init_db()

app = FastAPI(title="Personal Health Navigator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate limiting ---
# stores {session_id: [timestamp, timestamp, ...]}
rate_limit_store = defaultdict(list)
RATE_LIMIT = 3       # max requests
RATE_WINDOW = 120      # per 60 seconds
DAILY_BUDGET = 5.0    # USD


def check_rate_limit(session_id: str):
    now = time.time()
    timestamps = rate_limit_store[session_id]
    # remove timestamps older than the window
    rate_limit_store[session_id] = [t for t in timestamps if now - t < RATE_WINDOW]
    if len(rate_limit_store[session_id]) >= RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Whoa, slow down! You've sent too many messages. Please wait 60 seconds before trying again."
        )
    rate_limit_store[session_id].append(now)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    return load_session(session_id)


@app.get("/admin/usage")
async def admin_usage():
    return get_daily_usage()


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # 1. rate limit
    check_rate_limit(request.session_id)

    # 2. daily budget check
    if get_daily_cost() >= DAILY_BUDGET:
        raise HTTPException(
            status_code=503,
            detail="Daily usage limit reached. The service will resume tomorrow."
        )

    try:
        persisted = load_session(request.session_id)
        patient_context = persisted["patient_context"]
        history = persisted["history"]
        prev_count = len(history)

        reply, updated_history, patient_context, emergency, emergency_reason, tool_calls, usage = await run_agent(
            user_message=request.message,
            raw_history=history,
            patient_context=patient_context,
        )

        new_messages = updated_history[prev_count:]
        save_session(request.session_id, patient_context, new_messages)

        # 3. log token usage
        if usage:
            log_usage(request.session_id, usage.get("input_tokens", 0), usage.get("output_tokens", 0))
            print("logged usage:", usage)
        else:
            print("no usage data captured")

        return ChatResponse(
            reply=reply,
            updated_history=updated_history,
            patient_context=patient_context,
            emergency=emergency,
            emergency_reason=emergency_reason,
            tool_calls_made=tool_calls,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)