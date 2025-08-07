from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q, Count
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import json
from django.db import models
from django.urls import reverse_lazy

from .models import (
    TypeDepense, Depense, MouvementStock, TypeMouvement, 
    Approvisionnement
)
from product.models import Product, Category, LOW_STOCK_THRESHOLD
from order.models import Order, OrderItem


@login_required
def dashboard_view(request):
    """Dashboard principal pour la gestion des approvisionnements et dépenses"""
    
    # Période par défaut : 30 derniers jours
    today = timezone.now().date()
    date_debut = today - timedelta(days=30)
    date_fin = today
    
    # Filtres de date depuis la requête
    if request.GET.get('date_debut'):
        date_debut = datetime.strptime(request.GET.get('date_debut'), '%Y-%m-%d').date()
    if request.GET.get('date_fin'):
        date_fin = datetime.strptime(request.GET.get('date_fin'), '%Y-%m-%d').date()
    
    # Filtre par catégorie
    categorie_id = request.GET.get('categorie')
    categorie = None
    if categorie_id:
        categorie = get_object_or_404(Category, id=categorie_id)
    
    # === STATISTIQUES DÉPENSES ===
    depenses_periode = Depense.objects.filter(
        date_depense__gte=date_debut,
        date_depense__lte=date_fin
    )
    
    # Total des dépenses
    total_depenses = depenses_periode.aggregate(
        total=Sum('montant')
    )['total'] or 0
    
    # Dépenses par type avec pourcentages
    depenses_par_type = depenses_periode.values(
        'type_depense__nom', 'type_depense__couleur'
    ).annotate(
        total=Sum('montant'),
        nombre=models.Count('id')
    ).order_by('-total')
    
    # Calculer les pourcentages côté serveur
    for depense_type in depenses_par_type:
        if total_depenses > 0:
            depense_type['pourcentage'] = (depense_type['total'] / total_depenses) * 100
        else:
            depense_type['pourcentage'] = 0
    
    # === STATISTIQUES MOUVEMENTS ===
    mouvements_periode = MouvementStock.objects.filter(
        date_mouvement__date__gte=date_debut,
        date_mouvement__date__lte=date_fin
    )
    
    # Mouvements par type
    mouvements_par_type = mouvements_periode.values(
        'type_mouvement'
    ).annotate(
        nombre=models.Count('id'),
        quantite_totale=Sum('quantite')
    )
    
    # Coût total des approvisionnements
    cout_approvisionnements = mouvements_periode.filter(
        type_mouvement=TypeMouvement.ENTREE,
        cout_total__isnull=False
    ).aggregate(
        total=Sum('cout_total')
    )['total'] or 0
    
    # === DERNIÈRES ACTIVITÉS ===
    dernieres_depenses = Depense.objects.order_by('-created_at')[:10]
    derniers_mouvements = MouvementStock.objects.select_related(
        'produit', 'reference_commande', 'reference_depense'
    ).order_by('-date_mouvement')[:10]
    
    # === PRODUITS À RÉAPPROVISIONNER ===
    # Produits avec stock faible (moins de 5 unités)
    produits_stock_faible = Product.objects.filter(
        active=True, qty__lt=LOW_STOCK_THRESHOLD, qty__gt=0
    ).order_by('qty')[:10]
    
    # Produits en rupture
    produits_rupture = Product.objects.filter(
        active=True, qty=0
    ).order_by('-value')[:10]
    
    context = {
        'total_depenses': total_depenses,
        'depenses_par_type': depenses_par_type,
        'mouvements_par_type': mouvements_par_type,
        'cout_approvisionnements': cout_approvisionnements,
        'dernieres_depenses': dernieres_depenses,
        'derniers_mouvements': derniers_mouvements,
        'produits_stock_faible': produits_stock_faible,
        'produits_rupture': produits_rupture,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'categorie': categorie,
        'categories': Category.objects.all(),
    }
    
    return render(request, 'aprovision/dashboard.html', context)


@login_required
def approvisionnement_view(request):
    """Vue pour créer un approvisionnement"""
    # Cette vue est maintenant remplacée par la vue quick_stock_update dans product
    return redirect('product:quick_stock', pk=1)  # Rediriger vers la gestion des produits


@login_required
def nouvelle_depense_view(request):
    """Page dédiée pour créer une nouvelle dépense"""
    if request.method == 'POST':
        # Récupérer les données du formulaire
        montant = request.POST.get('montant')
        type_depense_id = request.POST.get('type_depense')
        description = request.POST.get('description', '')
        date_depense = request.POST.get('date_depense')
        fournisseur = request.POST.get('fournisseur', '')
        reference = request.POST.get('reference', '')
        
        # Validation
        if not montant or not type_depense_id:
            messages.error(request, 'Le montant et le type de dépense sont obligatoires.')
            return render(request, 'aprovision/nouvelle_depense.html', {
                'types_depense': TypeDepense.objects.filter(actif=True)
            })
        
        try:
            montant = float(montant)
            type_depense = TypeDepense.objects.get(id=type_depense_id)
            
            # Créer la dépense
            depense = Depense.objects.create(
                montant=montant,
                type_depense=type_depense,
                description=description,
                date_depense=date_depense or timezone.now().date(),
                fournisseur=fournisseur,
                reference=reference,
                created_by=request.user
            )
            
            messages.success(request, f'Dépense de {montant} GMD enregistrée avec succès.')
            return redirect('aprovision:dashboard')
            
        except (ValueError, TypeDepense.DoesNotExist):
            messages.error(request, 'Données invalides.')
    
    context = {
        'types_depense': TypeDepense.objects.filter(actif=True)
    }
    
    return render(request, 'aprovision/nouvelle_depense.html', context)


@login_required
def ajax_depense_rapide(request):
    """AJAX - Créer une dépense rapidement"""
    if request.method == 'POST':
        try:
            # Récupérer les données JSON
            data = json.loads(request.body)
            montant = data.get('montant')
            type_depense_id = data.get('type_depense_id')
            description = data.get('description', '')
            fournisseur = data.get('fournisseur', '')
            reference = data.get('reference', '')
            
            # Validation
            if not montant or not type_depense_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Le montant et le type de dépense sont obligatoires'
                })
            
            try:
                montant = float(montant)
                type_depense = TypeDepense.objects.get(id=type_depense_id)
                
                # Créer la dépense
                depense = Depense.objects.create(
                    montant=montant,
                    type_depense=type_depense,
                    description=description,
                    fournisseur=fournisseur,
                    reference=reference,
                    created_by=request.user
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Dépense de {montant} GMD enregistrée avec succès',
                    'depense': {
                        'id': depense.id,
                        'montant': depense.montant,
                        'type': depense.type_depense.nom,
                        'date': depense.date_depense.strftime('%d/%m/%Y')
                    }
                })
                
            except (ValueError, TypeDepense.DoesNotExist):
                return JsonResponse({
                    'success': False,
                    'error': 'Données invalides'
                })
                
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Format JSON invalide'
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
def ajax_recherche_produits(request):
    """AJAX - Rechercher des produits pour l'approvisionnement"""
    if request.method == 'GET':
        search = request.GET.get('search', '').strip()
        
        if len(search) < 2:
            return JsonResponse({'success': True, 'produits': []})
        
        produits = Product.objects.filter(
            Q(title__icontains=search) |
            Q(category__title__icontains=search),
            active=True
        )[:10]
        
        produits_data = []
        for produit in produits:
            produits_data.append({
                'id': produit.id,
                'title': produit.title,
                'category': produit.category.title if produit.category else '',
                'qty': produit.qty,
                'prix_achat': float(produit.prix_achat) if produit.prix_achat else 0,
                'display': f"{produit.title} ({produit.category.title if produit.category else 'Sans catégorie'})"
            })
        
        return JsonResponse({'success': True, 'produits': produits_data})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
def ajax_get_types_depense(request):
    """AJAX - Récupérer les types de dépenses actifs"""
    if request.method == 'GET':
        types = TypeDepense.objects.filter(actif=True)
        types_data = []
        
        for type_depense in types:
            types_data.append({
                'id': type_depense.id,
                'nom': type_depense.nom,
                'couleur': type_depense.couleur
            })
        
        return JsonResponse({'success': True, 'types': types_data})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
def ajax_get_dashboard_stats(request):
    """AJAX - Récupérer les statistiques du dashboard"""
    if request.method == 'GET':
        # Période par défaut : 30 derniers jours
        today = timezone.now().date()
        date_debut = today - timedelta(days=30)
        date_fin = today
        
        # Filtres depuis la requête
        if request.GET.get('date_debut'):
            date_debut = datetime.strptime(request.GET.get('date_debut'), '%Y-%m-%d').date()
        if request.GET.get('date_fin'):
            date_fin = datetime.strptime(request.GET.get('date_fin'), '%Y-%m-%d').date()
        
        # Statistiques
        total_depenses = Depense.objects.filter(
            date_depense__gte=date_debut,
            date_depense__lte=date_fin
        ).aggregate(total=Sum('montant'))['total'] or 0
        
        total_mouvements = MouvementStock.objects.filter(
            date_mouvement__date__gte=date_debut,
            date_mouvement__date__lte=date_fin
        ).count()
        
        cout_approvisionnements = MouvementStock.objects.filter(
            date_mouvement__date__gte=date_debut,
            date_mouvement__date__lte=date_fin,
            type_mouvement=TypeMouvement.ENTREE,
            cout_total__isnull=False
        ).aggregate(total=Sum('cout_total'))['total'] or 0
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_depenses': total_depenses,
                'total_mouvements': total_mouvements,
                'cout_approvisionnements': cout_approvisionnements,
                'date_debut': date_debut.strftime('%Y-%m-%d'),
                'date_fin': date_fin.strftime('%Y-%m-%d')
            }
        })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
def analytics_dashboard(request):
    """Dashboard analytique avancé avec filtres dynamiques"""
    
    # Période par défaut : mois en cours
    today = timezone.now().date()
    date_debut = today.replace(day=1)  # Premier jour du mois
    date_fin = today
    
    # Filtres depuis la requête
    if request.GET.get('date_debut'):
        date_debut = datetime.strptime(request.GET.get('date_debut'), '%Y-%m-%d').date()
    if request.GET.get('date_fin'):
        date_fin = datetime.strptime(request.GET.get('date_fin'), '%Y-%m-%d').date()
    
    # Filtre par catégorie
    categorie_id = request.GET.get('categorie')
    categorie = None
    if categorie_id:
        categorie = get_object_or_404(Category, id=categorie_id)
    
    # === STATISTIQUES DÉPENSES ===
    depenses_periode = Depense.objects.filter(
        date_depense__gte=date_debut,
        date_depense__lte=date_fin
    )
    
    # Filtrer par catégorie si sélectionnée
    if categorie:
        # Pour les dépenses, on ne peut pas filtrer par catégorie directement
        # car les dépenses ne sont pas liées aux produits
        pass
    
    total_depenses = depenses_periode.aggregate(
        total=Sum('montant')
    )['total'] or 0
    
    # Dépenses par type
    depenses_par_type = depenses_periode.values(
        'type_depense__nom', 'type_depense__couleur'
    ).annotate(
        total=Sum('montant'),
        nombre=Count('id')
    ).order_by('-total')
    
    # === STATISTIQUES DE VENTE ===
    # Commandes de la période (avec des produits vendus)
    commandes_periode = Order.objects.filter(
        date__gte=date_debut,
        date__lte=date_fin,
        order_items__isnull=False  # Commandes avec des produits
    ).distinct()
    
    # Filtrer par catégorie si sélectionnée
    if categorie:
        # Filtrer les commandes par les produits de la catégorie sélectionnée
        commandes_periode = commandes_periode.filter(
            order_items__product__category=categorie
        ).distinct()
    
    # Total des ventes en argent (toutes les commandes avec des produits)
    total_ventes_argent = commandes_periode.aggregate(
        total=Sum('final_value')
    )['total'] or 0
    
    # Nombre de commandes
    total_ventes_nombre_commandes = commandes_periode.count()
    
    # Nombre total de produits vendus
    total_ventes_nombre_produits = OrderItem.objects.filter(
        order__in=commandes_periode
    ).aggregate(
        total=Sum('qty')
    )['total'] or 0
    
    # Panier moyen (total ventes / nombre commandes)
    panier_moyen = 0
    if total_ventes_nombre_commandes > 0:
        panier_moyen = total_ventes_argent / total_ventes_nombre_commandes
    
    # Marge bénéficiaire (revenus - dépenses)
    marge_beneficiaire = total_ventes_argent - total_depenses
    
    # === BÉNÉFICE (VENTES - COÛT DES PRODUITS VENDUS) ===
    # Calculer le coût total des produits vendus (basé sur prix_achat)
    cout_produits_vendus = OrderItem.objects.filter(
        order__in=commandes_periode
    ).aggregate(
        total=Sum(models.F('qty') * models.F('product__prix_achat'))
    )['total'] or 0
    
    benefice = total_ventes_argent - cout_produits_vendus
    
    # === RESTE À PAYER (DETTES) ===
    # Commandes non payées de la période
    commandes_impayees = Order.objects.filter(
        date__gte=date_debut,
        date__lte=date_fin,
        is_paid=False  # Seulement les commandes non payées
    )
    
    # Filtrer par catégorie si sélectionnée
    if categorie:
        commandes_impayees = commandes_impayees.filter(
            order_items__product__category=categorie
        ).distinct()
    
    # Total des dettes (en tenant compte des paiements partiels)
    reste_a_payer = sum(
        commande.remaining_amount()
        for commande in commandes_impayees
    )
    
    # === MOUVEMENTS DE STOCK ===
    mouvements_periode = MouvementStock.objects.filter(
        date_mouvement__date__gte=date_debut,
        date_mouvement__date__lte=date_fin
    )
    
    # Filtrer par catégorie si sélectionnée
    if categorie:
        mouvements_periode = mouvements_periode.filter(
            produit__category=categorie
        )
    
    # Mouvements par type
    mouvements_par_type = mouvements_periode.values(
        'type_mouvement'
    ).annotate(
        nombre=Count('id'),
        quantite_totale=Sum('quantite')
    )
    
    # === TOP PRODUITS ===
    # Produits les plus vendus
    top_produits_ventes = OrderItem.objects.filter(
        order__in=commandes_periode
    ).values(
        'product__title', 'product__category__title'
    ).annotate(
        total_qty=Sum('qty'),
        total_revenue=Sum('total_price')
    ).order_by('-total_qty')[:5]
    
    # Produits avec le plus de mouvements
    produits_qs = Product.objects.filter(
        mouvements__date_mouvement__date__gte=date_debut,
        mouvements__date_mouvement__date__lte=date_fin
    )
    
    if categorie:
        produits_qs = produits_qs.filter(category=categorie)
    
    top_produits_mouvements = produits_qs.annotate(
        total_mouvements=Count('mouvements'),
        total_quantite=Sum('mouvements__quantite')
    ).order_by('-total_mouvements')[:5]
    
    # === ÉVOLUTION DES VENTES ===
    # Données pour le graphique d'évolution des ventes
    ventes_par_jour = Order.objects.filter(
        date__gte=date_debut,
        date__lte=date_fin,
        order_items__isnull=False
    ).values('date').annotate(
        total_ventes=Sum('final_value'),
        nombre_commandes=Count('id')
    ).order_by('date')
    
    # Filtrer par catégorie si sélectionnée
    if categorie:
        ventes_par_jour = ventes_par_jour.filter(
            order_items__product__category=categorie
        )
    
    # Préparer les données pour Chart.js
    chart_data = {
        'labels': [vente['date'].strftime('%d/%m') for vente in ventes_par_jour],
        'datasets': [{
            'label': 'Ventes (GMD)',
            'data': [float(vente['total_ventes']) for vente in ventes_par_jour],
            'borderColor': 'rgb(75, 192, 192)',
            'backgroundColor': 'rgba(75, 192, 192, 0.2)',
            'tension': 0.1
        }]
    }
    
    context = {
        # === PÉRIODE ET FILTRES ===
        'date_debut': date_debut,
        'date_fin': date_fin,
        'categorie': categorie,
        'categories': Category.objects.all(),
        
        # === STATISTIQUES DÉPENSES ===
        'total_depenses': total_depenses,
        'depenses_par_type': depenses_par_type,
        
        # === STATISTIQUES VENTES ===
        'total_ventes_argent': total_ventes_argent,
        'total_ventes_nombre_commandes': total_ventes_nombre_commandes,
        'total_ventes_nombre_produits': total_ventes_nombre_produits,
        'panier_moyen': panier_moyen,
        'marge_beneficiaire': marge_beneficiaire,
        'benefice': benefice,
        'reste_a_payer': reste_a_payer,
        
        # === MOUVEMENTS ===
        'mouvements_par_type': mouvements_par_type,
        
        # === TOP PRODUITS ===
        'top_produits_ventes': top_produits_ventes,
        'top_produits_mouvements': top_produits_mouvements,
        
        # === GRAPHIQUE ===
        'chart_data': chart_data,
    }
    
    return render(request, 'aprovision/analytics_dashboard.html', context)


@login_required
def ajax_analytics_data(request):
    """Endpoint AJAX pour les données analytiques dynamiques"""
    if request.method == 'GET':
        # Période
        date_debut = datetime.strptime(request.GET.get('date_debut'), '%Y-%m-%d').date()
        date_fin = datetime.strptime(request.GET.get('date_fin'), '%Y-%m-%d').date()
        
        # Filtre par catégorie
        categorie_id = request.GET.get('categorie')
        categorie = None
        if categorie_id:
            categorie = get_object_or_404(Category, id=categorie_id)
        
        # === STATISTIQUES DÉPENSES ===
        depenses_periode = Depense.objects.filter(
            date_depense__gte=date_debut,
            date_depense__lte=date_fin
        )
        
        total_depenses = depenses_periode.aggregate(
            total=Sum('montant')
        )['total'] or 0
        
        # === STATISTIQUES VENTES ===
        commandes_periode = Order.objects.filter(
            date__gte=date_debut,
            date__lte=date_fin,
            order_items__isnull=False
        ).distinct()
        
        if categorie:
            commandes_periode = commandes_periode.filter(
                order_items__product__category=categorie
            ).distinct()
        
        total_ventes_argent = commandes_periode.aggregate(
            total=Sum('final_value')
        )['total'] or 0
        
        total_ventes_nombre_commandes = commandes_periode.count()
        
        total_ventes_nombre_produits = OrderItem.objects.filter(
            order__in=commandes_periode
        ).aggregate(
            total=Sum('qty')
        )['total'] or 0
        
        panier_moyen = 0
        if total_ventes_nombre_commandes > 0:
            panier_moyen = total_ventes_argent / total_ventes_nombre_commandes
        
        marge_beneficiaire = total_ventes_argent - total_depenses
        
        # === BÉNÉFICE ===
        cout_produits_vendus = OrderItem.objects.filter(
            order__in=commandes_periode
        ).aggregate(
            total=Sum(models.F('qty') * models.F('product__prix_achat'))
        )['total'] or 0
        
        benefice = total_ventes_argent - cout_produits_vendus
        
        # === RESTE À PAYER ===
        commandes_impayees = Order.objects.filter(
            date__gte=date_debut,
            date__lte=date_fin,
            is_paid=False
        )
        
        if categorie:
            commandes_impayees = commandes_impayees.filter(
                order_items__product__category=categorie
            ).distinct()
        
        reste_a_payer = sum(
            commande.remaining_amount()
            for commande in commandes_impayees
        )
        
        # === ÉVOLUTION DES VENTES ===
        ventes_par_jour = Order.objects.filter(
            date__gte=date_debut,
            date__lte=date_fin,
            order_items__isnull=False
        ).values('date').annotate(
            total_ventes=Sum('final_value'),
            nombre_commandes=Count('id')
        ).order_by('date')
        
        if categorie:
            ventes_par_jour = ventes_par_jour.filter(
                order_items__product__category=categorie
            )
        
        chart_data = {
            'labels': [vente['date'].strftime('%d/%m') for vente in ventes_par_jour],
            'datasets': [{
                'label': 'Ventes (GMD)',
                'data': [float(vente['total_ventes']) for vente in ventes_par_jour],
                'borderColor': 'rgb(75, 192, 192)',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                'tension': 0.1
            }]
        }
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_depenses': total_depenses,
                'total_ventes_argent': total_ventes_argent,
                'total_ventes_nombre_commandes': total_ventes_nombre_commandes,
                'total_ventes_nombre_produits': total_ventes_nombre_produits,
                'panier_moyen': panier_moyen,
                'marge_beneficiaire': marge_beneficiaire,
                'benefice': benefice,
                'reste_a_payer': reste_a_payer,
            },
            'chart_data': chart_data
        })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
def ajax_create_type_depense(request):
    """Vue AJAX pour créer un nouveau type de dépense"""
    if request.method == 'POST':
        try:
            # Récupérer les données JSON
            data = json.loads(request.body)
            nom = data.get('nom', '').strip()
            couleur = data.get('couleur', '#007bff')
            description = data.get('description', '')
            
            # Validation
            if not nom:
                return JsonResponse({
                    'success': False,
                    'error': 'Le nom du type de dépense est obligatoire'
                })
            
            # Vérifier si le type existe déjà
            if TypeDepense.objects.filter(nom__iexact=nom).exists():
                return JsonResponse({
                    'success': False,
                    'error': f'Un type de dépense "{nom}" existe déjà'
                })
            
            # Créer le type de dépense
            type_depense = TypeDepense.objects.create(
                nom=nom,
                couleur=couleur,
                description=description,
                actif=True
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Type de dépense "{nom}" créé avec succès',
                'type_depense': {
                    'id': type_depense.id,
                    'nom': type_depense.nom,
                    'couleur': type_depense.couleur
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Format JSON invalide'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


class MouvementListView(ListView):
    """Liste des mouvements de stock"""
    model = MouvementStock
    template_name = 'aprovision/mouvement_list.html'
    context_object_name = 'mouvements'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = MouvementStock.objects.select_related(
            'produit', 'reference_commande', 'reference_depense'
        ).order_by('-date_mouvement')
        
        # Filtres
        type_mouvement = self.request.GET.get('type_mouvement')
        if type_mouvement:
            queryset = queryset.filter(type_mouvement=type_mouvement)
        
        produit_id = self.request.GET.get('produit')
        if produit_id:
            queryset = queryset.filter(produit_id=produit_id)
        
        date_debut = self.request.GET.get('date_debut')
        if date_debut:
            queryset = queryset.filter(date_mouvement__date__gte=date_debut)
        
        date_fin = self.request.GET.get('date_fin')
        if date_fin:
            queryset = queryset.filter(date_mouvement__date__lte=date_fin)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types_mouvement'] = TypeMouvement.choices
        context['produits'] = Product.objects.filter(active=True)
        return context


class DepenseListView(ListView):
    """Liste des dépenses"""
    model = Depense
    template_name = 'aprovision/depense_list.html'
    context_object_name = 'depenses'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Depense.objects.select_related('type_depense').order_by('-date_depense')
        
        # Filtres
        type_depense_id = self.request.GET.get('type_depense')
        if type_depense_id:
            queryset = queryset.filter(type_depense_id=type_depense_id)
        
        date_debut = self.request.GET.get('date_debut')
        if date_debut:
            queryset = queryset.filter(date_depense__gte=date_debut)
        
        date_fin = self.request.GET.get('date_fin')
        if date_fin:
            queryset = queryset.filter(date_depense__lte=date_fin)
        
        montant_min = self.request.GET.get('montant_min')
        if montant_min:
            queryset = queryset.filter(montant__gte=montant_min)
        
        montant_max = self.request.GET.get('montant_max')
        if montant_max:
            queryset = queryset.filter(montant__lte=montant_max)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types_depense'] = TypeDepense.objects.filter(actif=True)
        return context