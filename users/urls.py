from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Configuration initiale
    path('setup/', views.setup_view, name='setup'),
    
    # Authentification
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard et gestion des utilisateurs (Manager uniquement)
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('list/', views.user_list_view, name='user_list'),
    path('create/', views.user_create_view, name='user_create'),
    path('update/<int:pk>/', views.user_update_view, name='user_update'),
    path('delete/<int:pk>/', views.user_delete_view, name='user_delete'),
    path('profile/<int:pk>/', views.user_profile_view, name='user_profile'),
    path('change-password/<int:pk>/', views.change_password_view, name='change_password'),
    
    # Profil personnel (tous les utilisateurs)
    path('my-profile/', views.my_profile_view, name='my_profile'),
    path('my-password/', views.my_password_change_view, name='my_password_change'),
    
    # AJAX endpoints
    path('ajax/toggle-status/<int:pk>/', views.ajax_user_status_toggle, name='ajax_user_status_toggle'),
    path('ajax/search/', views.ajax_user_search, name='ajax_user_search'),
] 