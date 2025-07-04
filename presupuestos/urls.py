# presupuestos/urls.py
from django.urls import path
from . import views

app_name = 'presupuestos'

urlpatterns = [
    path('', views.presupuestos_view, name='presupuestos'),
    path('editar/<int:id_presupuesto>/', views.editar_presupuesto_view, name='editar_presupuesto'),
    path('eliminar/<int:id_presupuesto>/', views.eliminar_presupuesto_view, name='eliminar_presupuesto'),
    path('toggle/<int:id_presupuesto>/', views.toggle_presupuesto_view, name='toggle_presupuesto'),
    path('alerta/<int:id_alerta>/vista/', views.marcar_alerta_vista, name='marcar_alerta_vista'),
]