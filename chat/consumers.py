import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings # Import settings
import redis # Import redis

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract room name from the URL
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        # Create a Channels group name specific to the room
        self.room_group_name = f'chat_{self.room_name}'

        print(f"DEBUG CONSUMER: Connecting to room: '{self.room_name}', group: '{self.room_group_name}', channel: '{self.channel_name}'") # DEBUG

        # Join room group
        # The 'await' keyword is used because group_add is an async operation.
        try:
            print(f"DEBUG CONSUMER: Attempting group_add for '{self.room_group_name}'") # DEBUG
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name  # channel_name is a unique identifier for this consumer instance
            )
            print(f"DEBUG CONSUMER: Successfully executed group_add for '{self.room_group_name}'") # DEBUG

            # --- Add this block for immediate Redis check ---
            try:
                redis_connection_url = settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0]
                r = redis.from_url(redis_connection_url, decode_responses=True)
                key_type = r.type(f"asgi:group:{self.room_group_name}") # Note: channels_redis prepends 'asgi:group:'
                print(f"DEBUG CONSUMER: Redis type for 'asgi:group:{self.room_group_name}' immediately after group_add: {key_type}")
            except Exception as redis_e:
                print(f"ERROR CONSUMER: Could not check Redis key type for 'asgi:group:{self.room_group_name}'. Error: {redis_e}")
            # --- End of added block ---

        except Exception as e:
            print(f"ERROR CONSUMER: Failed group_add for '{self.room_group_name}'. Error: {e}, Type: {type(e)}") # DEBUG
            # Depending on the severity, you might want to close the connection if group_add fails
            # await self.close()
            # return

        await self.accept() # Accept the WebSocket connection
        print(f"DEBUG CONSUMER: WebSocket connection accepted for room: '{self.room_name}'") # DEBUG

    async def disconnect(self, close_code):
        print(f"DEBUG CONSUMER: Disconnecting from room: '{self.room_name}', group: '{self.room_group_name}', channel: '{self.channel_name}'") # DEBUG
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket client
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        username = text_data_json.get('username', 'Anonymous') # Get username, default to 'Anonymous'

        # Send message to room group
        # This will trigger the 'chat_message' method on all consumers in the group.
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message', # Corresponds to chat_message method name
                'message': message,
                'username': username
            }
        )

    # Receive message from room group (handler for 'chat.message' type)
    async def chat_message(self, event): # Method name matches 'type' after replacing '.' with '_'
        message = event['message']
        username = event['username']

        # Send message back to the WebSocket client
        await self.send(text_data=json.dumps({'message': message, 'username': username}))