from django.shortcuts import render

# Create your views here.
def index(request):
    # This view could be more complex, e.g., listing rooms or having a form to enter a room name.
    # For now, it just renders a simple index page.
    return render(request, 'chat/index.html')

def room(request, room_name):
    return render(request, 'chat/room.html', {
        'room_name': room_name
    })