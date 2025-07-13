from django.apps import AppConfig
import os

class GastosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gastos'
    
    def ready(self):
        """Ejecutar cuando la app esté lista"""
        # Solo ejecutar en producción (Railway)
        if os.environ.get('RAILWAY_ENVIRONMENT') == 'production':
            # Usar un pequeño delay para asegurar que la DB esté lista
            import threading
            import time
            
            def delayed_populate():
                time.sleep(3)  # Esperar 3 segundos
                self.poblar_categorias_automatico()
            
            # Ejecutar en un hilo separado para no bloquear el startup
            thread = threading.Thread(target=delayed_populate)
            thread.daemon = True
            thread.start()
    
    def poblar_categorias_automatico(self):
        """Poblar categorías automáticamente si no existen"""
        try:
            from django.db import connection
            from .models import TipoGasto
            
            # Verificar conexión a la base de datos
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            
            print("🔗 Conexión a base de datos exitosa")
            
            # Verificar si ya existen categorías
            count_existing = TipoGasto.objects.count()
            print(f"📊 Categorías existentes en BD: {count_existing}")
            
            if count_existing > 0:
                print("✅ Las categorías ya existen, no es necesario crearlas")
                return
            
            print("🚀 Creando categorías automáticamente...")
            
            # Crear las categorías
            categorias = [
                ('COMIDA', 'Comida'),
                ('TRANSPORTE', 'Transporte'),
                ('ENTRETENIMIENTO', 'Entretenimiento'),
                ('EDUCACION', 'Educación'),
                ('INTERNET', 'Internet'),
                ('VIAJES', 'Viajes'),
                ('ROPA', 'Ropa'),
                ('OTROS', 'Otros'),
            ]
            
            created_count = 0
            for codigo, nombre_display in categorias:
                try:
                    tipo_gasto, created = TipoGasto.objects.get_or_create(
                        nombre=codigo,
                        defaults={'descripcion': f'Categoría de {nombre_display.lower()}'}
                    )
                    
                    if created:
                        created_count += 1
                        print(f"✅ Categoría '{nombre_display}' creada")
                    else:
                        print(f"⚠️ Categoría '{nombre_display}' ya existía")
                        
                except Exception as e:
                    print(f"❌ Error al crear categoría '{nombre_display}': {e}")
            
            total_final = TipoGasto.objects.count()
            print(f"🎯 RESULTADO: {created_count} nuevas categorías creadas")
            print(f"📈 Total de categorías en BD: {total_final}")
            print("🚀 ¡Categorías disponibles para los dropdowns!")
            
        except Exception as e:
            print(f"🚨 Error en población automática de categorías: {e}")
            # No lanzar excepción para no interrumpir el startup de la app
            pass