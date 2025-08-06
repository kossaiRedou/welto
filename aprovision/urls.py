from django.urls import path
from . import views

app_name = 'aprovision'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_view, name='dashboard'),
    
    # Dashboard analytique
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    
    # Approvisionnement
    path('approvisionnement/', views.approvisionnement_view, name='approvisionnement'),
    
    # Dépenses
    path('nouvelle-depense/', views.nouvelle_depense_view, name='nouvelle_depense'),
    
    # Listes
    path('mouvements/', views.MouvementListView.as_view(), name='mouvement_list'),
    path('depenses/', views.DepenseListView.as_view(), name='depense_list'),
    
    # AJAX
    path('ajax/depense-rapide/', views.ajax_depense_rapide, name='ajax_depense_rapide'),
    path('ajax/recherche-produits/', views.ajax_recherche_produits, name='ajax_recherche_produits'),
    path('ajax/types-depense/', views.ajax_get_types_depense, name='ajax_types_depense'),
    path('ajax/create-type-depense/', views.ajax_create_type_depense, name='ajax_create_type_depense'),
    path('ajax/dashboard-stats/', views.ajax_get_dashboard_stats, name='ajax_dashboard_stats'),
    path('ajax/analytics-data/', views.ajax_analytics_data, name='ajax_analytics_data'),
]