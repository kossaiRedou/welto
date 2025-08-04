from django.db import models
import datetime


class Client(models.Model):
    """Modèle simple pour gérer les clients"""
    phone = models.CharField(max_length=20, unique=True, help_text="Numéro de téléphone (unique)")
    name = models.CharField(max_length=150, help_text="Nom complet du client")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Client actif")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Client"
        verbose_name_plural = "Clients"
    
    def __str__(self):
        return f"{self.name} ({self.phone})"
    
    def total_orders(self):
        """Nombre total de commandes du client"""
        return self.orders.count()
    
    def total_spent(self):
        """Montant total dépensé par le client"""
        from decimal import Decimal
        total = self.orders.aggregate(models.Sum('final_value'))['final_value__sum']
        return total or Decimal('0.00')
    
    def last_order_date(self):
        """Date de la dernière commande"""
        last_order = self.orders.first()  # Grâce à ordering = ['-date'] dans Order
        return last_order.date if last_order else None
    
    @classmethod
    def search_by_phone(cls, phone_query):
        """Recherche client par numéro de téléphone (partiel)"""
        return cls.objects.filter(
            phone__icontains=phone_query,
            is_active=True
        ).order_by('-created_at')[:10]  # Limiter à 10 résultats