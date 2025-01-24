import asyncio
import re
import websockets
import requests
from app.core.config import API_BASE_URL, WEBSOCKET_URL
from app.services.electron_ws_manager import electron_ws_manager
from app.services.log_processor import process_log  


class RustWebSocketClient:
    """
    Manages a WebSocket connection to the Rust WebSocket server.
    Automatically reconnects if the app state changes.
    """
    def __init__(self, app):
        self.app = app
        self.websocket = None
        self.task = None  # Store the running connection task
        self.connected_cd_id = None  # Track the last connected CD_ID

    async def connect(self):
        """
        Connects to the Rust WebSocket server using credentials from app state.
        If the credentials change, reconnects with the new credentials.
        """
        while True:
            try:
                # Retrieve latest credentials from app state
                app_state = self.app.state
                cd_id = app_state.organization_context.get("cd_id")
                cd_secret = app_state.organization_context.get("cd_secret")

                if not cd_id or not cd_secret:
                    print("No valid credentials found in app state. Retrying in 5 seconds...")
                    await asyncio.sleep(5)
                    continue

                # Check if credentials have changed
                if self.connected_cd_id == cd_id:
                    await asyncio.sleep(5)  # Avoid redundant reconnections
                    continue

                headers = {
                    "CD-ID": cd_id,
                    "CD-Secret": cd_secret,
                }
                ws_url = f"{WEBSOCKET_URL}"  

                print(f"Connecting to Rust WebSocket: {ws_url} with CD-ID: {cd_id}")

                async with websockets.connect(ws_url, additional_headers=headers) as websocket:
                    self.websocket = websocket
                    self.connected_cd_id = cd_id  # Store the active connection CD-ID
                    print("Connected to Rust WebSocket server")

                    while True:
                        message = await websocket.recv()
                        await self.process_message(message)

            except websockets.ConnectionClosed as e:
                print(f"Rust WebSocket connection closed: {e}. Retrying in 5 seconds...")
            except Exception as e:
                print(f"Rust WebSocket error: {e}. Retrying in 5 seconds...")
            finally:
                self.connected_cd_id = None  # Reset the connected ID on failure
                await asyncio.sleep(5)

    async def process_message(self, message):
        """
        Handles incoming WebSocket messages from the Rust server.
        Parses logs and broadcasts them to Electron clients.
        """
        pattern = r"New log ID:\s*(\w+)\s*and App ID:\s*(\w+)"
        match = re.search(pattern, message)

        if match:
            log_id = match.group(1)
            application_id = match.group(2)
            print(f"Extracted Log ID: {log_id}, App ID: {application_id}")

            headers = {
                "CD-ID": self.app.state.organization_context.get("cd_id"),
                "CD-Secret": self.app.state.organization_context.get("cd_secret"),
                "Application-ID": application_id,
            }

            response = requests.get(f"{API_BASE_URL}/logs/{log_id}", headers=headers)
            if response.status_code == 200:
                log_data = response.json()

                await self.broadcast_log(log_data, application_id, log_id)
                asyncio.create_task(process_log(log_data, application_id, log_id, self.app))
            
            else:
                print(f"Failed to fetch log details. Status: {response.status_code}, Error: {response.text}")
        else:
            print(f"Unexpected message format: {message}")

    async def broadcast_log(self, log_data, application_id, log_id):
        """
        Broadcast the received log to all connected Electron WebSocket clients.
        """
        message = {
            "protocol_version": "1.0",
            "type": "workflow",
            "workflow_id": "log_append",
            "action": "new_log",
            "message_id": f"log_{log_id}",
            "timestamp": asyncio.get_event_loop().time(),
            "data": {
                "log_id": log_id,
                "application_id": application_id,
                "raw_log": log_data
            }
        }
        await electron_ws_manager.broadcast(message)

    def start(self):
        """
        Starts the WebSocket connection in an async background task.
        If a previous connection task is running, it will be canceled before starting a new one.
        """
        if self.task:
            self.task.cancel()  # Cancel existing connection task
        self.task = asyncio.create_task(self.connect())  # Start new connection task


def start_websocket_client(app):
    """
    Initializes and starts the Rust WebSocket client with the given FastAPI app.
    """
    ws_client = RustWebSocketClient(app)
    ws_client.start()
