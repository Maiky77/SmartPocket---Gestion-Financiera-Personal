from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('authentication.urls')),
    path('gastos/', include('gastos.urls')),
    path('presupuestos/', include('presupuestos.urls')),
    path('recomendaciones/', include('recomendaciones.urls')),
    path('estadisticas/', include('estadisticas.urls')),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Agregar también archivos estáticos en desarrollo
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else None)
else:
    # En producción (Railway), también intentar servir media si WhiteNoise no lo hace
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)