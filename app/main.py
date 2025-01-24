import asyncio
import aiohttp
from bson import ObjectId
from fastapi import FastAPI, WebSocket
from app.core.websocket_client import start_websocket_client
from app.core.websocket_server import websocket_endpoint, electron_ws_manager
from app.core.config import API_BASE_URL, settings
from app.rag.paradigms.naive_rag.naive_rag_executer import NaiveRAGService

app = FastAPI()


import asyncio
from fastapi import FastAPI, WebSocket
from app.core.websocket_server import websocket_endpoint
from app.core.config import settings

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Start the WebSocket server and wait for Electron to send credentials."""
    print("WebSocket server started. Waiting for Electron to authenticate...")

@app.websocket("/ws/electron")
async def electron_ws(websocket: WebSocket):
    """WebSocket endpoint for Electron."""
    await websocket_endpoint(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6970)