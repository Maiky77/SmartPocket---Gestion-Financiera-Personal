from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('authentication.urls')),
    path('gastos/', include('gastos.urls')),
    path('presupuestos/', include('presupuestos.urls')),
    path('recomendaciones/', include('recomendaciones.urls')),
    path('estadisticas/', include('estadisticas.urls')),
]

