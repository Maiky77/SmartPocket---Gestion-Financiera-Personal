# authentication/forms.py
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
import os
from .models import Usuario

class PerfilForm(forms.ModelForm):
    """Formulario para editar información personal del perfil"""
    
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'telefono', 'descripcion_corta', 'foto_perfil']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-field',
                'placeholder': 'NOMBRE'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-field',
                'placeholder': 'APELLIDO'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-field',
                'placeholder': 'TELÉFONO'
            }),
            'descripcion_corta': forms.Textarea(attrs={
                'class': 'textarea-description',
                'placeholder': 'Escribe una descripción sobre ti, tus objetivos financieros o cualquier nota personal...',
                'rows': 4
            }),
            'foto_perfil': forms.FileInput(attrs={
                'accept': 'image/*',
                'id': 'id_foto_perfil',
                'style': 'display: none;'
            })
        }

    def clean_foto_perfil(self):
        """Validar foto de perfil"""
        foto = self.cleaned_data.get('foto_perfil')
        
        if foto:
            # Validar tamaño del archivo (max 5MB)
            if foto.size > 5 * 1024 * 1024:
                raise ValidationError('La imagen no puede superar los 5MB.')
            
            # Validar tipo de archivo
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']
            ext = os.path.splitext(foto.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError('Solo se permiten imágenes JPG, PNG o GIF.')
        
        return foto

    def clean_telefono(self):
        """Validar formato de teléfono"""
        telefono = self.cleaned_data.get('telefono')
        
        if telefono:
            # Remover espacios y caracteres especiales para validación
            telefono_limpio = ''.join(filter(str.isdigit, telefono))
            
            if len(telefono_limpio) < 9:
                raise ValidationError('El teléfono debe tener al menos 9 dígitos.')
            
            if len(telefono_limpio) > 15:
                raise ValidationError('El teléfono no puede tener más de 15 dígitos.')
        
        return telefono

class CambioContrasenaForm(PasswordChangeForm):
    """Formulario personalizado para cambio de contraseña"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalizar widgets
        self.fields['old_password'].widget.attrs.update({
            'class': 'password-input',
            'placeholder': '••••••••'
        })
        self.fields['new_password1'].widget.attrs.update({
            'class': 'password-input',
            'placeholder': '••••••••'
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'password-input',
            'placeholder': '••••••••'
        })

    def clean_new_password2(self):
        """Validación adicional para contraseñas"""
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError('Las contraseñas no coinciden.')
            
            # Validaciones adicionales
            if len(password1) < 8:
                raise ValidationError('La contraseña debe tener al menos 8 caracteres.')
            
            if password1.isdigit():
                raise ValidationError('La contraseña no puede ser solo números.')
            
            if password1.lower() in ['password', 'contraseña', '12345678']:
                raise ValidationError('La contraseña es muy común.')
        
        return password2