from django.apps import AppConfig


class AprovisionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'aprovision'
    
    def ready(self):
        import aprovision.signals