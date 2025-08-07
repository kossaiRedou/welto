from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from .models import User, UserProfile

class CustomUserCreationForm(UserCreationForm):
    """Formulaire de création d'utilisateur personnalisé"""
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'role', 'password1', 'password2')
        
    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)
        
        # Personnaliser les labels
        self.fields['first_name'].label = 'Prénom'
        self.fields['last_name'].label = 'Nom'
        self.fields['email'].label = 'Email'
        self.fields['phone'].label = 'Téléphone'
        self.fields['role'].label = 'Rôle'
        
        # Personnaliser les placeholders
        self.fields['first_name'].widget.attrs.update({'placeholder': 'Prénom'})
        self.fields['last_name'].widget.attrs.update({'placeholder': 'Nom'})
        self.fields['email'].widget.attrs.update({'placeholder': 'email@exemple.com'})
        self.fields['phone'].widget.attrs.update({'placeholder': 'Téléphone'})
        
        # Ajouter des classes CSS
        for field_name, field in self.fields.items():
            if hasattr(field, 'widget'):
                if field_name == 'is_active':
                    field.widget.attrs.update({'class': 'form-check-input'})
                elif field_name == 'role':
                    field.widget.attrs.update({'class': 'form-select'})
                elif field_name in ['password1', 'password2']:
                    field.widget.attrs.update({'class': 'form-control'})
                    field.widget.attrs.update({'placeholder': 'Mot de passe' if field_name == 'password1' else 'Confirmer le mot de passe'})
                else:
                    field.widget.attrs.update({'class': 'form-control'})
        
        # Rendre certains champs obligatoires
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        
        # Limiter les rôles selon l'utilisateur qui crée
        if self.request_user and not self.request_user.is_manager():
            self.fields['role'].choices = [('employee', 'Employé')]
            self.fields['role'].initial = 'employee'
            self.fields['role'].widget.attrs['readonly'] = True
            self.fields['role'].widget.attrs['disabled'] = True
    
    def clean_email(self):
        """Validation de l'email"""
        email = self.cleaned_data.get('email')
        if email:
            # Exclure l'utilisateur actuel lors de la modification
            existing_user = User.objects.filter(email=email)
            if self.instance:
                existing_user = existing_user.exclude(pk=self.instance.pk)
            
            if existing_user.exists():
                raise ValidationError('Un utilisateur avec cet email existe déjà.')
        return email
    
    def clean_phone(self):
        """Validation du téléphone"""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Supprimer les espaces et caractères spéciaux
            phone = ''.join(filter(str.isdigit, phone))
            if len(phone) < 7:
                raise ValidationError('Le numéro de téléphone doit contenir au moins 7 chiffres.')
        return phone
    
    def save(self, commit=True):
        """Sauvegarder l'utilisateur avec le créateur"""
        user = super().save(commit=False)
        if self.request_user:
            user.created_by = self.request_user
        if commit:
            user.save()
        return user
    
    def clean(self):
        """Nettoyer les données du formulaire"""
        cleaned_data = super().clean()
        
        # Si le rôle est désactivé, utiliser la valeur par défaut
        if self.request_user and not self.request_user.is_manager():
            cleaned_data['role'] = 'employee'
        
        return cleaned_data


class CustomUserChangeForm(UserChangeForm):
    """Formulaire de modification d'utilisateur personnalisé"""
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'role', 'is_active')
        
    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop('request_user', None)
        super().__init__(*args, **kwargs)
        
        # Personnaliser les labels
        self.fields['first_name'].label = 'Prénom'
        self.fields['last_name'].label = 'Nom'
        self.fields['email'].label = 'Email'
        self.fields['phone'].label = 'Téléphone'
        self.fields['role'].label = 'Rôle'
        self.fields['is_active'].label = 'Compte actif'
        
        # Limiter les modifications selon l'utilisateur
        if self.request_user and not self.request_user.is_manager():
            # Les employés ne peuvent pas modifier les rôles
            self.fields['role'].widget.attrs['readonly'] = True
            self.fields['role'].widget.attrs['disabled'] = True
            self.fields['is_active'].widget.attrs['readonly'] = True
            self.fields['is_active'].widget.attrs['disabled'] = True
        
        # Ajouter des classes CSS
        for field_name, field in self.fields.items():
            if hasattr(field, 'widget'):
                if field_name == 'is_active':
                    field.widget.attrs.update({'class': 'form-check-input'})
                elif field_name == 'role':
                    field.widget.attrs.update({'class': 'form-select'})
                elif field_name in ['password1', 'password2']:
                    field.widget.attrs.update({'class': 'form-control'})
                    field.widget.attrs.update({'placeholder': 'Mot de passe' if field_name == 'password1' else 'Confirmer le mot de passe'})
                else:
                    field.widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        """Nettoyer les données du formulaire"""
        cleaned_data = super().clean()
        
        # Si les champs sont désactivés, utiliser les valeurs actuelles
        if self.request_user and not self.request_user.is_manager():
            if self.instance:
                cleaned_data['role'] = self.instance.role
                cleaned_data['is_active'] = self.instance.is_active
        
        return cleaned_data


class UserProfileForm(forms.ModelForm):
    """Formulaire pour le profil utilisateur"""
    
    class Meta:
        model = UserProfile
        fields = ('address', 'birth_date', 'hire_date', 'salary', 'notes')
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'hire_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personnaliser les labels
        self.fields['address'].label = 'Adresse'
        self.fields['birth_date'].label = 'Date de naissance'
        self.fields['hire_date'].label = 'Date d\'embauche'
        self.fields['salary'].label = 'Salaire'
        self.fields['notes'].label = 'Notes'


class UserSearchForm(forms.Form):
    """Formulaire de recherche d'utilisateurs"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Rechercher par nom, email ou téléphone...',
            'class': 'form-control'
        }),
        label='Recherche'
    )
    
    role = forms.ChoiceField(
        choices=[('', 'Tous les rôles')] + User.ROLE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Rôle'
    )
    
    is_active = forms.ChoiceField(
        choices=[
            ('', 'Tous les comptes'),
            ('True', 'Comptes actifs'),
            ('False', 'Comptes inactifs')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Statut'
    )


class PasswordChangeForm(forms.Form):
    """Formulaire de changement de mot de passe"""
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe actuel'
        }),
        label='Mot de passe actuel'
    )
    
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nouveau mot de passe'
        }),
        label='Nouveau mot de passe'
    )
    
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmer le nouveau mot de passe'
        }),
        label='Confirmer le nouveau mot de passe'
    )
    
    def clean(self):
        """Validation du formulaire"""
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise ValidationError('Les mots de passe ne correspondent pas.')
            
            if len(new_password1) < 8:
                raise ValidationError('Le mot de passe doit contenir au moins 8 caractères.')
        
        return cleaned_data 