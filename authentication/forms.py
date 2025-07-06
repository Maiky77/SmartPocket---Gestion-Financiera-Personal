# authentication/forms.py
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
import os
import re
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

# ==================== NUEVOS FORMULARIOS DE RECUPERACIÓN ====================

class SolicitudRecuperacionForm(forms.Form):
    """Formulario para solicitar recuperación de contraseña"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'tu@email.com',
            'autocomplete': 'email'
        }),
        label='Correo Electrónico',
        help_text='Ingresa el email asociado a tu cuenta'
    )
    
    def clean_email(self):
        """Validar que el email existe en el sistema"""
        email = self.cleaned_data.get('email')
        
        if email:
            try:
                Usuario.objects.get(email=email)
            except Usuario.DoesNotExist:
                raise ValidationError('No existe una cuenta asociada a este email.')
        
        return email

class VerificacionCodigoForm(forms.Form):
    """Formulario para verificar código de recuperación"""
    
    codigo = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-input codigo-input',
            'placeholder': '000000',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
            'maxlength': '6'
        }),
        label='Código de Verificación',
        help_text='Ingresa el código de 6 dígitos enviado a tu email'
    )
    
    def clean_codigo(self):
        """Validar formato del código"""
        codigo = self.cleaned_data.get('codigo')
        
        if codigo:
            # Solo números
            if not codigo.isdigit():
                raise ValidationError('El código debe contener solo números.')
            
            # Exactamente 6 dígitos
            if len(codigo) != 6:
                raise ValidationError('El código debe tener exactamente 6 dígitos.')
        
        return codigo

class NuevaContrasenaForm(forms.Form):
    """Formulario para establecer nueva contraseña"""
    
    nueva_contrasena = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'password-input',
            'placeholder': '••••••••',
            'autocomplete': 'new-password'
        }),
        label='Nueva Contraseña',
        help_text='Mínimo 8 caracteres, incluye letras y números'
    )
    
    confirmar_contrasena = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'password-input',
            'placeholder': '••••••••',
            'autocomplete': 'new-password'
        }),
        label='Confirmar Contraseña',
        help_text='Repite la contraseña anterior'
    )
    
    def clean_nueva_contrasena(self):
        """Validar política de contraseñas"""
        password = self.cleaned_data.get('nueva_contrasena')
        
        if password:
            # Mínimo 8 caracteres
            if len(password) < 8:
                raise ValidationError('La contraseña debe tener al menos 8 caracteres.')
            
            # No solo números
            if password.isdigit():
                raise ValidationError('La contraseña no puede ser solo números.')
            
            # No solo letras
            if password.isalpha():
                raise ValidationError('La contraseña debe incluir al menos un número.')
            
            # Contraseñas comunes
            common_passwords = [
                'password', 'contraseña', '12345678', 'qwerty', 
                'abc123', '123456789', 'password123'
            ]
            if password.lower() in common_passwords:
                raise ValidationError('Esta contraseña es muy común. Elige una más segura.')
            
            # Al menos una letra y un número
            if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
                raise ValidationError('La contraseña debe contener letras y números.')
        
        return password
    
    def clean(self):
        """Validar que las contraseñas coincidan"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('nueva_contrasena')
        password2 = cleaned_data.get('confirmar_contrasena')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError('Las contraseñas no coinciden.')
        
        return cleaned_data

# ==================== FORMULARIO DE REGISTRO MEJORADO ====================

class RegistroUsuarioForm(forms.ModelForm):
    """Formulario completo para registro de nuevos usuarios"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'password-input',
            'placeholder': '••••••••',
            'autocomplete': 'new-password'
        }),
        label='Contraseña',
        help_text='Mínimo 8 caracteres, incluye letras y números'
    )
    
    confirmar_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'password-input',
            'placeholder': '••••••••',
            'autocomplete': 'new-password'
        }),
        label='Confirmar Contraseña'
    )
    
    acepto_terminos = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox-input'
        }),
        label='Acepto los términos y condiciones'
    )
    
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'username', 'email', 'telefono']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Tu nombre',
                'autocomplete': 'given-name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Tus apellidos',
                'autocomplete': 'family-name'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nombre de usuario',
                'autocomplete': 'username'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'tu@email.com',
                'autocomplete': 'email'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+51 999 999 999',
                'autocomplete': 'tel'
            })
        }
    
    def clean_username(self):
        """Validar nombre de usuario único"""
        username = self.cleaned_data.get('username')
        
        if username:
            # Verificar si ya existe
            if Usuario.objects.filter(username=username).exists():
                raise ValidationError('Este nombre de usuario ya está en uso.')
            
            # Validar formato
            if len(username) < 3:
                raise ValidationError('El nombre de usuario debe tener al menos 3 caracteres.')
            
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                raise ValidationError('El nombre de usuario solo puede contener letras, números y guiones bajos.')
        
        return username
    
    def clean_email(self):
        """Validar email único"""
        email = self.cleaned_data.get('email')
        
        if email:
            if Usuario.objects.filter(email=email).exists():
                raise ValidationError('Ya existe una cuenta con este email.')
        
        return email
    
    def clean_telefono(self):
        """Validar formato de teléfono"""
        telefono = self.cleaned_data.get('telefono')
        
        if telefono:
            # Remover espacios y caracteres especiales
            telefono_limpio = ''.join(filter(str.isdigit, telefono))
            
            if len(telefono_limpio) < 9:
                raise ValidationError('El teléfono debe tener al menos 9 dígitos.')
        
        return telefono
    
    def clean_password(self):
        """Validar política de contraseñas"""
        password = self.cleaned_data.get('password')
        
        if password:
            # Mínimo 8 caracteres
            if len(password) < 8:
                raise ValidationError('La contraseña debe tener al menos 8 caracteres.')
            
            # No solo números
            if password.isdigit():
                raise ValidationError('La contraseña no puede ser solo números.')
            
            # Al menos una letra y un número
            if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
                raise ValidationError('La contraseña debe contener letras y números.')
        
        return password
    
    def clean(self):
        """Validar que las contraseñas coincidan"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirmar_password = cleaned_data.get('confirmar_password')
        
        if password and confirmar_password:
            if password != confirmar_password:
                raise ValidationError('Las contraseñas no coinciden.')
        
        return cleaned_data