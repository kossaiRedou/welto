from django.db import models
from django.db.models import Sum
from django.conf import settings
from django.urls import reverse
from django.dispatch import receiver
from django.db.models.signals import post_delete
import datetime
from product.models import Product

from decimal import Decimal
CURRENCY = settings.CURRENCY


class OrderManager(models.Manager):

    def active(self):
        return self.filter(active=True)


class Order(models.Model):
    date = models.DateField(default=datetime.date.today)
    title = models.CharField(blank=True, max_length=150)
    timestamp = models.DateField(auto_now_add=True)
    value = models.DecimalField(default=0.00, decimal_places=2, max_digits=20)
    discount = models.DecimalField(default=0.00, decimal_places=2, max_digits=20)
    final_value = models.DecimalField(default=0.00, decimal_places=2, max_digits=20)
    is_paid = models.BooleanField(default=True)
    # Relation optionnelle vers le client (ajout non-intrusif)
    client = models.ForeignKey('client.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', help_text="Client associé (optionnel)")
    objects = models.Manager()
    browser = OrderManager()

    class Meta:
        ordering = ['-date']

    def save(self, *args, **kwargs):
        # Sauvegarder d'abord l'instance pour qu'elle ait une clé primaire
        super().save(*args, **kwargs)
        
        # Maintenant on peut accéder aux relations
        order_items = self.order_items.all()
        self.value = order_items.aggregate(Sum('total_price'))['total_price__sum'] if order_items.exists() else 0.00
        self.final_value = Decimal(self.value) - Decimal(self.discount)
        
        # Sauvegarder à nouveau avec les valeurs calculées
        if order_items.exists():
            super().save(*args, **kwargs)

    def __str__(self):
        return self.title if self.title else 'New Order'

    def get_edit_url(self):
        return reverse('update_order', kwargs={'pk': self.id})

    def get_delete_url(self):
        return reverse('delete_order', kwargs={'pk': self.id})

    def tag_final_value(self):
        return f'{self.final_value} {CURRENCY}'

    def tag_discount(self):
        return f'{self.discount} {CURRENCY}'

    def tag_value(self):
        return f'{self.value} {CURRENCY}'
    
    def total_payments(self):
        """Calcule le total des paiements reçus"""
        return self.payments.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    def remaining_amount(self):
        """Calcule le montant restant à payer"""
        return max(Decimal('0.00'), self.final_value - self.total_payments())
    
    def payment_percentage(self):
        """Calcule le pourcentage payé"""
        if self.final_value <= 0:
            return 100
        return min(100, (self.total_payments() / self.final_value) * 100)
    
    def is_fully_paid(self):
        """Vérifie si la commande est entièrement payée"""
        return self.remaining_amount() <= Decimal('0.00')
    
    def tag_total_payments(self):
        return f'{self.total_payments()} {CURRENCY}'
    
    def tag_remaining_amount(self):
        return f'{self.remaining_amount()} {CURRENCY}'
    
    def client_display(self):
        """Affichage du client pour les templates"""
        if self.client:
            return f"{self.client.name} ({self.client.phone})"
        return self.title if self.title else f"Commande #{self.id}"

    @staticmethod
    def filter_data(request, queryset):
        search_name = request.GET.get('search_name', None)
        date_start = request.GET.get('date_start', None)
        date_end = request.GET.get('date_end', None)
        is_paid = request.GET.get('is_paid', None)
        queryset = queryset.filter(title__contains=search_name) if search_name else queryset
        if date_end and date_start and date_end >= date_start:
            date_start = datetime.datetime.strptime(date_start, '%m/%d/%Y').strftime('%Y-%m-%d')
            date_end = datetime.datetime.strptime(date_end, '%m/%d/%Y').strftime('%Y-%m-%d')
            print(date_start, date_end)
            queryset = queryset.filter(date__range=[date_start, date_end])
        
        # Filtrer par statut de paiement
        if is_paid == "True":
            queryset = queryset.filter(is_paid=True)
        elif is_paid == "False":
            queryset = queryset.filter(is_paid=False)
        # Si is_paid est None ou "", on ne filtre pas (affiche tous)
        
        return queryset


class OrderItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    qty = models.PositiveIntegerField(default=1)
    price = models.DecimalField(default=0.00, decimal_places=2, max_digits=20)
    discount_price = models.DecimalField(default=0.00, decimal_places=2, max_digits=20)
    final_price = models.DecimalField(default=0.00, decimal_places=2, max_digits=20)
    total_price = models.DecimalField(default=0.00, decimal_places=2, max_digits=20)

    def __str__(self):
        return f'{self.product.title}'

    def save(self,  *args, **kwargs):
        self.final_price = self.discount_price if self.discount_price > 0 else self.price
        self.total_price = Decimal(self.qty) * Decimal(self.final_price)
        super().save(*args, **kwargs)
        self.order.save()

    def tag_final_price(self):
        return f'{self.final_price} {CURRENCY}'

    def tag_discount(self):
        return f'{self.discount_price} {CURRENCY}'

    def tag_price(self):
        return f'{self.price} {CURRENCY}'


class Payment(models.Model):
    """Modèle pour gérer les paiements échelonnés d'une commande"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=20, decimal_places=2, help_text="Montant du paiement")
    date = models.DateField(default=datetime.date.today, help_text="Date du paiement")
    method = models.CharField(max_length=50, choices=[
        ('cash', 'Espèces'),
        ('mobile', 'Mobile Money'),
        ('bank', 'Virement bancaire'),
        ('credit', 'Crédit'),
        ('other', 'Autre')
    ], default='cash', help_text="Méthode de paiement")
    note = models.CharField(max_length=200, blank=True, help_text="Note sur le paiement")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.amount} {CURRENCY} - {self.get_method_display()}'

    def tag_amount(self):
        return f'{self.amount} {CURRENCY}'


@receiver(post_delete, sender=OrderItem)
def delete_order_item(sender, instance, **kwargs):
    product = instance.product
    product.qty += instance.qty
    product.save()
    instance.order.save()


# Signal pour mettre à jour automatiquement is_paid quand un paiement est ajouté/supprimé
from django.db.models.signals import post_save, post_delete

@receiver(post_save, sender=Payment)
def update_order_payment_status_on_save(sender, instance, **kwargs):
    """Met à jour le statut is_paid de la commande quand un paiement est ajouté/modifié"""
    order = instance.order
    order.is_paid = order.is_fully_paid()
    # Utiliser update pour éviter de déclencher le signal save de Order
    Order.objects.filter(id=order.id).update(is_paid=order.is_paid)

@receiver(post_delete, sender=Payment)
def update_order_payment_status_on_delete(sender, instance, **kwargs):
    """Met à jour le statut is_paid de la commande quand un paiement est supprimé"""
    order = instance.order
    order.is_paid = order.is_fully_paid()
    # Utiliser update pour éviter de déclencher le signal save de Order
    Order.objects.filter(id=order.id).update(is_paid=order.is_paid)

