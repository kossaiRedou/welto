from django.urls import path
from . import views

app_name = 'client'

urlpatterns = [
    # Gestion complète des clients
    path('', views.ClientListView.as_view(), name='client_list'),
    path('add/', views.ClientCreateView.as_view(), name='add_client'),
    path('edit/<int:pk>/', views.ClientUpdateView.as_view(), name='edit_client'),
    path('delete/<int:pk>/', views.ClientDeleteView.as_view(), name='delete_client'),
    path('detail/<int:pk>/', views.client_detail_view, name='client_detail'),
    path('toggle-status/<int:pk>/', views.toggle_client_status, name='toggle_status'),
    
    # AJAX endpoints pour gestion des clients
    path('ajax/search/', views.ajax_search_clients, name='ajax_search'),
    path('ajax/create/', views.ajax_create_client, name='ajax_create'),
    path('ajax/info/<int:client_id>/', views.ajax_get_client_info, name='ajax_info'),
]