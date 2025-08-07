from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class SetupMiddleware:
    """Middleware pour rediriger vers la configuration initiale si aucun utilisateur n'existe"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Liste des URLs qui ne doivent pas être redirigées
        excluded_urls = [
            '/users/setup/',
            '/admin/',
            '/static/',
            '/media/',
            '/users/login/',
            '/users/logout/',
        ]
        
        # Vérifier si l'URL actuelle est exclue
        current_path = request.path
        is_excluded = any(current_path.startswith(url) for url in excluded_urls)
        
        # Si l'URL n'est pas exclue et qu'aucun utilisateur n'existe
        if not is_excluded and not request.path.startswith('/admin/'):
            try:
                from .models import User
                if not User.objects.exists():
                    # Rediriger vers la configuration initiale
                    return redirect('users:setup')
            except ImportError:
                # Si l'app users n'est pas disponible, continuer normalement
                pass
        
        response = self.get_response(request)
        return response 