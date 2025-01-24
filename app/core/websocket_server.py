from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
import asyncio
import aiohttp
from bson import ObjectId
from app.core.websocket_client import start_websocket_client
from app.rag.paradigms.naive_rag.naive_rag_executer import NaiveRAGService
from app.core.config import API_BASE_URL
from app.services.electron_ws_manager import electron_ws_manager


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint to handle Electron communication with keep-alive.
    """
    await electron_ws_manager.connect(websocket)

    try:
        await asyncio.gather(
            websocket_handler(websocket),  # Handles incoming messages
            keep_alive(websocket)          # Sends periodic ping messages
        )
    except WebSocketDisconnect:
        electron_ws_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        electron_ws_manager.disconnect(websocket)


async def keep_alive(websocket: WebSocket):
    """
    Periodically send a ping message to keep the WebSocket connection alive.
    """
    try:
        while True:
            await websocket.send_json({"type": "ping", "timestamp": datetime.utcnow().isoformat()})
            await asyncio.sleep(30)  # Adjust interval as needed
    except Exception as e:
        print(f"Keep-alive error: {e}")
        raise WebSocketDisconnect


async def websocket_handler(websocket: WebSocket):
    """
    Handle incoming WebSocket messages.
    """
    while True:
        try:
            message = await websocket.receive_json()
            message_type = message.get("type")

            if message_type == "authenticate":
                await handle_authentication(websocket, message)

                # After authentication, start a new Rust WebSocket connection
                app = websocket.app
                start_websocket_client(app)  # Reconnect with the new credentials
                
            elif message_type == "new_application":
                await handle_new_application(websocket, message)

            else:
                await electron_ws_manager.handle_message(websocket, message)

        except Exception as e:
            print(f"Error receiving message: {e}")
            break


async def fetch_application_ids(cd_id: str, cd_secret: str):
    """
    Fetch application IDs from the Rust API asynchronously, including custom headers.
    """
    headers = {
        'CD-ID': cd_id,
        'CD-Secret': cd_secret
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_BASE_URL}/applications', headers=headers) as response:
                response.raise_for_status()  # Raise an exception for HTTP errors
                data = await response.json()
                print("Fetched application data:", data)

                # Extract and convert ObjectId strings to ObjectId instances
                application_ids = [str(ObjectId(app['_id']['$oid'])) for app in data]
                return application_ids
    except Exception as e:
        print(f"Error fetching application IDs: {e}")
        return []  # Return empty list if error occurs


async def handle_authentication(websocket: WebSocket, message: dict):
    """
    Handles authentication setup when Electron sends organization details.
    Ensures only one organization context is active at a time.
    """
    app = websocket.app  # Get FastAPI app instance

    cd_id = message.get("cd_id")
    cd_secret = message.get("cd_secret")
    organization_id = message.get("organization_id")

    if not all([cd_id, cd_secret, organization_id]):
        await websocket.send_json({"error": "Missing required fields: cd_id, cd_secret, organization_id"})
        return

    # Reset previous organization context (Allow only one at a time)
    app.state.organization_context = {
        "cd_id": cd_id,
        "cd_secret": cd_secret,
        "organization_id": organization_id
    }

    # Remove previous `NaiveRAGService` instances
    if hasattr(app.state, "naive_rag_services"):
        app.state.naive_rag_services.clear()  # Clear all previous services

    # Fetch application IDs dynamically
    application_ids = await fetch_application_ids(cd_id, cd_secret)

    if not application_ids:
        await websocket.send_json({"error": "Failed to fetch application IDs"})
        return

    # Create NaiveRAGService instances for fetched applications
    app.state.naive_rag_services = {}
    for app_id in application_ids:
        app.state.naive_rag_services[app_id] = NaiveRAGService(
            application_id=app_id, persist_dir="./storage/naive_rag_storage"
        )
    
    print(f"Initialized NaiveRAGService for applications: {application_ids}")

    await websocket.send_json({
        "status": "authenticated",
        "message": f"NaiveRAGService created for organization {organization_id}",
        "application_ids": application_ids
    })


async def handle_new_application(websocket: WebSocket, message: dict):
    """
    Handles creating a new NaiveRAGService instance when a new application is registered.
    """
    app = websocket.app  # Get FastAPI app instance
    application_id = message.get("application_id")

    if not application_id:
        await websocket.send_json({"error": "Missing required field: application_id"})
        return

    # Ensure organization context is already set
    if not hasattr(app.state, "organization_context"):
        await websocket.send_json({"error": "No active organization context found."})
        return

    # Add new application ID to NaiveRAGService
    if not hasattr(app.state, "naive_rag_services"):
        app.state.naive_rag_services = {}

    # Check if the service already exists
    if application_id in app.state.naive_rag_services:
        service = app.state.naive_rag_services[application_id]
        if not service.index:
            try:
                print(f"Application {application_id} already exists in RAG services.")
                vector_index = service._load_or_create_index()
            except Exception as e:
                await websocket.send_json({"message": f"Could not create NaiveRAGService for application {application_id}.{e}"})
            await websocket.send_json({"message": f"Application {application_id} already exists in RAG services."})
        return

    # Create and store new NaiveRAGService instance
    app.state.naive_rag_services[application_id] = NaiveRAGService(
        application_id=application_id, persist_dir="./storage/naive_rag_storage"
    )

    print(f"New NaiveRAGService initialized for application: {application_id}")

    await websocket.send_json({
        "status": "success",
        "message": f"New NaiveRAGService created for application {application_id}"
    })
