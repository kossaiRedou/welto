from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """Modèle utilisateur personnalisé avec rôles"""
    
    ROLE_CHOICES = [
        ('manager', 'Manager'),
        ('employee', 'Employé'),
    ]
    
    # Champs personnalisés
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='employee',
        verbose_name='Rôle'
    )
    
    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name='Téléphone'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Compte actif'
    )
    
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_users',
        verbose_name='Créé par'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de création'
    )
    
    # Métadonnées
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def get_role_display(self):
        """Retourne le nom du rôle"""
        return dict(self.ROLE_CHOICES).get(self.role, 'Inconnu')
    
    def is_manager(self):
        """Vérifie si l'utilisateur est manager"""
        return self.role == 'manager'
    
    def is_employee(self):
        """Vérifie si l'utilisateur est employé"""
        return self.role == 'employee'
    
    def can_manage_users(self):
        """Vérifie si l'utilisateur peut gérer les utilisateurs"""
        return self.is_manager()
    
    def can_manage_products(self):
        """Vérifie si l'utilisateur peut gérer les produits"""
        return self.is_manager()
    
    def can_manage_orders(self):
        """Vérifie si l'utilisateur peut gérer les commandes"""
        return True  # Tous les utilisateurs peuvent gérer les commandes
    
    def can_manage_clients(self):
        """Vérifie si l'utilisateur peut gérer les clients"""
        return True  # Tous les utilisateurs peuvent gérer les clients
    
    def can_manage_aprovision(self):
        """Vérifie si l'utilisateur peut gérer les approvisionnements"""
        return self.is_manager()
    
    def can_view_analytics(self):
        """Vérifie si l'utilisateur peut voir les analytics"""
        return self.is_manager()
    
    def can_edit_orders(self):
        """Vérifie si l'utilisateur peut modifier les commandes (pour paiements)"""
        return True  # Tous les utilisateurs peuvent modifier les commandes pour les paiements


class UserProfile(models.Model):
    """Profil étendu pour les utilisateurs"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Utilisateur'
    )
    
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name='Adresse'
    )
    
    birth_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='Date de naissance'
    )
    
    hire_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='Date d\'embauche'
    )
    
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='Salaire'
    )
    
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notes'
    )
    
    # Métadonnées
    class Meta:
        verbose_name = 'Profil utilisateur'
        verbose_name_plural = 'Profils utilisateurs'
    
    def __str__(self):
        return f"Profil de {self.user.get_full_name()}"


class AppSetting(models.Model):
    """Paramètres globaux personnalisables par le manager"""
    currency_label = models.CharField(
        max_length=10,
        default='GMD',
        verbose_name=_('Devise (label)'),
        help_text=_('Exemple: GMD, FCFA, CFA, €')
    )
    low_stock_threshold = models.PositiveIntegerField(
        default=5,
        verbose_name=_('Seuil d\'alerte stock'),
        help_text=_('Stock sous lequel un produit est considéré en stock faible')
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Paramètre de l\'application')
        verbose_name_plural = _('Paramètres de l\'application')

    def __str__(self):
        return f"Paramètres ({self.currency_label}, seuil {self.low_stock_threshold})"

    @classmethod
    def get_solo(cls) -> 'AppSetting':
        obj, _ = cls.objects.get_or_create(id=1)
        return obj

    @classmethod
    def get_currency_label(cls) -> str:
        return cls.get_solo().currency_label or 'GMD'

    @classmethod
    def get_low_stock_threshold(cls) -> int:
        return cls.get_solo().low_stock_threshold or 5
