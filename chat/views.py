from django.shortcuts import render
from django.conf import settings
import redis
# urllib.parse 


def index(request):
   
    return render(request, 'chat/index.html')

def list_active_rooms(request):
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
                            
                            print(f"WARNING: Key '{group_key}' matched pattern but could not extract room name after 'chat_'.")
                    else:
                        
                        print(f"WARNING: Key '{group_key}' matched pattern but 'chat_' prefix was not found as expected.")
            elif key_type == 'zset': # Handle zset case
                print(f"INFO: Found key '{group_key}' as a ZSET. Attempting to list it if active.")
                if r.zcard(group_key) > 0: # ZCARD for sorted sets
                    if 'chat_' in group_key:
                        room_name_parts = group_key.split('chat_', 1)
                        if len(room_name_parts) > 1:
                            room_name = room_name_parts[-1]
                            active_rooms.append(room_name)
                        else:
                            print(f"WARNING: ZSET Key '{group_key}' matched pattern but could not extract room name after 'chat_'.")
                    else:
                        print(f"WARNING: ZSET Key '{group_key}' matched pattern but 'chat_' prefix was not found as expected.")
            else:
                
                print(f"WARNING: Found key '{group_key}' with pattern 'asgi:group:chat_*' but it is neither a Set nor a ZSet (type: {key_type}). Skipping.")
                
    except redis.exceptions.RedisError as e: 
        
        print(f"RedisError connecting to Redis or fetching rooms: {e}")
        
    except Exception as e: 
        print(f"An unexpected error occurred: {e}")


    return render(request, 'chat/list_rooms.html', {'active_rooms': sorted(list(set(active_rooms)))})

def room(request, room_name):
    return render(request, 'chat/room.html', {
        'room_name': room_name
    })
