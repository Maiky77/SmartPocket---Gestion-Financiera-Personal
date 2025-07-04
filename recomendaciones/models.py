# recomendaciones/models.py
from django.db import models
from django.utils import timezone
from authentication.models import Usuario
from gastos.models import TipoGasto
from decimal import Decimal

class TipoRecomendacion(models.Model):
    """
    Tipos de recomendaciones disponibles en el sistema
    """
    TIPOS = [
        ('REDUCIR_GASTO', 'Reducir Gasto'),
        ('OPTIMIZAR_CATEGORIA', 'Optimizar Categoría'),
        ('PATRON_TEMPORAL', 'Patrón Temporal'),
        ('META_AHORRO', 'Meta de Ahorro'),
        ('ALERTA_LIMITE', 'Alerta de Límite'),
        ('HABITO_FINANCIERO', 'Hábito Financiero'),
        ('COMPARATIVA', 'Comparativa con Promedio'),
    ]
    
    nombre = models.CharField(max_length=50, choices=TIPOS, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Tipo de Recomendación"
        verbose_name_plural = "Tipos de Recomendación"
    
    def __str__(self):
        return self.get_nombre_display()

class RecomendacionGenerada(models.Model):
    """
    Recomendaciones generadas automáticamente por el sistema IA
    """
    PRIORIDADES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]
    
    id_recomendacion = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, verbose_name="Usuario")
    tipo_recomendacion = models.ForeignKey(TipoRecomendacion, on_delete=models.CASCADE, verbose_name="Tipo")
    categoria_relacionada = models.ForeignKey(TipoGasto, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Categoría Relacionada")
    
    titulo = models.CharField(max_length=200, verbose_name="Título")
    mensaje = models.TextField(verbose_name="Mensaje de Recomendación")
    
    # Datos cuantitativos para la recomendación
    valor_actual = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Valor Actual")
    valor_objetivo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Valor Objetivo")
    ahorro_potencial = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Ahorro Potencial")
    porcentaje_impacto = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Porcentaje de Impacto")
    
    prioridad = models.CharField(max_length=10, choices=PRIORIDADES, default='MEDIA', verbose_name="Prioridad")
    fecha_generacion = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Generación")
    fecha_expiracion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Expiración")
    
    vista = models.BooleanField(default=False, verbose_name="Vista por el Usuario")
    aplicada = models.BooleanField(default=False, verbose_name="Aplicada por el Usuario")
    activa = models.BooleanField(default=True, verbose_name="Activa")
    
    # Metadatos para el análisis
    periodo_analisis_dias = models.IntegerField(default=30, verbose_name="Período de Análisis (días)")
    confianza_algoritmo = models.DecimalField(max_digits=5, decimal_places=2, default=80.00, verbose_name="Confianza del Algoritmo (%)")
    
    class Meta:
        verbose_name = "Recomendación Generada"
        verbose_name_plural = "Recomendaciones Generadas"
        ordering = ['-fecha_generacion', '-prioridad']
    
    def __str__(self):
        return f"{self.titulo} - {self.usuario.username}"
    
    def esta_vigente(self):
        """Verifica si la recomendación está vigente"""
        if not self.activa:
            return False
        if self.fecha_expiracion and timezone.now() > self.fecha_expiracion:
            return False
        return True
    
    def marcar_como_vista(self):
        """Marca la recomendación como vista"""
        self.vista = True
        self.save()
    
    def marcar_como_aplicada(self):
        """Marca la recomendación como aplicada"""
        self.aplicada = True
        self.vista = True
        self.save()

class PatronUsuario(models.Model):
    """
    Análisis de patrones de gasto del usuario
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, verbose_name="Usuario")
    categoria = models.ForeignKey(TipoGasto, on_delete=models.CASCADE, verbose_name="Categoría")
    
    # Análisis temporal
    gasto_promedio_mensual = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Gasto Promedio Mensual")
    gasto_maximo_mensual = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Gasto Máximo Mensual")
    gasto_minimo_mensual = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Gasto Mínimo Mensual")
    
    # Frecuencia
    transacciones_promedio_mes = models.DecimalField(max_digits=5, decimal_places=1, verbose_name="Transacciones Promedio/Mes")
    dia_semana_mas_gasto = models.IntegerField(null=True, blank=True, verbose_name="Día de Semana con Más Gasto")
    hora_mas_frecuente = models.IntegerField(null=True, blank=True, verbose_name="Hora Más Frecuente")
    
    # Tendencias
    tendencia_crecimiento = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Tendencia de Crecimiento (%)")
    volatilidad = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Volatilidad")
    
    # Comparativas
    porcentaje_vs_total = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="% vs Total de Gastos")
    ranking_importancia = models.IntegerField(verbose_name="Ranking de Importancia")
    
    # Metadatos
    fecha_ultimo_analisis = models.DateTimeField(default=timezone.now, verbose_name="Fecha Último Análisis")
    periodo_analisis_meses = models.IntegerField(default=3, verbose_name="Período de Análisis (meses)")
    confiabilidad_datos = models.DecimalField(max_digits=5, decimal_places=2, default=100.00, verbose_name="Confiabilidad de Datos (%)")
    
    class Meta:
        verbose_name = "Patrón de Usuario"
        verbose_name_plural = "Patrones de Usuario"
        unique_together = ['usuario', 'categoria']
        ordering = ['ranking_importancia']
    
    def __str__(self):
        return f"Patrón {self.categoria.get_nombre_display()} - {self.usuario.username}"
    
    def necesita_actualizacion(self):
        """Verifica si el patrón necesita actualización"""
        dias_desde_actualizacion = (timezone.now() - self.fecha_ultimo_analisis).days
        return dias_desde_actualizacion > 7  # Actualizar semanalmente

class EstadisticaComparativa(models.Model):
    """
    Estadísticas comparativas para generar recomendaciones benchmarking
    """
    categoria = models.ForeignKey(TipoGasto, on_delete=models.CASCADE, verbose_name="Categoría")
    
    # Estadísticas globales del sistema
    promedio_sistema = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Promedio del Sistema")
    mediana_sistema = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Mediana del Sistema")
    percentil_25 = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Percentil 25")
    percentil_75 = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Percentil 75")
    percentil_90 = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Percentil 90")
    
    # Metadatos
    fecha_calculo = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Cálculo")
    usuarios_en_muestra = models.IntegerField(verbose_name="Usuarios en Muestra")
    periodo_meses = models.IntegerField(default=3, verbose_name="Período (meses)")
    
    class Meta:
        verbose_name = "Estadística Comparativa"
        verbose_name_plural = "Estadísticas Comparativas"
        unique_together = ['categoria', 'periodo_meses']
        ordering = ['-fecha_calculo']
    
    def __str__(self):
        return f"Stats {self.categoria.get_nombre_display()} - {self.periodo_meses}m"