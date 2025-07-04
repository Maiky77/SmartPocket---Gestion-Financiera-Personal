# recomendaciones/urls.py
from django.urls import path
from . import views

app_name = 'recomendaciones'

urlpatterns = [
    path('', views.recomendaciones_view, name='recomendaciones'),
    path('detalle/<int:recomendacion_id>/', views.detalle_recomendacion, name='detalle_recomendacion'),
    path('descartar/<int:recomendacion_id>/', views.descartar_recomendacion, name='descartar_recomendacion'),
    path('regenerar/', views.regenerar_recomendaciones, name='regenerar_recomendaciones'),
    path('patrones/', views.analisis_patrones, name='analisis_patrones'),
    
    # AJAX endpoints
    path('ajax/vista/<int:recomendacion_id>/', views.marcar_vista_ajax, name='marcar_vista_ajax'),
    path('ajax/aplicada/<int:recomendacion_id>/', views.marcar_aplicada_ajax, name='marcar_aplicada_ajax'),
]