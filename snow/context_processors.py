from .models import CustomUser

def roles_processor(request):
    return {
        'roles': CustomUser.ROLE_CHOICES
    }
