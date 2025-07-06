# authentication/urls.py
from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    # Rutas principales
    path('', views.dashboard_view, name='dashboard'),  # Página principal
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/eliminar-foto/', views.eliminar_foto_perfil, name='eliminar_foto_perfil'),
    
    # Registro
    path('register/', views.register_view, name='register'),  # Registro básico (mantener compatibilidad)
    path('registro/', views.register_view_mejorado, name='registro_mejorado'),  # Registro mejorado
    
    # ==================== RUTAS DE RECUPERACIÓN DE CONTRASEÑA ====================
    path('recuperar_contrasena/', views.recuperar_contrasena_solicitud, name='recuperar_contrasena'),
    path('verificar_codigo/', views.verificar_codigo_recuperacion, name='verificar_codigo'),
    path('nueva_contrasena/', views.nueva_contrasena_recuperacion, name='nueva_contrasena'),
    
    # AJAX para recuperación
    path('reenviar_codigo/', views.reenviar_codigo_recuperacion, name='reenviar_codigo'),

        # ==================== RUTAS AJAX PARA REGISTRO MEJORADO ====================
    path('validar-campo/', views.validar_campo_ajax, name='validar_campo_ajax'),
    path('registro-ajax/', views.register_view_mejorado_ajax, name='registro_ajax'),
    path('register/', views.register_view_mejorado, name='register'),


    path('validar-campo/', views.validar_campo_ajax, name='validar_campo_ajax'),
]