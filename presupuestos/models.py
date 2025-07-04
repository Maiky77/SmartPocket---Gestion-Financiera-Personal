# presupuestos/models.py
from django.db import models
from django.utils import timezone
from authentication.models import Usuario
from gastos.models import TipoGasto

class Presupuesto(models.Model):
    """
    Modelo para los presupuestos mensuales por categoría
    """
    id_presupuesto = models.AutoField(primary_key=True)
    categoria = models.ForeignKey(TipoGasto, on_delete=models.CASCADE, verbose_name="Categoría")
    monto_maximo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Máximo")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin")
    id_usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, verbose_name="Usuario")
    fecha_creacion = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Creación")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        verbose_name = "Presupuesto"
        verbose_name_plural = "Presupuestos"
        ordering = ['-fecha_creacion']
        # Un usuario no puede tener dos presupuestos activos para la misma categoría en el mismo período
        unique_together = ['categoria', 'id_usuario', 'fecha_inicio', 'fecha_fin']
    
    def __str__(self):
        return f"Presupuesto {self.categoria.get_nombre_display()} - S/. {self.monto_maximo} ({self.fecha_inicio} - {self.fecha_fin})"
    
    def get_gasto_total_actual(self):
        """
        Calcula el total gastado en esta categoría durante el período del presupuesto
        """
        from gastos.models import Gasto
        
        gastos = Gasto.objects.filter(
            id_usuario=self.id_usuario,
            tipo_gasto=self.categoria,
            fecha__gte=self.fecha_inicio,
            fecha__lte=self.fecha_fin
        )
        return sum(gasto.monto for gasto in gastos)
    
    def get_porcentaje_usado(self):
        """
        Calcula el porcentaje del presupuesto que se ha usado
        """
        gasto_actual = self.get_gasto_total_actual()
        if self.monto_maximo > 0:
            return (gasto_actual / self.monto_maximo) * 100
        return 0
    
    def get_monto_restante(self):
        """
        Calcula cuánto dinero queda en el presupuesto
        """
        return self.monto_maximo - self.get_gasto_total_actual()
    
    def esta_cerca_del_limite(self, porcentaje_alerta=80):
        """
        Verifica si el presupuesto está cerca del límite (por defecto 80%)
        """
        return self.get_porcentaje_usado() >= porcentaje_alerta
    
    def esta_excedido(self):
        """
        Verifica si el presupuesto ha sido excedido
        """
        return self.get_gasto_total_actual() > self.monto_maximo
    
    def esta_vigente(self):
        """
        Verifica si el presupuesto está vigente en la fecha actual
        """
        hoy = timezone.now().date()
        return self.fecha_inicio <= hoy <= self.fecha_fin and self.activo

class AlertaPresupuesto(models.Model):
    """
    Modelo para las alertas de presupuesto
    """
    TIPOS_ALERTA = [
        ('CERCA_LIMITE', 'Cerca del límite'),
        ('LIMITE_EXCEDIDO', 'Límite excedido'),
        ('ADVERTENCIA', 'Advertencia general'),
    ]
    
    id_alerta = models.AutoField(primary_key=True)
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE, verbose_name="Presupuesto")
    tipo_alerta = models.CharField(max_length=20, choices=TIPOS_ALERTA, verbose_name="Tipo de Alerta")
    mensaje = models.TextField(verbose_name="Mensaje de Alerta")
    fecha_creacion = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Creación")
    vista = models.BooleanField(default=False, verbose_name="Vista")
    
    class Meta:
        verbose_name = "Alerta de Presupuesto"
        verbose_name_plural = "Alertas de Presupuesto"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Alerta {self.get_tipo_alerta_display()} - {self.presupuesto.categoria.get_nombre_display()}"
    
    @classmethod
    def crear_alerta_automatica(cls, presupuesto):
        """
        Crea alertas automáticas basadas en el estado del presupuesto
        """
        porcentaje_usado = presupuesto.get_porcentaje_usado()
        
        # Verificar si ya existe una alerta reciente para este presupuesto
        alertas_recientes = cls.objects.filter(
            presupuesto=presupuesto,
            fecha_creacion__date=timezone.now().date()
        )
        
        if alertas_recientes.exists():
            return None  # Ya hay una alerta hoy
        
        if presupuesto.esta_excedido():
            mensaje = f"¡Presupuesto excedido! Has gastado S/. {presupuesto.get_gasto_total_actual():.2f} de S/. {presupuesto.monto_maximo:.2f} en {presupuesto.categoria.get_nombre_display()}."
            return cls.objects.create(
                presupuesto=presupuesto,
                tipo_alerta='LIMITE_EXCEDIDO',
                mensaje=mensaje
            )
        elif presupuesto.esta_cerca_del_limite():
            mensaje = f"Cerca del límite: Has usado {porcentaje_usado:.1f}% de tu presupuesto en {presupuesto.categoria.get_nombre_display()}."
            return cls.objects.create(
                presupuesto=presupuesto,
                tipo_alerta='CERCA_LIMITE',
                mensaje=mensaje
            )