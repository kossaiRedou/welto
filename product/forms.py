from django import forms
from .models import Product, Category


class SimpleProductForm(forms.ModelForm):
    """Formulaire simple pour ajouter/modifier un produit"""
    
    class Meta:
        model = Product
        fields = ['title', 'category', 'value', 'discount_value', 'active']
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

            'active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'title': 'Nom du Produit',
            'category': 'Catégorie',
            'value': 'Prix Normal',
            'discount_value': 'Prix Réduit',
            'active': 'Produit Actif'
        }
        help_texts = {
            'title': 'Donnez un nom clair à votre produit',
            'value': 'Prix de vente normal',
            'discount_value': 'Prix réduit (optionnel, laissez 0 si pas de réduction)',
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
    
    # Nouveaux champs pour la traçabilité
    prix_achat_unitaire = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prix d\'achat unitaire (FCFA)',
            'step': '0.01'
        }),
        help_text="Obligatoire pour les ajouts de stock (approvisionnements)"
    )
    
    fournisseur = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom du fournisseur (optionnel)'
        })
    )
    
    reference = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'N° facture ou référence (optionnel)'
        })
    )
    
    description = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Description du mouvement (optionnel)'
        })
    )
    
    def __init__(self, *args, **kwargs):
        product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        
        # Pré-remplir le prix d'achat si le produit en a un
        if product and product.prix_achat > 0:
            self.fields['prix_achat_unitaire'].initial = product.prix_achat
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        prix_achat = cleaned_data.get('prix_achat_unitaire')
        
        # Le prix d'achat est obligatoire pour les ajouts de stock
        if action == 'add' and not prix_achat:
            raise forms.ValidationError(
                'Le prix d\'achat unitaire est obligatoire pour les approvisionnements.'
            )
        
        return cleaned_data