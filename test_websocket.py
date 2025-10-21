import asyncio
import json
import websockets  # pip install websockets

async def main():
    # Adjust this port if your client_api runs on something else
    uri = "ws://127.0.0.1:5167/websocket?token=testtoken"

    async with websockets.connect(uri) as websocket:
        print("Connected to the server!")

        # Send a test message
        message = {"hello": "server"}
        await websocket.send(json.dumps(message))
        print(f"Sent: {message}")

        # Wait for the echo reply
        response = await websocket.recv()
        print(f"Received: {response}")

# Run the coroutine
asyncio.run(main())
