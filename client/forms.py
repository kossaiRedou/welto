from django import forms
from .models import Client


class BaseForm(forms.Form):
    """Classe de base pour appliquer des styles uniformes"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class ClientForm(BaseForm, forms.ModelForm):
    """Formulaire pour créer/modifier un client"""
    
    class Meta:
        model = Client
        fields = ['name', 'phone', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nom complet du client',
                'maxlength': 150
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': 'Ex: 7123456 (7 chiffres)',
                'maxlength': 7,
                'pattern': '[0-9]{7}',
                'title': 'Numéro de téléphone gambien (7 chiffres)'
            }),
        }
        labels = {
            'name': 'Nom complet',
            'phone': 'Téléphone',
            'is_active': 'Client actif'
        }
        help_texts = {
            'phone': 'Numéro de téléphone gambien (7 chiffres) - doit être unique',
            'is_active': 'Décocher pour désactiver le client'
        }
    
    def clean_phone(self):
        """Validation personnalisée du téléphone pour la Gambie (7 chiffres)"""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Supprimer les espaces et caractères spéciaux
            phone = ''.join(filter(str.isdigit, phone))
            
            if len(phone) != 7:
                raise forms.ValidationError('Le numéro de téléphone doit contenir exactement 7 chiffres (format Gambie)')
            
            # Vérifier l'unicité (sauf pour l'instance actuelle en cas de modification)
            existing = Client.objects.filter(phone=phone)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise forms.ValidationError(f'Un client avec le numéro {phone} existe déjà')
        
        return phone
    
    def clean_name(self):
        """Validation du nom"""
        name = self.cleaned_data.get('name')
        if name:
            name = name.strip().title()  # Capitaliser proprement
            if len(name) < 2:
                raise forms.ValidationError('Le nom doit contenir au moins 2 caractères')
        return name


class ClientSearchForm(forms.Form):
    """Formulaire de recherche de clients"""
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par nom ou téléphone...',
            'autocomplete': 'off'
        }),
        label='Recherche'
    )
    
    status = forms.ChoiceField(
        choices=[
            ('', 'Tous les clients'),
            ('active', 'Clients actifs'),
            ('inactive', 'Clients inactifs')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Statut'
    )