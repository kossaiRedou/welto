from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count, Sum
from django_tables2 import RequestConfig
from .models import Client
from .forms import ClientForm, ClientSearchForm
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
        
        # Nettoyer le numéro (garder seulement les chiffres)
        phone = ''.join(filter(str.isdigit, phone))
        
        if len(phone) != 7:
            return JsonResponse({
                'success': False,
                'error': 'Le numéro de téléphone doit contenir exactement 7 chiffres (format Gambie)'
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


# === VUES CRUD COMPLÈTES POUR GESTION DES CLIENTS ===

@method_decorator(staff_member_required, name='dispatch')
class ClientListView(ListView):
    """Vue pour lister tous les clients avec recherche"""
    model = Client
    template_name = 'client/client_list.html'
    context_object_name = 'clients'
    paginate_by = 20
    
    def get_queryset(self):
        """Filtrer les clients selon les critères de recherche"""
        queryset = Client.objects.annotate(
            total_orders=Count('orders'),
            total_spent=Sum('orders__final_value')
        ).order_by('-created_at')
        
        # Appliquer les filtres de recherche
        search = self.request.GET.get('search', '').strip()
        status = self.request.GET.get('status', '')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(phone__icontains=search)
            )
        
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = ClientSearchForm(self.request.GET)
        context['total_clients'] = Client.objects.count()
        context['active_clients'] = Client.objects.filter(is_active=True).count()
        return context


@method_decorator(staff_member_required, name='dispatch')
class ClientCreateView(CreateView):
    """Vue pour créer un nouveau client"""
    model = Client
    form_class = ClientForm
    template_name = 'client/client_form.html'
    success_url = reverse_lazy('client:client_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Client "{form.cleaned_data["name"]}" créé avec succès !')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Nouveau Client'
        context['submit_text'] = 'Créer le Client'
        return context


@method_decorator(staff_member_required, name='dispatch')
class ClientUpdateView(UpdateView):
    """Vue pour modifier un client existant"""
    model = Client
    form_class = ClientForm
    template_name = 'client/client_form.html'
    success_url = reverse_lazy('client:client_list')
    
    def form_valid(self, form):
        messages.success(self.request, f'Client "{form.cleaned_data["name"]}" modifié avec succès !')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = f'Modifier {self.object.name}'
        context['submit_text'] = 'Sauvegarder'
        return context


@method_decorator(staff_member_required, name='dispatch')
class ClientDeleteView(DeleteView):
    """Vue pour supprimer un client"""
    model = Client
    template_name = 'client/client_confirm_delete.html'
    success_url = reverse_lazy('client:client_list')
    
    def delete(self, request, *args, **kwargs):
        client = self.get_object()
        messages.success(request, f'Client "{client.name}" supprimé avec succès !')
        return super().delete(request, *args, **kwargs)


@staff_member_required
def client_detail_view(request, pk):
    """Vue détaillée d'un client avec ses commandes"""
    client = get_object_or_404(Client, pk=pk)
    
    # Statistiques du client
    orders = client.orders.all().order_by('-date')
    total_orders = orders.count()
    total_spent = orders.aggregate(Sum('final_value'))['final_value__sum'] or 0
    paid_orders = orders.filter(is_paid=True).count()
    unpaid_orders = orders.filter(is_paid=False).count()
    unpaid_amount = orders.filter(is_paid=False).aggregate(Sum('final_value'))['final_value__sum'] or 0
    
    # Dernières commandes (5 plus récentes)
    recent_orders = orders[:5]
    
    context = {
        'client': client,
        'orders': orders,
        'recent_orders': recent_orders,
        'stats': {
            'total_orders': total_orders,
            'total_spent': total_spent,
            'paid_orders': paid_orders,
            'unpaid_orders': unpaid_orders,
            'unpaid_amount': unpaid_amount,
        }
    }
    
    return render(request, 'client/client_detail.html', context)


@staff_member_required
def toggle_client_status(request, pk):
    """Activer/désactiver un client via AJAX"""
    if request.method == 'POST':
        try:
            client = get_object_or_404(Client, pk=pk)
            client.is_active = not client.is_active
            client.save()
            
            status = "activé" if client.is_active else "désactivé"
            messages.success(request, f'Client "{client.name}" {status} !')
            
            return JsonResponse({
                'success': True,
                'is_active': client.is_active,
                'message': f'Client {status}'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})