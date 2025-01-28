import asyncio
import aiohttp
from bson import ObjectId
from fastapi import FastAPI, WebSocket
from app.core.websocket_server import websocket_endpoint
from app.core.config import API_BASE_URL, settings

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP LOGIC
    print("WebSocket server started. Waiting for Electron to authenticate...")

    try:
        # Yield control back to FastAPI until shutdown
        yield
    finally:
        # SHUTDOWN LOGIC
        print("Shutting down FastAPI application...")

        # Cancel all active asyncio tasks (except the current one)
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()

        # Wait for these tasks to actually cancel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                print(f"Task cancelled with exception: {result}")

        print("All tasks have been cancelled. Application shutdown complete.")

# Pass the async context manager to FastAPI
app = FastAPI(lifespan=lifespan)

@app.websocket("/ws/electron")
async def electron_ws(websocket: WebSocket):
    """WebSocket endpoint for Electron."""
    await websocket_endpoint(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6970)
