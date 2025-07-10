# authentication/management/commands/validar_migracion.py
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

# Importar modelos según diagrama original
from authentication.models import Usuario, TokenRecuperacion
from gastos.models import TipoGasto, Gasto
from presupuestos.models import Presupuesto, AlertaPresupuesto
from recomendaciones.models import (
    TipoRecomendacion, RecomendacionGenerada, 
    PatronUsuario, EstadisticaComparativa
)
from estadisticas.models import EstadisticaUsuario, Reporte


class Command(BaseCommand):
    help = 'Valida que la migración SQLite→MySQL fue exitosa y respeta el diagrama original'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detallado',
            action='store_true',
            help='Muestra información detallada de la validación',
        )

    def handle(self, *args, **options):
        self.detallado = options['detallado']
        
        self.stdout.write(self.style.SUCCESS("="*80))
        self.stdout.write(self.style.SUCCESS("🎯 SMARTPOCKET - VALIDACIÓN DE MIGRACIÓN SQLite→MySQL"))
        self.stdout.write(self.style.SUCCESS("="*80))
        
        # Ejecutar validaciones
        conexion_ok = self.validar_conexion_mysql()
        diagrama_ok = self.validar_diagrama_clases()
        fks_ok = self.validar_relaciones_fk()
        datos = self.validar_datos_migrados()
        categorias_ok = self.validar_categorias_gasto()
        indices_count = self.validar_indices_mysql()
        
        # Generar reporte final
        puntuacion = self.generar_reporte_final(
            conexion_ok, diagrama_ok, fks_ok, 
            datos, categorias_ok, indices_count
        )
        
        if puntuacion >= 90:
            self.stdout.write(self.style.SUCCESS("🎉 MIGRACIÓN COMPLETAMENTE EXITOSA"))
        elif puntuacion >= 70:
            self.stdout.write(self.style.WARNING("⚠️ MIGRACIÓN EXITOSA CON OBSERVACIONES"))
        else:
            self.stdout.write(self.style.ERROR("❌ MIGRACIÓN CON PROBLEMAS"))

    def print_header(self, title):
        """Imprime encabezado formateado"""
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.HTTP_INFO(f"🎯 {title}"))
        self.stdout.write("="*80)

    def print_success(self, message):
        """Imprime mensaje de éxito"""
        self.stdout.write(self.style.SUCCESS(f"✅ {message}"))

    def print_error(self, message):
        """Imprime mensaje de error"""
        self.stdout.write(self.style.ERROR(f"❌ {message}"))

    def print_info(self, message):
        """Imprime información"""
        self.stdout.write(self.style.HTTP_INFO(f"📊 {message}"))

    def validar_conexion_mysql(self):
        """Valida la conexión a MySQL"""
        self.print_header("VALIDACIÓN DE CONEXIÓN MYSQL")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()[0]
                self.print_success(f"Conexión MySQL exitosa: {version}")
                
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()[0]
                self.print_success(f"Base de datos actual: {db_name}")
                
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                self.print_info(f"Tablas encontradas: {len(tables)}")
                
                if self.detallado:
                    for table in tables:
                        self.stdout.write(f"  - {table[0]}")
                
                return True
        except Exception as e:
            self.print_error(f"Error de conexión MySQL: {e}")
            return False

    def validar_diagrama_clases(self):
        """Valida que todas las clases del diagrama original estén implementadas"""
        self.print_header("VALIDACIÓN DEL DIAGRAMA DE CLASES ORIGINAL")
        
        clases_esperadas = {
            'Usuario': Usuario,
            'TokenRecuperacion': TokenRecuperacion,
            'TipoGasto': TipoGasto,
            'Gasto': Gasto,
            'Presupuesto': Presupuesto,
            'AlertaPresupuesto': AlertaPresupuesto,
            'TipoRecomendacion': TipoRecomendacion,
            'RecomendacionGenerada': RecomendacionGenerada,
            'PatronUsuario': PatronUsuario,
            'EstadisticaComparativa': EstadisticaComparativa,
            'EstadisticaUsuario': EstadisticaUsuario,
            'Reporte': Reporte,
        }
        
        clases_validas = 0
        
        for nombre_clase, modelo in clases_esperadas.items():
            try:
                # Verificar que la tabla existe
                table_name = modelo._meta.db_table
                with connection.cursor() as cursor:
                    cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                    if cursor.fetchone():
                        self.print_success(f"Clase {nombre_clase} → Tabla {table_name} ✓")
                        clases_validas += 1
                    else:
                        self.print_error(f"Clase {nombre_clase} → Tabla {table_name} NO ENCONTRADA")
            except Exception as e:
                self.print_error(f"Error validando {nombre_clase}: {e}")
        
        self.print_info(f"Clases validadas: {clases_validas}/{len(clases_esperadas)}")
        return clases_validas == len(clases_esperadas)

    def validar_relaciones_fk(self):
        """Valida las relaciones Foreign Key según el diagrama"""
        self.print_header("VALIDACIÓN DE RELACIONES (FOREIGN KEYS)")
        
        relaciones_esperadas = [
            ('gastos_gasto', 'id_usuario_id', 'authentication_usuario'),
            ('gastos_gasto', 'tipo_gasto_id', 'gastos_tipogasto'),
            ('presupuestos_presupuesto', 'id_usuario_id', 'authentication_usuario'),
            ('presupuestos_presupuesto', 'categoria_id', 'gastos_tipogasto'),
            ('presupuestos_alertapresupuesto', 'presupuesto_id', 'presupuestos_presupuesto'),
            ('recomendaciones_recomendaciongenerada', 'usuario_id', 'authentication_usuario'),
            ('recomendaciones_patronusuario', 'usuario_id', 'authentication_usuario'),
            ('estadisticas_estadisticausuario', 'usuario_id', 'authentication_usuario'),
            ('estadisticas_reporte', 'usuario_id', 'authentication_usuario'),
            ('authentication_tokenrecuperacion', 'usuario_id', 'authentication_usuario'),
        ]
        
        fks_validas = 0
        
        with connection.cursor() as cursor:
            for tabla, columna_fk, tabla_ref in relaciones_esperadas:
                try:
                    query = """
                    SELECT COUNT(*) 
                    FROM information_schema.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = DATABASE()
                        AND TABLE_NAME = %s 
                        AND COLUMN_NAME = %s 
                        AND REFERENCED_TABLE_NAME = %s
                    """
                    cursor.execute(query, [tabla, columna_fk, tabla_ref])
                    result = cursor.fetchone()[0]
                    
                    if result > 0:
                        self.print_success(f"FK: {tabla}.{columna_fk} → {tabla_ref} ✓")
                        fks_validas += 1
                    else:
                        self.print_error(f"FK: {tabla}.{columna_fk} → {tabla_ref} NO ENCONTRADA")
                        
                except Exception as e:
                    self.print_error(f"Error validando FK {tabla}.{columna_fk}: {e}")
        
        self.print_info(f"Foreign Keys validadas: {fks_validas}/{len(relaciones_esperadas)}")
        return fks_validas >= len(relaciones_esperadas) * 0.8  # Al menos 80%

    def validar_datos_migrados(self):
        """Valida que los datos se migraron correctamente"""
        self.print_header("VALIDACIÓN DE DATOS MIGRADOS")
        
        contadores = {}
        
        modelos_a_validar = [
            ('Usuarios', Usuario),
            ('TiposGasto', TipoGasto),
            ('Gastos', Gasto),
            ('Presupuestos', Presupuesto),
            ('AlertasPresupuesto', AlertaPresupuesto),
            ('TiposRecomendacion', TipoRecomendacion),
            ('RecomendacionesGeneradas', RecomendacionGenerada),
            ('PatronesUsuario', PatronUsuario),
            ('EstadisticasComparativas', EstadisticaComparativa),
            ('EstadisticasUsuario', EstadisticaUsuario),
            ('Reportes', Reporte),
            ('TokensRecuperacion', TokenRecuperacion),
        ]
        
        for nombre, modelo in modelos_a_validar:
            try:
                count = modelo.objects.count()
                contadores[nombre] = count
                self.print_info(f"{nombre}: {count} registros")
            except Exception as e:
                self.print_error(f"Error contando {nombre}: {e}")
                contadores[nombre] = -1
        
        return contadores

    def validar_categorias_gasto(self):
        """Valida que las categorías de gasto estén correctas según el mockup"""
        self.print_header("VALIDACIÓN DE CATEGORÍAS DE GASTO")
        
        categorias_esperadas = [
            'COMIDA', 'TRANSPORTE', 'ENTRETENIMIENTO', 
            'EDUCACION', 'INTERNET', 'VIAJES', 'ROPA', 'OTROS'
        ]
        
        try:
            categorias_db = list(TipoGasto.objects.values_list('nombre', flat=True))
            
            categorias_validas = 0
            for categoria in categorias_esperadas:
                if categoria in categorias_db:
                    self.print_success(f"Categoría {categoria} ✓")
                    categorias_validas += 1
                else:
                    self.print_error(f"Categoría {categoria} FALTANTE")
            
            if self.detallado:
                self.print_info(f"Categorías en DB: {categorias_db}")
            
            return categorias_validas == len(categorias_esperadas)
            
        except Exception as e:
            self.print_error(f"Error validando categorías: {e}")
            return False

    def validar_indices_mysql(self):
        """Valida que los índices estén creados"""
        self.print_header("VALIDACIÓN DE ÍNDICES MYSQL")
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT INDEX_NAME 
                    FROM information_schema.STATISTICS 
                    WHERE TABLE_SCHEMA = DATABASE()
                        AND INDEX_NAME NOT IN ('PRIMARY')
                """)
                indices_db = [row[0] for row in cursor.fetchall()]
                
                # Contar índices personalizados (que empiecen con idx_)
                indices_personalizados = [idx for idx in indices_db if idx.startswith('idx_')]
                
                self.print_info(f"Índices personalizados encontrados: {len(indices_personalizados)}")
                
                if self.detallado:
                    for indice in indices_personalizados:
                        self.stdout.write(f"  - {indice}")
                
                return len(indices_personalizados)
                
        except Exception as e:
            self.print_error(f"Error validando índices: {e}")
            return 0

    def generar_reporte_final(self, conexion_ok, diagrama_ok, fks_ok, datos, categorias_ok, indices_count):
        """Genera reporte final de la validación"""
        self.print_header("REPORTE FINAL DE VALIDACIÓN")
        
        self.stdout.write("📋 RESUMEN DE VALIDACIÓN:")
        self.stdout.write(f"   • Conexión MySQL: {'✅ OK' if conexion_ok else '❌ ERROR'}")
        self.stdout.write(f"   • Diagrama de Clases: {'✅ OK' if diagrama_ok else '❌ ERROR'}")
        self.stdout.write(f"   • Foreign Keys: {'✅ OK' if fks_ok else '❌ ERROR'}")
        self.stdout.write(f"   • Categorías de Gasto: {'✅ OK' if categorias_ok else '❌ ERROR'}")
        self.stdout.write(f"   • Índices MySQL: {indices_count} creados")
        
        self.stdout.write("\n📊 DATOS MIGRADOS:")
        for tabla, count in datos.items():
            status = "✅" if count >= 0 else "❌"
            self.stdout.write(f"   • {tabla}: {count} registros {status}")
        
        # Calcular puntuación final
        puntuacion = 0
        if conexion_ok: puntuacion += 20
        if diagrama_ok: puntuacion += 25
        if fks_ok: puntuacion += 25
        if categorias_ok: puntuacion += 15
        if indices_count >= 3: puntuacion += 15
        
        self.stdout.write(f"\n🎯 PUNTUACIÓN FINAL: {puntuacion}/100")
        
        if puntuacion >= 90:
            self.stdout.write(self.style.SUCCESS("🎉 MIGRACIÓN EXITOSA - SISTEMA COMPLETAMENTE OPTIMIZADO"))
        elif puntuacion >= 70:
            self.stdout.write(self.style.WARNING("⚠️ MIGRACIÓN EXITOSA - ALGUNAS OPTIMIZACIONES PENDIENTES"))
        else:
            self.stdout.write(self.style.ERROR("❌ MIGRACIÓN CON PROBLEMAS - REQUIERE REVISIÓN"))
        
        return puntuacion