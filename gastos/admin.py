# gastos/admin.py
from django.contrib import admin
from .models import TipoGasto, Gasto

@admin.register(TipoGasto)
class TipoGastoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'descripcion']
    list_filter = ['nombre']
    search_fields = ['nombre', 'descripcion']

@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'tipo_gasto', 'descripcion', 'monto', 'id_usuario']
    list_filter = ['tipo_gasto', 'fecha', 'id_usuario']
    search_fields = ['descripcion', 'id_usuario__username']
    date_hierarchy = 'fecha'
    list_per_page = 20
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tipo_gasto', 'id_usuario')