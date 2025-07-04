# authentication/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class Usuario(AbstractUser):
    """Modelo de usuario personalizado para SmartPocket"""
    
    # Campos adicionales
    email = models.EmailField(unique=True, verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=15, blank=True, null=True, verbose_name="Teléfono")
    fecha_registro = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Registro")
    
    # NUEVOS CAMPOS PARA EL PERFIL
    foto_perfil = models.ImageField(
        upload_to='perfiles/', 
        blank=True, 
        null=True, 
        verbose_name="Foto de Perfil",
        help_text="Sube una imagen para tu foto de perfil (máximo 5MB)"
    )
    descripcion_corta = models.TextField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Descripción Corta",
        help_text="Cuéntanos un poco sobre ti"
    )
    
    # Configuración del modelo
    USERNAME_FIELD = 'email'  # Usar email como campo de login
    REQUIRED_FIELDS = ['username']  # Campos requeridos además del email
    
    def getNombre(self):
        """Obtiene el nombre completo o username si no hay nombre"""
        if self.first_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.username
    
    def getEmail(self):
        """Obtiene el email del usuario"""
        return self.email
    
    def getTelefono(self):
        """Obtiene el teléfono del usuario"""
        return self.telefono or "No especificado"
    
    def setNombre(self, nombre):
        """Establece el nombre del usuario"""
        self.first_name = nombre
    
    def setTelefono(self, telefono):
        """Establece el teléfono del usuario"""
        self.telefono = telefono
    
    def setEmail(self, email):
        """Establece el email del usuario"""
        self.email = email
    
    def __str__(self):
        return f"{self.getNombre()} ({self.email})"
    
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"