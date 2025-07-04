from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Usuario(AbstractUser):
    """
    Modelo Usuario personalizado basado en el diagrama UML de SmartPocket
    """
    
    # Campos adicionales según el diseño UML
    telefono = models.CharField(max_length=15, blank=True, null=True)
    fecha_registro = models.DateTimeField(default=timezone.now)
    descripcion_corta = models.TextField(max_length=500, blank=True, null=True)
    
    # Métodos del diagrama UML
    def getNombre(self):
        """Obtiene el nombre completo del usuario"""
        return f"{self.first_name} {self.last_name}".strip() or self.username
    
    def getEmail(self):
        """Obtiene el email del usuario"""
        return self.email
    
    def getTelefono(self):
        """Obtiene el teléfono del usuario"""
        return self.telefono
    
    def __str__(self):
        return f"{self.getNombre()} ({self.username})"
    
    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'