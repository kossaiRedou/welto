from django import forms

from .models import Order


class BaseForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class OrderCreateForm(BaseForm, forms.ModelForm):
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    title = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Laissez vide pour génération automatique'
        }),
        help_text='Un numéro de commande sera généré automatiquement si ce champ est laissé vide'
    )
    # Le champ client sera géré via AJAX, pas dans le formulaire Django
    
    class Meta:
        model = Order
        fields = ['date', 'title' ]


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
        fields = ['date', 'title', 'discount', 'is_paid']