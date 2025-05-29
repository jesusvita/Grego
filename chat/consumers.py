import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract room name from the URL
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        # Create a Channels group name specific to the room
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        # The 'await' keyword is used because group_add is an async operation.
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name  # channel_name is a unique identifier for this consumer instance
        )

        await self.accept() # Accept the WebSocket connection

    async def disconnect(self, close_code):
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