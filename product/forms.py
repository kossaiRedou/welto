from django import forms
from .models import Product, Category


class SimpleProductForm(forms.ModelForm):
    """Formulaire simple pour ajouter/modifier un produit"""
    
    class Meta:
        model = Product
        fields = ['title', 'category', 'value', 'discount_value', 'qty', 'active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du produit (ex: Riz 1kg)',
                'required': True
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'step': '0.01',
                'min': '0'
            }),
            'discount_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0 (optionnel)',
                'step': '0.01',
                'min': '0'
            }),
            'qty': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0',
                'min': '0'
            }),
            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'title': 'Nom du Produit',
            'category': 'Catégorie',
            'value': 'Prix Normal (GMD)',
            'discount_value': 'Prix Réduit (GMD)',
            'qty': 'Quantité en Stock',
            'active': 'Produit Actif'
        }
        help_texts = {
            'title': 'Donnez un nom clair à votre produit',
            'value': 'Prix de vente normal',
            'discount_value': 'Prix réduit (optionnel, laissez 0 si pas de réduction)',
            'qty': 'Nombre d\'unités en stock',
            'active': 'Décochez pour désactiver temporairement le produit'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre le champ category optionnel avec une option par défaut
        self.fields['category'].empty_label = "-- Choisir une catégorie --"
        self.fields['category'].required = False
        
        # Valeurs par défaut
        if not self.instance.pk:  # Nouveau produit
            self.fields['active'].initial = True
            self.fields['qty'].initial = 0
            self.fields['value'].initial = 0
            self.fields['discount_value'].initial = 0


class SimpleCategoryForm(forms.ModelForm):
    """Formulaire simple pour ajouter une catégorie"""
    
    class Meta:
        model = Category
        fields = ['title']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de la catégorie (ex: Céréales, Boissons)',
                'required': True
            })
        }
        labels = {
            'title': 'Nom de la Catégorie'
        }
        help_texts = {
            'title': 'Créez des catégories pour organiser vos produits'
        }


class QuickStockForm(forms.Form):
    """Formulaire rapide pour ajuster le stock"""
    action = forms.ChoiceField(
        choices=[('add', 'Ajouter'), ('remove', 'Retirer'), ('set', 'Définir')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantité'
        })
    )