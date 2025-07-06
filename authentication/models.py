# authentication/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import random
import string
from datetime import timedelta

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

# ==================== MODELO PARA RECUPERACIÓN DE CONTRASEÑA ====================

class TokenRecuperacion(models.Model):
    """Modelo para manejar tokens de recuperación de contraseña"""
    
    usuario = models.ForeignKey(
        Usuario, 
        on_delete=models.CASCADE, 
        related_name='tokens_recuperacion',
        verbose_name="Usuario"
    )
    codigo = models.CharField(
        max_length=6, 
        verbose_name="Código de Verificación",
        help_text="Código de 6 dígitos para verificación"
    )
    email = models.EmailField(verbose_name="Email de Recuperación")
    creado_en = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Fecha de Creación"
    )
    usado = models.BooleanField(
        default=False, 
        verbose_name="Token Usado"
    )
    intentos = models.IntegerField(
        default=0, 
        verbose_name="Intentos de Verificación"
    )
    ip_solicitud = models.GenericIPAddressField(
        blank=True, 
        null=True, 
        verbose_name="IP de Solicitud"
    )
    
    class Meta:
        verbose_name = 'Token de Recuperación'
        verbose_name_plural = 'Tokens de Recuperación'
        ordering = ['-creado_en']
        indexes = [
            models.Index(fields=['codigo', 'usado']),
            models.Index(fields=['usuario', 'usado']),
            models.Index(fields=['creado_en']),
        ]
    
    def __str__(self):
        estado = "Usado" if self.usado else "Activo"
        return f"Token {self.codigo} para {self.email} ({estado})"
    
    @classmethod
    def generar_codigo(cls):
        """Genera un código de 6 dígitos único"""
        max_intentos = 10
        for _ in range(max_intentos):
            codigo = ''.join(random.choices(string.digits, k=6))
            
            # Verificar que no exista un código activo igual
            if not cls.objects.filter(
                codigo=codigo, 
                usado=False,
                creado_en__gte=timezone.now() - timedelta(hours=1)
            ).exists():
                return codigo
        
        # Si no se pudo generar uno único, usar timestamp
        return str(int(timezone.now().timestamp()))[-6:]
    
    @classmethod
    def crear_token(cls, usuario, ip_address=None):
        """Crea un nuevo token para el usuario"""
        # Invalidar tokens anteriores no usados del mismo usuario
        cls.objects.filter(
            usuario=usuario, 
            usado=False
        ).update(usado=True)
        
        # Crear nuevo token
        token = cls.objects.create(
            usuario=usuario,
            codigo=cls.generar_codigo(),
            email=usuario.email,
            ip_solicitud=ip_address
        )
        return token
    
    def es_valido(self):
        """
        Verifica si el token es válido
        Returns: (bool, str) - (es_valido, mensaje)
        """
        if self.usado:
            return False, "Este código ya ha sido utilizado"
        
        if self.intentos >= 5:
            return False, "Demasiados intentos fallidos. Solicita un nuevo código"
        
        # Expiración: 15 minutos
        expiracion = self.creado_en + timedelta(minutes=15)
        if timezone.now() > expiracion:
            return False, "El código ha expirado. Solicita uno nuevo"
        
        return True, "Código válido"
    
    def incrementar_intento(self):
        """Incrementa el contador de intentos fallidos"""
        self.intentos += 1
        self.save(update_fields=['intentos'])
        
        # Si supera 5 intentos, invalidar el token
        if self.intentos >= 5:
            self.usado = True
            self.save(update_fields=['usado'])
    
    def marcar_usado(self):
        """Marca el token como usado exitosamente"""
        self.usado = True
        self.save(update_fields=['usado'])
    
    def tiempo_restante(self):
        """
        Calcula el tiempo restante antes de la expiración en segundos
        Returns: int - segundos restantes (0 si ya expiró)
        """
        expiracion = self.creado_en + timedelta(minutes=15)
        restante = expiracion - timezone.now()
        return max(0, int(restante.total_seconds()))
    
    def tiempo_restante_str(self):
        """
        Devuelve el tiempo restante en formato legible
        Returns: str - formato "X minutos Y segundos"
        """
        segundos = self.tiempo_restante()
        if segundos <= 0:
            return "Expirado"
        
        minutos = segundos // 60
        segundos_restantes = segundos % 60
        
        if minutos > 0:
            return f"{minutos} min {segundos_restantes} seg"
        else:
            return f"{segundos_restantes} segundos"
    
    @classmethod
    def limpiar_tokens_expirados(cls):
        """
        Método para limpiar tokens expirados (puede ejecutarse periódicamente)
        """
        hace_24_horas = timezone.now() - timedelta(hours=24)
        tokens_eliminados = cls.objects.filter(
            creado_en__lt=hace_24_horas
        ).delete()
        return tokens_eliminados[0] if tokens_eliminados else 0
    
    def get_info_seguridad(self):
        """Devuelve información de seguridad del token"""
        return {
            'intentos_restantes': max(0, 5 - self.intentos),
            'tiempo_restante': self.tiempo_restante(),
            'tiempo_restante_str': self.tiempo_restante_str(),
            'ip_solicitud': self.ip_solicitud,
            'creado_en': self.creado_en,
            'es_valido': self.es_valido()[0]
        }