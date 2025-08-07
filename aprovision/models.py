from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

CURRENCY = settings.CURRENCY


class TypeDepense(models.Model):
    """Types de dépenses pour catégoriser les dépenses"""
    nom = models.CharField(max_length=100, unique=True, help_text="Ex: Approvisionnement, Matériel, Main d'œuvre")
    description = models.TextField(blank=True, help_text="Description du type de dépense")
    couleur = models.CharField(max_length=7, default="#007bff", help_text="Couleur hex pour l'affichage")
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Type de Dépense"
        verbose_name_plural = "Types de Dépenses"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Depense(models.Model):
    """Enregistrement des dépenses du commerce"""
    type_depense = models.ForeignKey(TypeDepense, on_delete=models.PROTECT, related_name='depenses')
    description = models.CharField(max_length=200, help_text="Description de la dépense")
    montant = models.DecimalField(max_digits=10, decimal_places=2, help_text="Montant de la dépense")
    date_depense = models.DateField(default=timezone.now, help_text="Date de la dépense")
    
    # Champs optionnels
    fournisseur = models.CharField(max_length=150, blank=True, help_text="Nom du fournisseur (optionnel)")
    reference = models.CharField(max_length=50, blank=True, help_text="Numéro de facture ou référence")
    notes = models.TextField(blank=True, help_text="Notes additionnelles")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"
        ordering = ['-date_depense', '-created_at']

    def __str__(self):
        return f"{self.description} - {self.montant} {CURRENCY}"

    def tag_montant(self):
        return f"{self.montant} {CURRENCY}"
    tag_montant.short_description = "Montant"


class TypeMouvement(models.TextChoices):
    """Types de mouvements de stock"""
    ENTREE = 'ENTREE', 'Entrée (Approvisionnement)'
    SORTIE_VENTE = 'SORTIE_VENTE', 'Sortie (Vente)'
    SORTIE_PERTE = 'SORTIE_PERTE', 'Sortie (Perte/Casse)'
    AJUSTEMENT_PLUS = 'AJUSTEMENT_PLUS', 'Ajustement +'
    AJUSTEMENT_MOINS = 'AJUSTEMENT_MOINS', 'Ajustement -'


class MouvementStock(models.Model):
    """Traçabilité des mouvements de stock"""
    produit = models.ForeignKey('product.Product', on_delete=models.CASCADE, related_name='mouvements')
    type_mouvement = models.CharField(max_length=20, choices=TypeMouvement.choices)
    quantite = models.IntegerField(help_text="Quantité (positive pour entrée, négative pour sortie)")
    
    # Stock avant et après le mouvement
    stock_avant = models.PositiveIntegerField(help_text="Stock avant le mouvement")
    stock_apres = models.PositiveIntegerField(help_text="Stock après le mouvement")
    
    # Informations sur les prix (pour les entrées)
    prix_achat_unitaire = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                            help_text="Prix d'achat unitaire (pour les entrées)")
    cout_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                   help_text="Coût total du mouvement")
    
    # Références
    reference_commande = models.ForeignKey('order.Order', on_delete=models.SET_NULL, null=True, blank=True,
                                         help_text="Commande associée (pour les ventes)")
    reference_depense = models.ForeignKey(Depense, on_delete=models.SET_NULL, null=True, blank=True,
                                        help_text="Dépense associée (pour les approvisionnements)")
    
    # Métadonnées
    description = models.CharField(max_length=200, blank=True, help_text="Description du mouvement")
    date_mouvement = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Mouvement de Stock"
        verbose_name_plural = "Mouvements de Stock"
        ordering = ['-date_mouvement']

    def __str__(self):
        signe = "+" if self.quantite > 0 else ""
        return f"{self.produit.title} - {signe}{self.quantite} ({self.get_type_mouvement_display()})"

    def save(self, *args, **kwargs):
        # Calculer le coût total si prix d'achat fourni
        if self.prix_achat_unitaire and self.quantite:
            self.cout_total = Decimal(abs(self.quantite)) * self.prix_achat_unitaire
        super().save(*args, **kwargs)

    def get_couleur_badge(self):
        """Retourne la couleur du badge selon le type de mouvement"""
        couleurs = {
            'ENTREE': 'success',
            'SORTIE_VENTE': 'primary', 
            'SORTIE_PERTE': 'danger',
            'AJUSTEMENT_PLUS': 'info',
            'AJUSTEMENT_MOINS': 'warning'
        }
        return couleurs.get(self.type_mouvement, 'secondary')

    def get_icone(self):
        """Retourne l'icône Bootstrap selon le type de mouvement"""
        icones = {
            'ENTREE': 'bi-arrow-up-circle',
            'SORTIE_VENTE': 'bi-cart-check',
            'SORTIE_PERTE': 'bi-exclamation-triangle',
            'AJUSTEMENT_PLUS': 'bi-plus-circle',
            'AJUSTEMENT_MOINS': 'bi-dash-circle'
        }
        return icones.get(self.type_mouvement, 'bi-arrow-right-circle')


class ApprovisionnementManager(models.Manager):
    """Manager pour les approvisionnements"""
    
    def create_approvisionnement(self, produit, quantite, prix_achat_unitaire, 
                               description="", fournisseur="", reference="", user=None):
        """Créer un approvisionnement complet avec dépense et mouvement de stock"""
        from django.db import transaction
        
        with transaction.atomic():
            # 1. Créer la dépense
            type_appro, _ = TypeDepense.objects.get_or_create(
                nom="Approvisionnement",
                defaults={
                    'description': "Achat de marchandises pour le stock",
                    'couleur': "#28a745"
                }
            )
            
            cout_total = Decimal(quantite) * Decimal(prix_achat_unitaire)
            depense = Depense.objects.create(
                type_depense=type_appro,
                description=description or f"Approvisionnement {produit.title}",
                montant=cout_total,
                fournisseur=fournisseur,
                reference=reference,
                created_by=user
            )
            
            # 2. Sauvegarder l'ancien stock
            stock_avant = produit.qty
            
            # 3. Mettre à jour le stock du produit
            produit.qty += quantite
            produit.save()
            
            # 4. Créer le mouvement de stock
            mouvement = MouvementStock.objects.create(
                produit=produit,
                type_mouvement=TypeMouvement.ENTREE,
                quantite=quantite,
                stock_avant=stock_avant,
                stock_apres=produit.qty,
                prix_achat_unitaire=prix_achat_unitaire,
                cout_total=cout_total,
                reference_depense=depense,
                description=description or f"Approvisionnement de {quantite} unités",
                created_by=user
            )
            
            return {
                'depense': depense,
                'mouvement': mouvement,
                'produit': produit
            }


class Approvisionnement:
    """Classe utilitaire pour faciliter la gestion des approvisionnements"""
    
    objects = ApprovisionnementManager()