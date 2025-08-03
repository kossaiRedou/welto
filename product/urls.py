from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    # Page d'accueil de la gestion des produits
    path('', views.product_management_home, name='management_home'),
    
    # Gestion des produits
    path('list/', views.product_list, name='product_list'),
    path('add/', views.add_product, name='add_product'),
    path('edit/<int:pk>/', views.edit_product, name='edit_product'),
    path('delete/<int:pk>/', views.delete_product, name='delete_product'),
    path('toggle/<int:pk>/', views.toggle_product_status, name='toggle_product'),
    
    # Gestion du stock
    path('stock/<int:pk>/', views.quick_stock_update, name='quick_stock'),
    
    # Gestion des catégories
    path('categories/', views.category_management, name='category_management'),
    path('categories/delete/<int:pk>/', views.delete_category, name='delete_category'),
    
    # AJAX
    path('ajax/search/', views.ajax_product_search, name='ajax_search'),
]