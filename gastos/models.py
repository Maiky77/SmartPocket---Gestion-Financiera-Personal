# gastos/models.py
from django.db import models
from django.utils import timezone
from authentication.models import Usuario

class TipoGasto(models.Model):
    """Categorías de gastos según mockup"""
    CATEGORIAS = [
        ('COMIDA', 'Comida'),
        ('TRANSPORTE', 'Transporte'),
        ('ENTRETENIMIENTO', 'Entretenimiento'),
        ('EDUCACION', 'Educación'),
        ('INTERNET', 'Internet'),
        ('VIAJES', 'Viajes'),
        ('ROPA', 'Ropa'),
        ('OTROS', 'Otros'),
    ]
    
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, choices=CATEGORIAS, unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return self.get_nombre_display()
    
    class Meta:
        verbose_name = "Tipo de Gasto"
        verbose_name_plural = "Tipos de Gastos"

class Gasto(models.Model):
    """Modelo de gastos según diseño UML"""
    id_gasto = models.AutoField(primary_key=True)
    tipo_gasto = models.ForeignKey(TipoGasto, on_delete=models.CASCADE, verbose_name="Categoría")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto")
    descripcion = models.CharField(max_length=255, verbose_name="Descripción")
    fecha = models.DateField(default=timezone.now, verbose_name="Fecha")
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, verbose_name="Usuario")
    fecha_registro = models.DateTimeField(default=timezone.now)
    
    def getMonto(self):
        return float(self.monto)
    
    def getTipoDescripcion(self):
        return f"{self.tipo_gasto.get_nombre_display()}: {self.descripcion}"
    
    def getFecha(self):
        return self.fecha
    
    def setMonto(self, m):
        self.monto = m
    
    def setTipoDescripcion(self, d):
        self.descripcion = d
    
    def setFecha(self, f):
        self.fecha = f
    
    def __str__(self):
        return f"{self.tipo_gasto} - S/.{self.monto} - {self.fecha}"
    
    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"
        ordering = ['-fecha', '-fecha_registro']