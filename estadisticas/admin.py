# estadisticas/admin.py
from django.contrib import admin
from .models import EstadisticaUsuario, Reporte

@admin.register(EstadisticaUsuario)
class EstadisticaUsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tipo_grafico', 'periodo', 'promedio_gastos', 'fecha_generacion']
    list_filter = ['tipo_grafico', 'periodo', 'fecha_generacion']
    search_fields = ['usuario__username', 'usuario__email']
    ordering = ['-fecha_generacion']
    readonly_fields = ['fecha_generacion']

@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tipo_reporte', 'formato', 'fecha_inicio', 'fecha_fin', 'fecha_generacion']
    list_filter = ['formato', 'tipo_reporte', 'fecha_generacion']
    search_fields = ['usuario__username', 'usuario__email']
    ordering = ['-fecha_generacion']
    readonly_fields = ['fecha_generacion']