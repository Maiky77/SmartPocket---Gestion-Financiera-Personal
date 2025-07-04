# gastos/forms.py
from django import forms
from django.utils import timezone
from .models import Gasto, TipoGasto

class GastoForm(forms.ModelForm):
    """Formulario para registrar gastos según mockup"""
    
    class Meta:
        model = Gasto
        fields = ['tipo_gasto', 'monto', 'descripcion', 'fecha']
        widgets = {
            'tipo_gasto': forms.Select(attrs={
                'class': 'form-control',
                'id': 'categoria-select'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el monto',
                'step': '0.01',
                'min': '0'
            }),
            'descripcion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del gasto',
                'maxlength': 255
            }),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'value': timezone.now().date()
            })
        }
        labels = {
            'tipo_gasto': 'Categoría',
            'monto': 'Monto (S/.)',
            'descripcion': 'Descripción',
            'fecha': 'Fecha'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar el queryset de tipos de gasto
        self.fields['tipo_gasto'].queryset = TipoGasto.objects.all()
        self.fields['tipo_gasto'].empty_label = "Seleccionar categoría"
        
        # Hacer todos los campos requeridos
        for field in self.fields.values():
            field.required = True

class FiltroGastosForm(forms.Form):
    """Formulario para filtrar gastos en el historial"""
    
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'Fecha inicio'
        }),
        label='Desde'
    )
    
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'Fecha fin'
        }),
        label='Hasta'
    )
    
    categoria = forms.ModelChoiceField(
        queryset=TipoGasto.objects.all(),
        required=False,
        empty_label="Todas las categorías",
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='Categoría'
    )