from datetime import datetime
from fastapi import HTTPException
from llama_index.core.base.response.schema import Response, StreamingResponse

from app.services.electron_ws_manager import electron_ws_manager


async def process_log_with_rag(log_data: dict,log_id:str, application_id: str, app):
    """
    Process log data using NaiveRAGService to find a solution.

    Args:
        app (FastAPI): The FastAPI application instance to access app state.
        log_data (dict): The structured log data containing details like error, traceback, and other metadata.
        application_id (str): The application ID to fetch the appropriate NaiveRAGService.

    Returns:
        dict: The aggregated response from the RAG service with additional metadata.
    """
    try:
        # Get the appropriate NaiveRAGService from app state
        rag_service = app.state.naive_rag_services.get(application_id)
        if not rag_service:
            raise HTTPException(
                status_code=404,
                detail=f"RAG service for application ID '{application_id}' not found.",
            )

        # Extract relevant information from the log data
        error_message = log_data.get("error", "No error message provided.")
        traceback = log_data.get("traceback", "No traceback available.")
        url = log_data.get("url", "No URL provided.")
        method = log_data.get("method", "No method provided.")
        created_at = log_data.get("created_at", "No timestamp provided.")

        # Construct the query for the RAG service
        query = f"""
        I encountered the following error while accessing {url} using {method} method:
        Error Message: {error_message}
        Traceback: {traceback}
        Can you provide a detailed solution or suggest debugging steps?
        """

        # Query the RAG service
        response = rag_service.query(query)

        response_text = ""  # To aggregate the response

        # Handle streaming response
        if isinstance(response, StreamingResponse):
            for chunk in response.response_gen:  # Using a regular for loop for synchronous generator
                # Stream the chunk to WebSocket clients
                message = {
                    "protocol_version": "1.0",
                    "type": "workflow",
                    "workflow_id": "log_process",
                    "action": "stream_log_response",
                    "data": {"chunk": chunk, "application_id": application_id,"log_id": log_id},
                }
                await electron_ws_manager.broadcast(message)
                # Aggregate the chunk into the response text
                response_text += chunk
            

            print(f"Aggregated RAG StreamingResponse: {response_text}")

            # Send a "stream complete" message after the for loop
            stream_complete_message = {
                "protocol_version": "1.0",
                "type": "workflow",
                "workflow_id": "log_process",
                "action": "stream_complete",
                "data": {"application_id": application_id, "log_id": log_id},
            }
            await electron_ws_manager.broadcast(stream_complete_message)
            print("Streaming completed.")

        else:
            # Handle regular response
            response_text = response.response
            # Stream the full response to WebSocket clients
            message = {
                "protocol_version": "1.0",
                "type": "workflow",
                "workflow_id": "log_process",
                "action": "final_log_response",
                "data": {"response": response_text, "application_id": application_id},
            }
            await electron_ws_manager.broadcast(message)
            print(f"RAG Response: {response_text}")

        # Prepare a structured response to return
        return {
            "application_id": application_id,
            "created_at": created_at,
            "query": query,
            "rag_response": response_text,
            "processed_at": datetime.utcnow().isoformat() + "Z",
        }

    except Exception as e:
        print(f"An error occurred while processing the log: {str(e)}")
        error_message = {
            "protocol_version": "1.0",
            "type": "workflow",
            "workflow_id": "log_process",
            "action": "error",
            "data": {"error": str(e), "application_id": application_id},
        }
        await electron_ws_manager.broadcast(error_message)

        return {
            "error": f"An error occurred while processing the log: {str(e)}",
            "log_data": log_data,
            "processed_at": datetime.utcnow().isoformat() + "Z",
        }
