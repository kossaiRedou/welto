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
    is_paid = models.BooleanField(default=False)
    # Relation optionnelle vers le client (ajout non-intrusif)
    client = models.ForeignKey('client.Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', help_text="Client associé (optionnel)")
    objects = models.Manager()
    browser = OrderManager()

    class Meta:
        ordering = ['-date']

    def generate_order_number(self):
        """Génère un numéro de commande automatique basé sur la date et l'heure"""
        # Format: CMD-YYYYMMDD-HHMM-XXX
        # Exemple: CMD-20241215-1430-001
        
        from django.utils import timezone
        now = timezone.now()
        
        # Utiliser la date de la commande pour la partie date, et l'heure actuelle pour l'heure
        date_part = self.date.strftime('%Y%m%d')
        time_part = now.strftime('%H%M')
        
        # Compter les commandes avec des numéros générés aujourd'hui pour éviter les doublons
        today_orders_count = Order.objects.filter(
            date=self.date,
            title__startswith=f"CMD-{date_part}-"
        ).count()
        
        # Générer un numéro unique en incrémentant jusqu'à trouver un disponible
        sequence = today_orders_count + 1
        while True:
            order_number = f"CMD-{date_part}-{time_part}-{sequence:03d}"
            
            # Vérifier si ce numéro existe déjà (exclure la commande actuelle si modification)
            existing = Order.objects.filter(title=order_number)
            if self.pk:  # Si c'est une modification, exclure la commande actuelle
                existing = existing.exclude(pk=self.pk)
            
            if not existing.exists():
                return order_number
            
            sequence += 1
            
            # Sécurité : éviter une boucle infinie
            if sequence > 999:
                # Fallback avec timestamp plus précis
                microsecond_part = now.strftime('%f')[:3]  # 3 premiers chiffres des microsecondes
                return f"CMD-{date_part}-{time_part}-{microsecond_part}"
    
    def save(self, *args, **kwargs):
        # Générer automatiquement le numéro de commande si title est vide
        if not self.title or self.title.strip() == '':
            self.title = self.generate_order_number()
        
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
        # Une commande sans montant n'est pas considérée comme payée
        if self.final_value <= Decimal('0.00'):
            return False
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
    
    def order_number_display(self):
        """Affichage formaté du numéro de commande"""
        if self.title and self.title.startswith('CMD-'):
            # CMD-20241215-1430-001 -> CMD-2024/12/15-14:30-001
            parts = self.title.split('-')
            if len(parts) == 4:
                date_part = parts[1]  # 20241215
                time_part = parts[2]  # 1430
                seq_part = parts[3]   # 001
                
                # Formater la date : 20241215 -> 2024/12/15
                formatted_date = f"{date_part[:4]}/{date_part[4:6]}/{date_part[6:8]}"
                # Formater l'heure : 1430 -> 14:30
                formatted_time = f"{time_part[:2]}:{time_part[2:4]}"
                
                return f"CMD-{formatted_date}-{formatted_time}-{seq_part}"
        
        return self.title
    
    def is_auto_generated_number(self):
        """Vérifie si le titre est un numéro de commande généré automatiquement"""
        return self.title and self.title.startswith('CMD-') and len(self.title.split('-')) == 4

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

