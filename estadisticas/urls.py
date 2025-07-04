# estadisticas/urls.py
from django.urls import path
from . import views

app_name = 'estadisticas'

urlpatterns = [
    path('', views.estadisticas_view, name='estadisticas'),
    path('ajax/grafico/', views.datos_grafico_ajax, name='datos_grafico_ajax'),
    path('exportar/', views.exportar_reporte, name='exportar_reporte'),
]