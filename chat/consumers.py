import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings # Import settings
import redis # Import redis
import logging

logger = logging.getLogger(__name__)

# Module-level storage for room secrets and creators (NOT SUITABLE FOR MULTI-SERVER PRODUCTION)
room_secrets_and_creators = {}

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extract room name from the URL
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        # Create a Channels group name specific to the room
        self.room_group_name = f'chat_{self.room_name}'

        logger.info(f"[CONSUMER CONNECT] Scope user: {self.scope.get('user', 'N/A')}, Authenticated: {self.scope.get('user', type('obj', (object,), {'is_authenticated': False})()).is_authenticated}")

        # Extract secret phrase if present in the scope (passed from URL via view to WebSocket scope)
        # This requires modifying asgi.py or using a custom middleware to pass query params to scope if not already there.
        # For simplicity, we'll assume the client (room.html JS) will send it on first message if it's the creator.
        # A better way is to pass it during WebSocket connection handshake if possible.
        # For now, we'll rely on the view passing it to the room.html template,
        # and the creator's client JS will know it.

        query_string = self.scope.get('query_string', b'').decode()
        initial_secret = None
        if query_string:
            params = dict(s.split('=', 1) for s in query_string.split('&') if '=' in s)
            initial_secret = params.get('secret')

        logger.debug(f"Connecting to room: '{self.room_name}', group: '{self.room_group_name}', channel: '{self.channel_name}', initial_secret: '{initial_secret}'")

        is_authenticated_user = self.scope['user'].is_authenticated
        is_creating_or_rejoining_with_secret = is_authenticated_user and initial_secret
        is_room_already_active_with_secret = self.room_group_name in room_secrets_and_creators

        if is_room_already_active_with_secret:
            # Room exists in our controlled list.
            if is_creating_or_rejoining_with_secret:
                # Authenticated user trying to connect with a secret. Validate if they are the creator and secret matches.
                if room_secrets_and_creators[self.room_group_name]['creator_username'] != self.scope['user'].username or \
                   room_secrets_and_creators[self.room_group_name]['secret'] != initial_secret:
                    logger.warning(f"Auth user '{self.scope['user'].username}' attempted to join room '{self.room_name}' with incorrect secret or as non-creator. Rejecting.")
                    await self.close(code=4003) # Access denied / wrong secret
                    return
            # If not trying to join with a secret, allow connection (auth or anon can join an active room)
        elif not is_creating_or_rejoining_with_secret:
            # Room is NOT active with a secret, AND the current user is NOT an authenticated user trying to create it with a secret.
            logger.info(f"WebSocket connection rejected for room '{self.room_name}'. Room not active or not being created with secret by authenticated user.")
            await self.close(code=4004) # Room not found/active or invalid creation attempt
            return
       
        # Join room group
        # The 'await' keyword is used because group_add is an async operation.
        try:
            logger.debug(f"Attempting group_add for '{self.room_group_name}'")
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name  # channel_name is a unique identifier for this consumer instance
            )
            logger.debug(f"Successfully executed group_add for '{self.room_group_name}'")

            if is_creating_or_rejoining_with_secret and not is_room_already_active_with_secret:
                # This is a new room being created with a secret by an authenticated user
                room_secrets_and_creators[self.room_group_name] = {
                    'secret': initial_secret,
                    'creator_username': self.scope['user'].username,
                    # 'creator_channel_name' is less critical if creator can reconnect from any channel
                }
                logger.info(f"Room '{self.room_name}' CREATED by '{self.scope['user'].username}' with secret '{initial_secret}'.")
            elif is_room_already_active_with_secret and is_authenticated_user and room_secrets_and_creators[self.room_group_name]['creator_username'] == self.scope['user'].username:
                 logger.info(f"Creator '{self.scope['user'].username}' (re)connected to room '{self.room_name}'.")


        except Exception as e:
            logger.error(f"Failed group_add for '{self.room_group_name}'. Error: {e}, Type: {type(e)}")
            # Depending on the severity, you might want to close the connection if group_add fails
            await self.close() # Close connection if group_add fails
            return # Prevent self.accept()

        await self.accept() # Accept the WebSocket connection
        logger.debug(f"WebSocket connection accepted for room: '{self.room_name}'")

    async def disconnect(self, close_code):
        logger.debug(f"Disconnecting from room: '{self.room_name}', group: '{self.room_group_name}', channel: '{self.channel_name}', code: {close_code}")
        # Optional: Clean up room_secrets_and_creators if room becomes empty.
        # This requires checking group size, which is tricky without direct Redis SCARD here.
        # For now, secrets persist until server restart or manual cleanup.

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    # Receive message from WebSocket client
    async def receive(self, text_data):
        logger.debug(f"Raw text_data received: {text_data} from channel {self.channel_name}")
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json['message']
            # Attempt to get the username sent by the client
            client_sent_username = text_data_json.get('username')
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Invalid message format from {self.channel_name}: {text_data}, error: {e}")
            await self.send(text_data=json.dumps({'error': 'Invalid message format.'}))
            return

        final_username = 'Anonymous' # Default username
        if self.scope['user'].is_authenticated:
            final_username = self.scope['user'].username
            logger.debug(f"User is authenticated. Using Django username: {final_username}")
        
        # Check for secret phrase
            room_data = room_secrets_and_creators.get(self.room_group_name)
            if room_data and \
               room_data['creator_username'] == final_username and \
               message == room_data['secret']:
                
                logger.info(f"Secret phrase '{message}' used by creator '{final_username}' in room '{self.room_name}'. Initiating shutdown.")
                # Send shutdown message to all clients in the group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat.room_shutdown',
                        'message': f"Room '{self.room_name}' is being closed by the creator."
                    }
                )
                # Clean up the secret storage
                if self.room_group_name in room_secrets_and_creators:
                    del room_secrets_and_creators[self.room_group_name]
                
                # Note: group_discard for all members happens when they disconnect after receiving shutdown.
                # Or we could try to iterate and close connections, but that's more complex.
                return # Stop further processing of this message
        else:
            logger.debug(f"User is anonymous. Client sent username: '{client_sent_username}'")
            if client_sent_username and client_sent_username.strip(): # Check if a non-empty name was sent
                final_username = client_sent_username.strip()
            else:
                logger.warning(f"Anonymous user did not send a valid username or it was empty. Defaulting to 'Anonymous'. Payload was: {text_data_json}")
                


        logger.info(f"Message from '{final_username}': '{message}' in room '{self.room_name}'")

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message', # Corresponds to chat_message method name
                'message': message,
                'username': final_username
            }
        )

    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        logger.debug(f"Broadcasting message to {self.channel_name}: User '{username}', Msg '{message}'")

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username
        }))

    async def chat_room_shutdown(self, event):
        """
        Handler for the room_shutdown message. Sends a final message and closes the WebSocket.
        """
        message = event['message']
        logger.info(f"Sending shutdown event to client {self.channel_name}: {message}")
        # Send shutdown message to WebSocket client
        await self.send(text_data=json.dumps({
            'message': message,
            'username': "System" # Or from event if specified, e.g., event.get('sender_username')
        }))
        await self.close(code=1000) # Graceful shutdown from server side