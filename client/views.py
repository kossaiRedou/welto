from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from .models import Client
import json


@staff_member_required
@require_http_methods(["GET"])
def ajax_search_clients(request):
    """Recherche de clients par téléphone via AJAX"""
    phone_query = request.GET.get('phone', '').strip()
    
    if len(phone_query) < 2:  # Au moins 2 caractères pour déclencher la recherche
        return JsonResponse({
            'success': True,
            'clients': [],
            'message': 'Tapez au moins 2 chiffres pour rechercher'
        })
    
    # Rechercher les clients
    clients = Client.search_by_phone(phone_query)
    
    # Préparer les données pour le JSON
    clients_data = []
    for client in clients:
        clients_data.append({
            'id': client.id,
            'name': client.name,
            'phone': client.phone,
            'total_orders': client.total_orders(),
            'last_order': client.last_order_date().strftime('%d/%m/%Y') if client.last_order_date() else 'Jamais',
            'display': f"{client.name} ({client.phone})"
        })
    
    return JsonResponse({
        'success': True,
        'clients': clients_data,
        'count': len(clients_data)
    })


@staff_member_required
@require_http_methods(["POST"])
def ajax_create_client(request):
    """Création rapide d'un client via AJAX"""
    try:
        # Récupérer les données JSON
        data = json.loads(request.body)
        phone = data.get('phone', '').strip()
        name = data.get('name', '').strip()
        
        # Validation simple
        if not phone or not name:
            return JsonResponse({
                'success': False,
                'error': 'Le téléphone et le nom sont obligatoires'
            })
        
        if len(phone) < 8:
            return JsonResponse({
                'success': False,
                'error': 'Le numéro de téléphone doit contenir au moins 8 chiffres'
            })
        
        # Vérifier si le client existe déjà
        if Client.objects.filter(phone=phone).exists():
            return JsonResponse({
                'success': False,
                'error': f'Un client avec le numéro {phone} existe déjà'
            })
        
        # Créer le client
        client = Client.objects.create(
            phone=phone,
            name=name
        )
        
        return JsonResponse({
            'success': True,
            'client': {
                'id': client.id,
                'name': client.name,
                'phone': client.phone,
                'display': f"{client.name} ({client.phone})"
            },
            'message': f'Client "{client.name}" créé avec succès'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Données JSON invalides'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors de la création: {str(e)}'
        })


@staff_member_required
def ajax_get_client_info(request, client_id):
    """Récupérer les informations détaillées d'un client via AJAX"""
    try:
        client = get_object_or_404(Client, id=client_id)
        
        return JsonResponse({
            'success': True,
            'client': {
                'id': client.id,
                'name': client.name,
                'phone': client.phone,
                'total_orders': client.total_orders(),
                'total_spent': str(client.total_spent()),
                'last_order': client.last_order_date().strftime('%d/%m/%Y') if client.last_order_date() else 'Jamais',
                'created_at': client.created_at.strftime('%d/%m/%Y'),
                'display': f"{client.name} ({client.phone})"
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Erreur: {str(e)}'
        })