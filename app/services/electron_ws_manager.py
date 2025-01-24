import asyncio
from datetime import datetime
from app.utils.ws_protocol import validate_message, build_ack_message

class ElectronWebSocketManager:
    def __init__(self):
        self.active_connections = set()  # Store active WebSocket connections

    async def connect(self, websocket):
        """
        Handle new WebSocket connection.
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        print("New WebSocket connection established")

    def disconnect(self, websocket):
        """
        Handle WebSocket disconnection.
        """
        self.active_connections.remove(websocket)
        print("WebSocket connection closed")

    async def handle_message(self, websocket, message):
        """
        Process incoming WebSocket messages.
        """
        # Validate incoming message
        validated_message = validate_message(message)
        if not validated_message:
            await websocket.send_json({"error": "Invalid message format"})
            return

        # Example routing logic
        message_type = validated_message["type"]
        if message_type == "workflow":
            await self.handle_workflow_message(websocket, validated_message)
        else:
            await websocket.send_json({"error": f"Unknown message type: {message_type}"})

    async def handle_workflow_message(self, websocket, message):
        """
        Handle workflow-related messages.
        """
        action = message.get("action")
        if action == "init":
            # Respond to workflow initialization
            response = build_ack_message(message["message_id"], status="initialized")
            await websocket.send_json(response)
        elif action == "update":
            # Handle updates (e.g., streaming logs)
            data = message.get("data", {})
            print(f"Received log update: {data}")
            # Example: broadcast update to all clients
            await self.broadcast({"type": "workflow", "action": "update", "data": data})
        else:
            await websocket.send_json({"error": f"Unknown action: {action}"})

    async def broadcast(self, message):
        """
        Broadcast a message to all connected clients.
        """
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Failed to send message: {e}")

electron_ws_manager = ElectronWebSocketManager()