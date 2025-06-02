from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
import redis
from django.contrib.auth.decorators import login_required
import logging # Import the logging module

logger = logging.getLogger(__name__) # Get a logger for this module

@login_required 
def create_room_view(request):
    """
    Serves the page where logged-in users can enter a room name to create or join.
    Only accessible to logged-in users.
    """
    return render(request, 'chat/create_room.html')

@login_required
def home_view(request):
    return render(request, 'chat/home.html')

@login_required
def list_active_rooms(request): # Consider if this view also needs @login_required
    active_rooms = []
    try:
        
        redis_connection_url = settings.CHANNEL_LAYERS['default']['CONFIG']['hosts'][0]
        r = redis.from_url(redis_connection_url, decode_responses=True)

       
        for group_key in r.scan_iter(match='asgi:group:chat_*'):
            
            key_type = r.type(group_key)
            if key_type == 'set':
                if r.scard(group_key) > 0: # SCARD for sets
                    
                    if 'chat_' in group_key:
                        room_name_parts = group_key.split('chat_', 1)
                        if len(room_name_parts) > 1:
                            room_name = room_name_parts[-1]
                            active_rooms.append(room_name)
                        else:
                            logger.warning(f"Key '{group_key}' matched pattern but could not extract room name after 'chat_'.")
                    else:
                        logger.warning(f"Key '{group_key}' matched pattern but 'chat_' prefix was not found as expected.")
            # channels_redis uses Redis Sets for groups. ZSET handling might be unnecessary unless you have a specific reason.
            # elif key_type == 'zset': 
            #     logger.info(f"Found key '{group_key}' as a ZSET. This is unusual for standard channel groups.")
            #     if r.zcard(group_key) > 0: 
            #         if 'chat_' in group_key:
            #             room_name_parts = group_key.split('chat_', 1)
            #             if len(room_name_parts) > 1:
            #                 room_name = room_name_parts[-1]
            #                 active_rooms.append(room_name)
            #             else:
            #                 logger.warning(f"ZSET Key '{group_key}' matched pattern but could not extract room name after 'chat_'.")
            #         else:
            #             logger.warning(f"ZSET Key '{group_key}' matched pattern but 'chat_' prefix was not found as expected.")
            else:
                logger.warning(f"Found key '{group_key}' with pattern 'asgi:group:chat_*' but it is not a Redis Set (type: {key_type}). Skipping.")
                
    except redis.exceptions.RedisError as e: 
        logger.error(f"RedisError connecting to Redis or fetching rooms: {e}")
        
    except Exception as e: 
        logger.error(f"An unexpected error occurred while listing active rooms: {e}", exc_info=True)

    # Remove duplicates just in case and sort
    return render(request, 'chat/list_rooms.html', {'active_rooms': sorted(list(set(active_rooms)))}) 



def room(request, room_name):
    secret_phrase = request.GET.get('secret', None) # Get secret phrase from query params
    return render(request, 'chat/room.html', {
        'room_name': room_name,
        'user': request.user, # Pass the authenticated user object
        'secret_phrase_for_creator': secret_phrase if request.user.is_authenticated else None
    })

def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('chat:home')  # Corrected redirect to namespaced URL
    else:
        form = UserCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('chat:home') # Corrected redirect to namespaced URL
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')