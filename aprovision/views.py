from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q, Count
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
import json
from django.db import models

from .models import (
    TypeDepense, Depense, MouvementStock, TypeMouvement, 
    Approvisionnement
)
from product.models import Product, Category, LOW_STOCK_THRESHOLD
from order.models import Order, OrderItem


@staff_member_required
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
        active=True, qty__lt=LOW_STOCK_THRESHOLD
    ).order_by('qty')[:10]
    
    # Filtrer par catégorie si spécifiée
    if categorie:
        produits_stock_faible = produits_stock_faible.filter(category=categorie)
    
    context = {
        'date_debut': date_debut,
        'date_fin': date_fin,
        'categorie': categorie,
        'categories': Category.objects.all(),
        'total_depenses': total_depenses,
        'depenses_par_type': depenses_par_type,
        'mouvements_par_type': mouvements_par_type,
        'cout_approvisionnements': cout_approvisionnements,
        'dernieres_depenses': dernieres_depenses,
        'derniers_mouvements': derniers_mouvements,
        'produits_stock_faible': produits_stock_faible,
    }
    
    return render(request, 'aprovision/dashboard.html', context)


@staff_member_required
def approvisionnement_view(request):
    """Vue pour créer un approvisionnement"""
    
    if request.method == 'POST':
        try:
            produit_id = request.POST.get('produit')
            quantite = int(request.POST.get('quantite', 0))
            prix_achat = float(request.POST.get('prix_achat', 0))
            description = request.POST.get('description', '')
            fournisseur = request.POST.get('fournisseur', '')
            reference = request.POST.get('reference', '')
            
            if quantite <= 0 or prix_achat <= 0:
                messages.error(request, 'La quantité et le prix d\'achat doivent être positifs')
                return redirect('aprovision:approvisionnement')
            
            produit = get_object_or_404(Product, id=produit_id)
            
            # Créer l'approvisionnement
            result = Approvisionnement.objects.create_approvisionnement(
                produit=produit,
                quantite=quantite,
                prix_achat_unitaire=prix_achat,
                description=description,
                fournisseur=fournisseur,
                reference=reference,
                user=request.user
            )
            
            messages.success(
                request, 
                f'Approvisionnement créé avec succès ! Stock de {produit.title} : '
                f'{result["mouvement"].stock_avant} → {result["mouvement"].stock_apres} unités'
            )
            
            return redirect('aprovision:dashboard')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création : {str(e)}')
    
    # GET - Afficher le formulaire
    produits = Product.objects.filter(active=True).order_by('title')
    
    context = {
        'produits': produits,
    }
    
    return render(request, 'aprovision/approvisionnement_form.html', context)


@staff_member_required
def ajax_depense_rapide(request):
    """AJAX - Créer une dépense rapidement"""
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            type_depense_id = data.get('type_depense')
            description = data.get('description', '').strip()
            montant = float(data.get('montant', 0))
            fournisseur = data.get('fournisseur', '').strip()
            reference = data.get('reference', '').strip()
            
            if not description or montant <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Description et montant sont obligatoires'
                })
            
            type_depense = get_object_or_404(TypeDepense, id=type_depense_id)
            
            depense = Depense.objects.create(
                type_depense=type_depense,
                description=description,
                montant=montant,
                fournisseur=fournisseur,
                reference=reference,
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Dépense de {montant} FCFA enregistrée avec succès',
                'depense': {
                    'id': depense.id,
                    'description': depense.description,
                    'montant': str(depense.montant),
                    'type': depense.type_depense.nom,
                    'date': depense.date_depense.strftime('%d/%m/%Y')
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erreur : {str(e)}'
            })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@staff_member_required
def ajax_recherche_produits(request):
    """AJAX - Rechercher des produits pour l'approvisionnement"""
    
    q = request.GET.get('q', '').strip()
    
    if len(q) < 2:
        return JsonResponse({'produits': []})
    
    produits = Product.objects.filter(
        active=True,
        title__icontains=q
    ).values('id', 'title', 'qty', 'final_value')[:10]
    
    return JsonResponse({
        'produits': list(produits)
    })


@staff_member_required
def ajax_get_types_depense(request):
    """AJAX - Récupérer les types de dépenses actifs"""
    
    types = TypeDepense.objects.filter(actif=True).values(
        'id', 'nom', 'description', 'couleur'
    ).order_by('nom')
    
    return JsonResponse({
        'types': list(types)
    })


@staff_member_required
def ajax_get_dashboard_stats(request):
    """AJAX - Récupérer les statistiques du dashboard"""
    
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    # Période par défaut : 30 derniers jours
    today = timezone.now().date()
    date_debut = today - timedelta(days=30)
    date_fin = today
    
    # Filtres de date depuis la requête
    if request.GET.get('date_debut'):
        date_debut = datetime.strptime(request.GET.get('date_debut'), '%Y-%m-%d').date()
    if request.GET.get('date_fin'):
        date_fin = datetime.strptime(request.GET.get('date_fin'), '%Y-%m-%d').date()
    
    # Dépenses de la période
    depenses_periode = Depense.objects.filter(
        date_depense__gte=date_debut,
        date_depense__lte=date_fin
    )
    
    total_depenses = depenses_periode.aggregate(
        total=Sum('montant')
    )['total'] or 0
    
    # Dépenses par type
    depenses_par_type = depenses_periode.values(
        'type_depense__nom', 'type_depense__couleur'
    ).annotate(
        total=Sum('montant'),
        nombre=models.Count('id')
    ).order_by('-total')
    
    # Calculer les pourcentages
    for depense_type in depenses_par_type:
        if total_depenses > 0:
            depense_type['pourcentage'] = (depense_type['total'] / total_depenses) * 100
        else:
            depense_type['pourcentage'] = 0
    
    # Mouvements récents
    recent_movements = MouvementStock.objects.select_related(
        'produit'
    ).order_by('-date_mouvement')[:5]
    
    movements_data = []
    for mouvement in recent_movements:
        movements_data.append({
            'produit': mouvement.produit.title,
            'type': mouvement.get_type_mouvement_display(),
            'quantite': mouvement.quantite,
            'date': mouvement.date_mouvement.strftime('%d/%m %H:%M'),
            'icone': mouvement.get_icone(),
            'couleur': mouvement.get_couleur_badge()
        })
    
    return JsonResponse({
        'total_depenses': float(total_depenses),
        'depenses_par_type': list(depenses_par_type),
        'recent_movements': movements_data,
        'periode': {
            'debut': date_debut.strftime('%d/%m/%Y'),
            'fin': date_fin.strftime('%d/%m/%Y')
        }
    })


@staff_member_required
def analytics_dashboard(request):
    """Dashboard analytique avancé avec filtres dynamiques"""
    
    # === FILTRES ===
    # Période par défaut : 30 derniers jours
    today = timezone.now().date()
    date_debut = today - timedelta(days=30)
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
    
    # === QUERYSETS FILTRÉS ===
    # Dépenses filtrées
    depenses_qs = Depense.objects.filter(
        date_depense__gte=date_debut,
        date_depense__lte=date_fin
    )
    
    # Mouvements filtrés
    mouvements_qs = MouvementStock.objects.filter(
        date_mouvement__date__gte=date_debut,
        date_mouvement__date__lte=date_fin
    )
    
    # Produits filtrés par catégorie
    produits_qs = Product.objects.filter(active=True)
    if categorie:
        produits_qs = produits_qs.filter(category=categorie)
        # Filtrer les mouvements par les produits de cette catégorie
        mouvements_qs = mouvements_qs.filter(produit__in=produits_qs)
    
    # === STATISTIQUES GÉNÉRALES ===
    total_depenses = depenses_qs.aggregate(total=Sum('montant'))['total'] or 0
    total_approvisionnements = mouvements_qs.filter(
        type_mouvement=TypeMouvement.ENTREE
    ).aggregate(total=Sum('cout_total'))['total'] or 0
    
    # === STATISTIQUES DE VENTE ===
    # Commandes de la période
    commandes_periode = Order.objects.filter(
        date__gte=date_debut,
        date__lte=date_fin,
        is_paid=True  # Seulement les commandes payées
    )
    
    # Filtrer par catégorie si sélectionnée
    if categorie:
        # Filtrer les commandes par les produits de la catégorie sélectionnée
        commandes_periode = commandes_periode.filter(
            order_items__product__category=categorie
        ).distinct()
    
    # Total des ventes en argent
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
    
    # Marge bénéficiaire (revenus - dépenses)
    marge_beneficiaire = total_ventes_argent - total_depenses
    
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
    
    # Total des dettes
    reste_a_payer = commandes_impayees.aggregate(
        total=Sum('final_value')
    )['total'] or 0
    
    # Mouvements par type
    mouvements_par_type = mouvements_qs.values('type_mouvement').annotate(
        nombre=Count('id'),
        quantite_totale=Sum('quantite')
    ).order_by('type_mouvement')
    
    # === STATISTIQUES PAR CATÉGORIE ===
    if not categorie:
        # Statistiques par catégorie (simplifiées)
        stats_par_categorie = Category.objects.annotate(
            nombre_produits=Count('product'),
            stock_total=Sum('product__qty'),
            valeur_stock=Sum(models.F('product__qty') * models.F('product__prix_achat'))
        ).filter(nombre_produits__gt=0)
        
        # Ajouter les statistiques de mouvements manuellement
        for stat in stats_par_categorie:
            produits_categorie = Product.objects.filter(category=stat)
            stat.mouvements_entree = MouvementStock.objects.filter(
                produit__in=produits_categorie,
                type_mouvement=TypeMouvement.ENTREE
            ).count()
            stat.mouvements_sortie = MouvementStock.objects.filter(
                produit__in=produits_categorie,
                type_mouvement__in=[TypeMouvement.SORTIE_VENTE, TypeMouvement.SORTIE_PERTE]
            ).count()
    else:
        stats_par_categorie = None
    
    # === ÉVOLUTION TEMPORELLE ===
    # Dépenses par jour
    depenses_par_jour = depenses_qs.values('date_depense').annotate(
        total=Sum('montant')
    ).order_by('date_depense')
    
    # Mouvements par jour
    mouvements_par_jour = mouvements_qs.values('date_mouvement__date').annotate(
        entree=Sum('quantite', filter=Q(type_mouvement=TypeMouvement.ENTREE)),
        sortie=Sum('quantite', filter=Q(type_mouvement__in=[TypeMouvement.SORTIE_VENTE, TypeMouvement.SORTIE_PERTE]))
    ).order_by('date_mouvement__date')
    
    # === TOP PRODUITS ===
    # Produits avec le plus de mouvements
    top_produits_mouvements = produits_qs.annotate(
        total_mouvements=Count('mouvements'),
        total_entrees=Sum('mouvements__quantite', filter=Q(mouvements__type_mouvement=TypeMouvement.ENTREE)),
        total_sorties=Sum('mouvements__quantite', filter=Q(mouvements__type_mouvement__in=[TypeMouvement.SORTIE_VENTE, TypeMouvement.SORTIE_PERTE]))
    ).filter(total_mouvements__gt=0).order_by('-total_mouvements')[:10]
    
    # Produits avec stock faible
    produits_stock_faible = produits_qs.filter(qty__lt=LOW_STOCK_THRESHOLD).order_by('qty')[:10]
    
    # === DÉPENSES PAR TYPE ===
    depenses_par_type = depenses_qs.values(
        'type_depense__nom', 'type_depense__couleur'
    ).annotate(
        total=Sum('montant'),
        nombre=Count('id')
    ).order_by('-total')
    
    # Calculer les pourcentages
    for depense_type in depenses_par_type:
        if total_depenses > 0:
            depense_type['pourcentage'] = (depense_type['total'] / total_depenses) * 100
        else:
            depense_type['pourcentage'] = 0
    
    # === CONTEXTE ===
    context = {
        'date_debut': date_debut,
        'date_fin': date_fin,
        'categorie': categorie,
        'categories': Category.objects.all(),
        'total_depenses': total_depenses,
        'total_approvisionnements': total_approvisionnements,
        'total_ventes_argent': total_ventes_argent,
        'total_ventes_nombre_commandes': total_ventes_nombre_commandes,
        'total_ventes_nombre_produits': total_ventes_nombre_produits,
        'marge_beneficiaire': marge_beneficiaire,
        'reste_a_payer': reste_a_payer,
        'mouvements_par_type': mouvements_par_type,
        'stats_par_categorie': stats_par_categorie,
        'depenses_par_jour': list(depenses_par_jour),
        'mouvements_par_jour': list(mouvements_par_jour),
        'top_produits_mouvements': top_produits_mouvements,
        'produits_stock_faible': produits_stock_faible,
        'depenses_par_type': depenses_par_type,
        'mouvements_par_type': mouvements_par_type,
    }
    
    return render(request, 'aprovision/analytics_dashboard.html', context)


@staff_member_required
def ajax_analytics_data(request):
    """Endpoint AJAX pour les données analytiques dynamiques"""
    
    # Récupérer les paramètres
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    categorie_id = request.GET.get('categorie')
    
    if date_debut:
        date_debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
    else:
        date_debut = timezone.now().date() - timedelta(days=30)
    
    if date_fin:
        date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
    else:
        date_fin = timezone.now().date()
    
    # Filtrer les données
    depenses_qs = Depense.objects.filter(
        date_depense__gte=date_debut,
        date_depense__lte=date_fin
    )
    
    mouvements_qs = MouvementStock.objects.filter(
        date_mouvement__date__gte=date_debut,
        date_mouvement__date__lte=date_fin
    )
    
    if categorie_id:
        categorie = get_object_or_404(Category, id=categorie_id)
        produits_qs = Product.objects.filter(category=categorie, active=True)
        mouvements_qs = mouvements_qs.filter(produit__in=produits_qs)
    
    # Calculer les statistiques
    total_depenses = depenses_qs.aggregate(total=Sum('montant'))['total'] or 0
    total_approvisionnements = mouvements_qs.filter(
        type_mouvement=TypeMouvement.ENTREE
    ).aggregate(total=Sum('cout_total'))['total'] or 0
    
    # === STATISTIQUES DE VENTE ===
    # Commandes de la période
    commandes_periode = Order.objects.filter(
        date__gte=date_debut,
        date__lte=date_fin,
        is_paid=True  # Seulement les commandes payées
    )
    
    # Filtrer par catégorie si sélectionnée
    if categorie_id:
        commandes_periode = commandes_periode.filter(
            order_items__product__category_id=categorie_id
        ).distinct()
    
    # Total des ventes en argent
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
    
    # Marge bénéficiaire (revenus - dépenses)
    marge_beneficiaire = total_ventes_argent - total_depenses
    
    # === RESTE À PAYER (DETTES) ===
    # Commandes non payées de la période
    commandes_impayees = Order.objects.filter(
        date__gte=date_debut,
        date__lte=date_fin,
        is_paid=False  # Seulement les commandes non payées
    )
    
    # Filtrer par catégorie si sélectionnée
    if categorie_id:
        commandes_impayees = commandes_impayees.filter(
            order_items__product__category_id=categorie_id
        ).distinct()
    
    # Total des dettes
    reste_a_payer = commandes_impayees.aggregate(
        total=Sum('final_value')
    )['total'] or 0
    
    # Dépenses par jour pour le graphique
    depenses_par_jour = list(depenses_qs.values('date_depense').annotate(
        total=Sum('montant')
    ).order_by('date_depense'))
    
    # Mouvements par jour pour le graphique
    mouvements_par_jour = list(mouvements_qs.values('date_mouvement__date').annotate(
        entree=Sum('quantite', filter=Q(type_mouvement=TypeMouvement.ENTREE)),
        sortie=Sum('quantite', filter=Q(type_mouvement__in=[TypeMouvement.SORTIE_VENTE, TypeMouvement.SORTIE_PERTE]))
    ).order_by('date_mouvement__date'))
    
    return JsonResponse({
        'total_depenses': total_depenses,
        'total_approvisionnements': total_approvisionnements,
        'total_ventes_argent': total_ventes_argent,
        'total_ventes_nombre_commandes': total_ventes_nombre_commandes,
        'total_ventes_nombre_produits': total_ventes_nombre_produits,
        'marge_beneficiaire': marge_beneficiaire,
        'reste_a_payer': reste_a_payer,
        'depenses_par_jour': depenses_par_jour,
        'mouvements_par_jour': mouvements_par_jour,
    })


@method_decorator(staff_member_required, name='dispatch')
class MouvementListView(ListView):
    """Liste des mouvements de stock"""
    model = MouvementStock
    template_name = 'aprovision/mouvement_list.html'
    context_object_name = 'mouvements'
    paginate_by = 50
    
    def get_queryset(self):
        qs = MouvementStock.objects.select_related(
            'produit', 'produit__category', 'reference_commande', 
            'reference_depense', 'created_by'
        ).order_by('-date_mouvement')
        
        # Filtres
        produit_id = self.request.GET.get('produit')
        type_mouvement = self.request.GET.get('type_mouvement')
        date_debut = self.request.GET.get('date_debut')
        date_fin = self.request.GET.get('date_fin')
        
        if produit_id:
            qs = qs.filter(produit_id=produit_id)
        
        if type_mouvement:
            qs = qs.filter(type_mouvement=type_mouvement)
        
        if date_debut:
            try:
                date_debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
                qs = qs.filter(date_mouvement__date__gte=date_debut)
            except:
                pass
        
        if date_fin:
            try:
                date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
                qs = qs.filter(date_mouvement__date__lte=date_fin)
            except:
                pass
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['produits'] = Product.objects.filter(active=True).order_by('title')
        context['types_mouvement'] = TypeMouvement.choices
        return context


@method_decorator(staff_member_required, name='dispatch')
class DepenseListView(ListView):
    """Liste des dépenses"""
    model = Depense
    template_name = 'aprovision/depense_list.html'
    context_object_name = 'depenses'
    paginate_by = 50
    
    def get_queryset(self):
        qs = Depense.objects.select_related(
            'type_depense', 'created_by'
        ).order_by('-date_depense', '-created_at')
        
        # Filtres
        type_depense_id = self.request.GET.get('type_depense')
        date_debut = self.request.GET.get('date_debut')
        date_fin = self.request.GET.get('date_fin')
        
        if type_depense_id:
            qs = qs.filter(type_depense_id=type_depense_id)
        
        if date_debut:
            try:
                date_debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
                qs = qs.filter(date_depense__gte=date_debut)
            except:
                pass
        
        if date_fin:
            try:
                date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
                qs = qs.filter(date_depense__lte=date_fin)
            except:
                pass
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['types_depense'] = TypeDepense.objects.filter(actif=True)
        
        # Calcul du total des dépenses affichées
        total_depenses = self.get_queryset().aggregate(
            total=Sum('montant')
        )['total'] or 0
        context['total_depenses'] = total_depenses
        
        return context