from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
import redis
import re # Import the re module for regular expressions
from django.contrib.auth.decorators import login_required
import logging # Import the logging module

# Import the shared dictionary from consumers. See caveats below.
from .consumers import room_secrets_and_creators

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

            # Extract the 'chat_actualroomname' part (e.g., "chat_table_20")
            # This is the format used as keys in room_secrets_and_creators
            match = re.match(r'asgi:group:(chat_.+)', group_key)
            if not match:
                logger.warning(f"Key '{group_key}' matched Redis pattern but could not extract 'chat_...' suffix.")
                continue
            
            consumer_side_group_name = match.group(1) # e.g., "chat_table_20"

            # Derive display name (e.g., "table 20")
            # Assumes consumer_side_group_name starts with "chat_"
            if consumer_side_group_name.startswith("chat_"):
                slugified_room_name = consumer_side_group_name[len("chat_"):]
                display_room_name = slugified_room_name.replace('_', ' ')
            else:
                # Should not happen with the regex match, but as a fallback
                display_room_name = consumer_side_group_name.replace('_', ' ')

            # Check 1: Is the room considered "active" by the consumer's secret logic?
            if consumer_side_group_name not in room_secrets_and_creators:
                logger.info(f"Room '{display_room_name}' (key: {group_key}, consumer_group: {consumer_side_group_name}) found in Redis but not in consumer's room_secrets_and_creators. Skipping.")
                continue

            # Check 2: Does the Redis group actually have members?
            is_redis_group_populated = False
            if key_type == 'set':
                if r.scard(group_key) > 0:
                    is_redis_group_populated = True
            elif key_type == 'zset':
                logger.info(f"Found key '{group_key}' as a ZSET. Checking ZCARD.")
                if r.zcard(group_key) > 0:
                    is_redis_group_populated = True
            else:
                logger.warning(f"Key '{group_key}' (for room '{display_room_name}') has unexpected type '{key_type}'. Skipping.")
                continue

            if is_redis_group_populated:
                active_rooms.append(display_room_name)
            else:
                logger.info(f"Room '{display_room_name}' (key: {group_key}) is in room_secrets_and_creators but Redis group is empty. Not listing as active.")

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

def review_qr_view(request):
    """
    Serves a page that displays a QR code for the Google Review link.
    """
    google_review_url = "https://search.google.com/local/writereview?placeid=ChIJX42RYQ2k2YgR8qb2wqVMbVk"
    context = {
        'qr_data_url': google_review_url,
        'page_title': "Google Review QR Code"
    }
    return render(request, 'chat/review_qr.html', context)

def menu_qr_view(request):
    """
    Serves a page that displays a QR code for the Menu link.
    """
    menu_url = "https://www.benihana.com/menus/"
    context = {
        'qr_data_url': menu_url,
        'page_title': "Restaurant Menu QR Code"
    }
    return render(request, 'chat/menu_qr.html', context)