# gastos/management/commands/poblar_categorias.py
from django.core.management.base import BaseCommand
from gastos.models import TipoGasto

class Command(BaseCommand):
    help = 'Poblar las categorías de gastos en la base de datos'

    def handle(self, *args, **options):
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
            tipo_gasto, created = TipoGasto.objects.get_or_create(
                nombre=codigo,
                defaults={'descripcion': f'Categoría de {nombre_display.lower()}'}
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Categoría "{nombre_display}" creada')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠️ Categoría "{nombre_display}" ya existe')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎯 COMPLETADO: {created_count} categorías nuevas creadas')
        )
        self.stdout.write(
            self.style.SUCCESS(f'📊 Total de categorías en BD: {TipoGasto.objects.count()}')
        )