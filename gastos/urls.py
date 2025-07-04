# gastos/urls.py
from django.urls import path
from . import views

app_name = 'gastos'

urlpatterns = [
    path('', views.gastos_view, name='gastos'),
    path('editar/<int:gasto_id>/', views.editar_gasto, name='editar_gasto'),
    path('eliminar/<int:gasto_id>/', views.eliminar_gasto, name='eliminar_gasto'),
]