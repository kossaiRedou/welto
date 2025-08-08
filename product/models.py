from django.db import models
from django.conf import settings
try:
    from users.models import AppSetting
except Exception:
    AppSetting = None
from .managers import ProductManager

def get_currency_label():
    try:
        if AppSetting:
            return AppSetting.get_currency_label()
    except Exception:
        pass
    from django.conf import settings as dj_settings
    return getattr(dj_settings, 'CURRENCY', 'GMD')

# Seuil de stock faible depuis les paramètres
def get_low_stock_threshold():
    try:
        return AppSetting.get_low_stock_threshold()
    except Exception:
        return 5


class Category(models.Model):
    title = models.CharField(max_length=150, unique=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.title


class Product(models.Model):
    active = models.BooleanField(default=True)
    title = models.CharField(max_length=150, unique=True)
    category = models.ForeignKey(Category, null=True, on_delete=models.SET_NULL)
    value = models.DecimalField(default=0.00, decimal_places=2, max_digits=10)
    discount_value = models.DecimalField(default=0.00, decimal_places=2, max_digits=10)
    final_value = models.DecimalField(default=0.00, decimal_places=2, max_digits=10)
    qty = models.PositiveIntegerField(default=0)
    prix_achat = models.DecimalField(default=0.00, decimal_places=2, max_digits=10, help_text="Prix d'achat unitaire (pour la traçabilité)")

    objects = models.Manager()
    browser = ProductManager()

    class Meta:
        verbose_name_plural = 'Products'

    def save(self, *args, **kwargs):
        self.final_value = self.discount_value if self.discount_value > 0 else self.value
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def tag_final_value(self):
        return f'{self.final_value} {get_currency_label()}'
    tag_final_value.short_description = 'Value'
    
    def tag_prix_achat(self):
        if self.prix_achat > 0:
            return f'{self.prix_achat} {get_currency_label()}'
        return 'Non défini'
    tag_prix_achat.short_description = 'Prix d\'achat'