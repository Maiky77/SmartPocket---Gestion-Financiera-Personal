# presupuestos/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Presupuesto
from gastos.models import TipoGasto

class PresupuestoForm(forms.ModelForm):
    """
    Formulario para crear y editar presupuestos
    """
    
    class Meta:
        model = Presupuesto
        fields = ['categoria', 'monto_maximo', 'fecha_inicio', 'fecha_fin']
        widgets = {
            'categoria': forms.Select(attrs={
                'class': 'form-input',
                'required': True
            }),
            'monto_maximo': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': 'Ingrese el monto máximo',
                'step': '0.01',
                'min': '0.01',
                'required': True
            }),
            'fecha_inicio': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
            'fecha_fin': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
                'required': True
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)
        
        # Personalizar queryset de categorías
        self.fields['categoria'].queryset = TipoGasto.objects.all()
        self.fields['categoria'].empty_label = "Seleccionar categoría"
        
        # Establecer fecha de inicio por defecto (primer día del mes actual)
        if not self.instance.pk:
            hoy = timezone.now().date()
            primer_dia_mes = hoy.replace(day=1)
            # Último día del mes
            if hoy.month == 12:
                ultimo_dia_mes = hoy.replace(year=hoy.year + 1, month=1, day=1) - timezone.timedelta(days=1)
            else:
                ultimo_dia_mes = hoy.replace(month=hoy.month + 1, day=1) - timezone.timedelta(days=1)
            
            self.fields['fecha_inicio'].initial = primer_dia_mes
            self.fields['fecha_fin'].initial = ultimo_dia_mes
    
    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        categoria = cleaned_data.get('categoria')
        monto_maximo = cleaned_data.get('monto_maximo')
        
        # Validar que la fecha de fin sea posterior a la de inicio
        if fecha_inicio and fecha_fin:
            if fecha_fin <= fecha_inicio:
                raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio.")
            
            # Validar que el período no sea muy largo (máximo 1 año)
            diferencia = fecha_fin - fecha_inicio
            if diferencia.days > 365:
                raise ValidationError("El período del presupuesto no puede ser mayor a 1 año.")
        
        # Validar monto máximo
        if monto_maximo and monto_maximo <= 0:
            raise ValidationError("El monto máximo debe ser mayor a 0.")
        
        # Validar que no exista un presupuesto activo para la misma categoría en el mismo período
        if self.usuario and categoria and fecha_inicio and fecha_fin:
            presupuestos_existentes = Presupuesto.objects.filter(
                id_usuario=self.usuario,
                categoria=categoria,
                activo=True,
                fecha_inicio__lte=fecha_fin,
                fecha_fin__gte=fecha_inicio
            )
            
            # Si estamos editando, excluir el presupuesto actual
            if self.instance.pk:
                presupuestos_existentes = presupuestos_existentes.exclude(pk=self.instance.pk)
            
            if presupuestos_existentes.exists():
                raise ValidationError(
                    f"Ya existe un presupuesto activo para {categoria.get_nombre_display()} "
                    f"en el período seleccionado."
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        presupuesto = super().save(commit=False)
        if self.usuario:
            presupuesto.id_usuario = self.usuario
        if commit:
            presupuesto.save()
        return presupuesto

class FiltroPresupuestosForm(forms.Form):
    """
    Formulario para filtrar presupuestos
    """
    ESTADO_CHOICES = [
        ('', 'Todos los estados'),
        ('activo', 'Activos'),
        ('excedido', 'Excedidos'),
        ('cerca_limite', 'Cerca del límite'),
        ('vigente', 'Vigentes'),
        ('expirado', 'Expirados'),
    ]
    
    categoria = forms.ModelChoiceField(
        queryset=TipoGasto.objects.all(),
        required=False,
        empty_label="Todas las categorías",
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-input'})
    )
    
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )