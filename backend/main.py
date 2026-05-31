import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from models import ChatRequest, ChatResponse
from agent import run_agent, init_gemini

init_gemini()

app = FastAPI(title="Personal Health Navigator", version="1.0.0")

# CORS — allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "model": "gemini-3.1-flash-lite"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        reply, updated_history, emergency, emergency_reason, tool_calls = await run_agent(
            user_message=request.message,
            raw_history=[msg.dict() for msg in request.history],
        )
        return ChatResponse(
            reply=reply,
            updated_history=updated_history,
            emergency=emergency,
            emergency_reason=emergency_reason,
            tool_calls_made=tool_calls,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Serve frontend static files (for single-server deployment)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
