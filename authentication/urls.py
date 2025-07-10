# authentication/urls.py
from django.urls import path
from . import views
from django.urls import path, include  # ← Faltaba 'include'

app_name = 'authentication'

urlpatterns = [
 path('', views.dashboard_view, name='dashboard'),  # Página principal
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/eliminar-foto/', views.eliminar_foto_perfil, name='eliminar_foto_perfil'),
    
    # Registro OPTIMIZADO con email automático
    path('register/', views.register_view_con_email_automatico, name='register'),  # ← NUEVA VISTA OPTIMIZADA
    path('registro/', views.register_view_con_email_automatico, name='registro_mejorado'),  # Alias
    
    # Mantener vista anterior como backup (temporal)
    path('register-old/', views.register_view_mejorado, name='register_old'),  # ← BACKUP TEMPORAL
    
    # ==================== RUTAS DE RECUPERACIÓN DE CONTRASEÑA ====================
    path('recuperar_contrasena/', views.recuperar_contrasena_solicitud, name='recuperar_contrasena'),
    path('verificar_codigo/', views.verificar_codigo_recuperacion, name='verificar_codigo'),
    path('nueva_contrasena/', views.nueva_contrasena_recuperacion, name='nueva_contrasena'),
    
    # AJAX para recuperación
    path('reenviar_codigo/', views.reenviar_codigo_recuperacion, name='reenviar_codigo'),

    # ==================== VISTA DE PRUEBA OPTIMIZADA ====================
    path('test-email/', views.test_email_view, name='test_email'),

    # ==================== RUTAS AJAX PARA REGISTRO MEJORADO ====================
    path('validar-campo/', views.validar_campo_ajax, name='validar_campo_ajax'),
    path('registro-ajax/', views.register_view_mejorado_ajax, name='registro_ajax'),
]