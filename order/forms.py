from django import forms

from .models import Order


class BaseForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class OrderCreateForm(BaseForm, forms.ModelForm):
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'placeholder': 'Laissez vide pour la date d\'aujourd\'hui'
        }),
        help_text='La date d\'aujourd\'hui sera utilisée si ce champ est laissé vide'
    )
    # Le champ title est masqué car généré automatiquement
    title = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.HiddenInput(),  # Masqué pour l'utilisateur
    )
    # Forcer is_paid à False explicitement
    is_paid = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput()
    )
    # Le champ client sera géré via AJAX, pas dans le formulaire Django
    
    class Meta:
        model = Order
        fields = ['date', 'title', 'is_paid']


class OrderEditForm(BaseForm, forms.ModelForm):
    title = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Numéro de commande'
        }),
        help_text='Numéro de commande (généré automatiquement si vide lors de la création)'
    )

    class Meta:
        model = Order
        fields = ['date', 'title', 'discount']