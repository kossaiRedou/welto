from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from order.models import Order, OrderItem
from .models import MouvementStock, TypeMouvement


@receiver(post_save, sender=OrderItem)
def tracer_vente_produit(sender, instance, created, **kwargs):
    """
    Signal pour tracer automatiquement les mouvements de stock lors des ventes
    """
    if created:
        # Nouvelle vente - créer un mouvement de sortie
        stock_avant = instance.product.qty + instance.qty  # Stock avant la vente
        
        MouvementStock.objects.create(
            produit=instance.product,
            type_mouvement=TypeMouvement.SORTIE_VENTE,
            quantite=-instance.qty,  # Négatif pour une sortie
            stock_avant=stock_avant,
            stock_apres=instance.product.qty,
            reference_commande=instance.order,
            description=f"Vente - Commande #{instance.order.id}",
            created_by=None  # Sera défini si on a accès au user dans le contexte
        )


@receiver(post_delete, sender=OrderItem)
def annuler_mouvement_vente(sender, instance, **kwargs):
    """
    Signal pour annuler le mouvement de stock si un item de commande est supprimé
    """
    # Restaurer le stock
    instance.product.qty += instance.qty
    instance.product.save()
    
    # Créer un mouvement d'ajustement pour tracer cette annulation
    MouvementStock.objects.create(
        produit=instance.product,
        type_mouvement=TypeMouvement.AJUSTEMENT_PLUS,
        quantite=instance.qty,
        stock_avant=instance.product.qty - instance.qty,
        stock_apres=instance.product.qty,
        description=f"Annulation vente - Commande #{instance.order.id}",
        created_by=None
    )


@receiver(post_save, sender=Order)
def tracer_statut_commande(sender, instance, created, **kwargs):
    """
    Signal pour tracer les changements de statut de paiement des commandes
    """
    if not created:
        # Commande existante modifiée
        # On pourrait ajouter ici une logique pour tracer les changements de statut
        # Par exemple, si is_paid change de False à True
        pass