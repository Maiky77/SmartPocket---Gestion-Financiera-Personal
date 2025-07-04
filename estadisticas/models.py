# estadisticas/models.py
from django.db import models
from django.utils import timezone
from authentication.models import Usuario
from gastos.models import TipoGasto

class EstadisticaUsuario(models.Model):
    """Estadísticas calculadas del usuario según diseño UML"""
    id_estadistica = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    tipo_grafico = models.CharField(max_length=50, choices=[
        ('BARRAS', 'Gráfico de Barras'),
        ('LINEA', 'Gráfico de Línea'),
        ('CIRCULAR', 'Gráfico Circular'),
        ('AREA', 'Gráfico de Área'),
    ])
    promedio_gastos = models.DecimalField(max_digits=10, decimal_places=2)
    periodo = models.CharField(max_length=20, choices=[
        ('SEMANAL', 'Semanal'),
        ('MENSUAL', 'Mensual'),
        ('ANUAL', 'Anual'),
    ])
    fecha_generacion = models.DateTimeField(default=timezone.now)
    datos_json = models.JSONField(default=dict)  # Para almacenar datos del gráfico
    
    def __str__(self):
        return f"Estadística {self.tipo_grafico} - {self.usuario.username}"
    
    class Meta:
        verbose_name = "Estadística de Usuario"
        verbose_name_plural = "Estadísticas de Usuarios"

class Reporte(models.Model):
    """Reportes generados según diseño UML"""
    id_reporte = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    formato = models.CharField(max_length=10, choices=[
        ('PDF', 'PDF'),
        ('EXCEL', 'Excel'),
        ('CSV', 'CSV'),
    ])
    tipo_reporte = models.CharField(max_length=20, choices=[
        ('MENSUAL', 'Reporte Mensual'),
        ('ANUAL', 'Reporte Anual'),
        ('PERSONALIZADO', 'Reporte Personalizado'),
    ])
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    fecha_generacion = models.DateTimeField(default=timezone.now)
    archivo_path = models.CharField(max_length=500, blank=True, null=True)
    
    def __str__(self):
        return f"Reporte {self.tipo_reporte} - {self.usuario.username}"
    
    class Meta:
        verbose_name = "Reporte"
        verbose_name_plural = "Reportes"
        ordering = ['-fecha_generacion']