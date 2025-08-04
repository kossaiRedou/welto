from django.urls import path
from . import views

app_name = 'client'

urlpatterns = [
    # AJAX endpoints pour gestion des clients
    path('ajax/search/', views.ajax_search_clients, name='ajax_search'),
    path('ajax/create/', views.ajax_create_client, name='ajax_create'),
    path('ajax/info/<int:client_id>/', views.ajax_get_client_info, name='ajax_info'),
]