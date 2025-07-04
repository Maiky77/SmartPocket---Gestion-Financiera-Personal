# recomendaciones/algorithms.py
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Max, Min, Q
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta, datetime
from collections import defaultdict
import statistics

from .models import RecomendacionGenerada, PatronUsuario, EstadisticaComparativa, TipoRecomendacion
from gastos.models import Gasto, TipoGasto
from presupuestos.models import Presupuesto

class AnalizadorPatrones:
    """
    Clase principal para analizar patrones de gasto y generar recomendaciones inteligentes
    """
    
    def __init__(self, usuario):
        self.usuario = usuario
        self.hoy = timezone.now().date()
        self.hace_30_dias = self.hoy - timedelta(days=30)
        self.hace_90_dias = self.hoy - timedelta(days=90)
    
    def generar_todas_recomendaciones(self):
        """
        Genera todas las recomendaciones para el usuario
        """
        print(f"🤖 Generando recomendaciones para {self.usuario.username}")
        
        # Limpiar recomendaciones antiguas (más de 30 días)
        self._limpiar_recomendaciones_antiguas()
        
        # Actualizar patrones de usuario
        self._actualizar_patrones_usuario()
        
        # Generar diferentes tipos de recomendaciones
        recomendaciones_generadas = []
        
        recomendaciones_generadas.extend(self._analizar_gastos_excesivos())
        recomendaciones_generadas.extend(self._analizar_patrones_temporales())
        recomendaciones_generadas.extend(self._generar_metas_ahorro())
        recomendaciones_generadas.extend(self._analizar_comparativas())
        recomendaciones_generadas.extend(self._analizar_presupuestos())
        
        print(f"✅ Generadas {len(recomendaciones_generadas)} recomendaciones")
        return recomendaciones_generadas
    
    def _limpiar_recomendaciones_antiguas(self):
        """Elimina recomendaciones antiguas o ya no relevantes"""
        fecha_limite = timezone.now() - timedelta(days=30)
        eliminadas = RecomendacionGenerada.objects.filter(
            usuario=self.usuario,
            fecha_generacion__lt=fecha_limite,
            vista=False
        ).delete()
        
        # Desactivar recomendaciones vistas pero no aplicadas después de 7 días
        RecomendacionGenerada.objects.filter(
            usuario=self.usuario,
            vista=True,
            aplicada=False,
            fecha_generacion__lt=timezone.now() - timedelta(days=7)
        ).update(activa=False)
    
    def _actualizar_patrones_usuario(self):
        """Actualiza los patrones de gasto del usuario"""
        categorias = TipoGasto.objects.all()
        
        for categoria in categorias:
            # Obtener gastos de los últimos 3 meses
            gastos = Gasto.objects.filter(
                id_usuario=self.usuario,
                tipo_gasto=categoria,
                fecha__gte=self.hace_90_dias
            )
            
            if gastos.exists():
                patron, created = PatronUsuario.objects.get_or_create(
                    usuario=self.usuario,
                    categoria=categoria,
                    defaults={
                        'gasto_promedio_mensual': Decimal('0'),
                        'gasto_maximo_mensual': Decimal('0'),
                        'gasto_minimo_mensual': Decimal('0'),
                        'transacciones_promedio_mes': Decimal('0'),
                        'volatilidad': Decimal('0'),
                        'porcentaje_vs_total': Decimal('0'),
                        'ranking_importancia': 1,
                    }
                )
                
                # Calcular estadísticas
                montos_mensuales = self._calcular_gastos_mensuales(gastos)
                total_gastos_usuario = self._obtener_total_gastos_usuario()
                
                if montos_mensuales:
                    patron.gasto_promedio_mensual = Decimal(str(statistics.mean(montos_mensuales))).quantize(Decimal('0.01'))
                    patron.gasto_maximo_mensual = Decimal(str(max(montos_mensuales))).quantize(Decimal('0.01'))
                    patron.gasto_minimo_mensual = Decimal(str(min(montos_mensuales))).quantize(Decimal('0.01'))
                    
                    if len(montos_mensuales) > 1:
                        patron.volatilidad = Decimal(str(statistics.stdev(montos_mensuales))).quantize(Decimal('0.01'))
                    
                    patron.transacciones_promedio_mes = Decimal(str(gastos.count() / 3)).quantize(Decimal('0.1'))
                    
                    if total_gastos_usuario > 0:
                        patron.porcentaje_vs_total = (patron.gasto_promedio_mensual / total_gastos_usuario * 100).quantize(Decimal('0.01'))
                
                patron.fecha_ultimo_analisis = timezone.now()
                patron.save()
        
        # Actualizar rankings de importancia
        self._actualizar_rankings_importancia()
    
    def _calcular_gastos_mensuales(self, gastos):
        """Calcula gastos agrupados por mes"""
        gastos_por_mes = defaultdict(Decimal)
        
        for gasto in gastos:
            mes_key = f"{gasto.fecha.year}-{gasto.fecha.month:02d}"
            gastos_por_mes[mes_key] += gasto.monto
        
        return list(gastos_por_mes.values())
    
    def _obtener_total_gastos_usuario(self):
        """Obtiene el total de gastos del usuario en los últimos 30 días"""
        total = Gasto.objects.filter(
            id_usuario=self.usuario,
            fecha__gte=self.hace_30_dias
        ).aggregate(total=Sum('monto'))['total']
        
        return total or Decimal('0')
    
    def _actualizar_rankings_importancia(self):
        """Actualiza el ranking de importancia de las categorías"""
        patrones = PatronUsuario.objects.filter(usuario=self.usuario).order_by('-gasto_promedio_mensual')
        
        for index, patron in enumerate(patrones, 1):
            patron.ranking_importancia = index
            patron.save()
    
    def _analizar_gastos_excesivos(self):
        """Analiza gastos excesivos comparado con promedios"""
        recomendaciones = []
        
        # Obtener estadísticas comparativas actualizadas
        self._actualizar_estadisticas_comparativas()
        
        patrones = PatronUsuario.objects.filter(usuario=self.usuario, ranking_importancia__lte=5)
        
        for patron in patrones:
            try:
                stats = EstadisticaComparativa.objects.get(categoria=patron.categoria)
                
                # Si el usuario gasta más del percentil 75, generar recomendación
                if patron.gasto_promedio_mensual > stats.percentil_75:
                    exceso = patron.gasto_promedio_mensual - stats.promedio_sistema
                    porcentaje_exceso = ((patron.gasto_promedio_mensual / stats.promedio_sistema) - 1) * 100
                    
                    titulo = f"Optimización en {patron.categoria.get_nombre_display()}"
                    mensaje = (
                        f"Has gastado {porcentaje_exceso:.1f}% más que el promedio en "
                        f"{patron.categoria.get_nombre_display()}. "
                        f"Tu promedio mensual es S/. {patron.gasto_promedio_mensual:.2f}, "
                        f"mientras que el promedio general es S/. {stats.promedio_sistema:.2f}."
                    )
                    
                    prioridad = 'ALTA' if porcentaje_exceso > 50 else 'MEDIA'
                    
                    recomendacion = self._crear_recomendacion(
                        tipo='REDUCIR_GASTO',
                        categoria=patron.categoria,
                        titulo=titulo,
                        mensaje=mensaje,
                        valor_actual=patron.gasto_promedio_mensual,
                        valor_objetivo=stats.promedio_sistema,
                        ahorro_potencial=exceso,
                        porcentaje_impacto=porcentaje_exceso,
                        prioridad=prioridad
                    )
                    
                    if recomendacion:
                        recomendaciones.append(recomendacion)
                        
            except EstadisticaComparativa.DoesNotExist:
                continue
        
        return recomendaciones
    
    def _analizar_patrones_temporales(self):
        """Analiza patrones temporales para optimizaciones"""
        recomendaciones = []
        
        # Analizar gastos por día de la semana
        gastos_recientes = Gasto.objects.filter(
            id_usuario=self.usuario,
            fecha__gte=self.hace_30_dias
        )
        
        if gastos_recientes.count() < 10:  # Necesitamos datos suficientes
            return recomendaciones
        
        # Agrupar gastos por día de la semana
        gastos_por_dia = defaultdict(list)
        for gasto in gastos_recientes:
            dia_semana = gasto.fecha.weekday()  # 0=Lunes, 6=Domingo
            gastos_por_dia[dia_semana].append(float(gasto.monto))
        
        # Encontrar el día con más gastos
        if gastos_por_dia:
            promedios_por_dia = {dia: statistics.mean(montos) for dia, montos in gastos_por_dia.items() if montos}
            
            if promedios_por_dia:
                dia_mayor_gasto = max(promedios_por_dia, key=promedios_por_dia.get)
                promedio_mayor = promedios_por_dia[dia_mayor_gasto]
                promedio_general = statistics.mean([m for montos in gastos_por_dia.values() for m in montos])
                
                dias_nombres = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                
                if promedio_mayor > promedio_general * 1.3:  # 30% más que el promedio
                    titulo = f"Patrón de Gasto: {dias_nombres[dia_mayor_gasto]}"
                    mensaje = (
                        f"Detectamos que gastas significativamente más los {dias_nombres[dia_mayor_gasto]} "
                        f"(S/. {promedio_mayor:.2f} vs S/. {promedio_general:.2f} promedio). "
                        f"Planificar tus gastos este día podría generar ahorros importantes."
                    )
                    
                    recomendacion = self._crear_recomendacion(
                        tipo='PATRON_TEMPORAL',
                        titulo=titulo,
                        mensaje=mensaje,
                        valor_actual=Decimal(str(promedio_mayor)).quantize(Decimal('0.01')),
                        valor_objetivo=Decimal(str(promedio_general)).quantize(Decimal('0.01')),
                        prioridad='MEDIA'
                    )
                    
                    if recomendacion:
                        recomendaciones.append(recomendacion)
        
        return recomendaciones
    
    def _generar_metas_ahorro(self):
        """Genera recomendaciones de metas de ahorro"""
        recomendaciones = []
        
        total_mensual = self._obtener_total_gastos_usuario()
        
        if total_mensual > Decimal('100'):  # Solo si hay gastos significativos
            # Meta conservadora: 10% de ahorro
            meta_ahorro = total_mensual * Decimal('0.10')
            
            titulo = "Meta de Ahorro Inteligente"
            mensaje = (
                f"Basado en tus gastos actuales de S/. {total_mensual:.2f} mensuales, "
                f"puedes establecer una meta de ahorro de S/. {meta_ahorro:.2f} (10%). "
                f"Esto se puede lograr optimizando pequeños gastos diarios."
            )
            
            recomendacion = self._crear_recomendacion(
                tipo='META_AHORRO',
                titulo=titulo,
                mensaje=mensaje,
                valor_actual=total_mensual,
                valor_objetivo=total_mensual - meta_ahorro,
                ahorro_potencial=meta_ahorro,
                porcentaje_impacto=Decimal('10.00'),
                prioridad='MEDIA'
            )
            
            if recomendacion:
                recomendaciones.append(recomendacion)
        
        return recomendaciones
    
    def _analizar_comparativas(self):
        """Analiza comparativas con otros usuarios"""
        recomendaciones = []
        
        # Obtener categorías donde el usuario está en el top 20% de gastos
        patrones = PatronUsuario.objects.filter(usuario=self.usuario)
        
        for patron in patrones:
            try:
                stats = EstadisticaComparativa.objects.get(categoria=patron.categoria)
                
                if patron.gasto_promedio_mensual > stats.percentil_90:
                    titulo = f"Alto Gasto en {patron.categoria.get_nombre_display()}"
                    mensaje = (
                        f"Tu gasto en {patron.categoria.get_nombre_display()} "
                        f"(S/. {patron.gasto_promedio_mensual:.2f}) está en el 10% más alto. "
                        f"El 75% de usuarios gasta menos de S/. {stats.percentil_75:.2f} en esta categoría."
                    )
                    
                    recomendacion = self._crear_recomendacion(
                        tipo='COMPARATIVA',
                        categoria=patron.categoria,
                        titulo=titulo,
                        mensaje=mensaje,
                        valor_actual=patron.gasto_promedio_mensual,
                        valor_objetivo=stats.percentil_75,
                        prioridad='ALTA'
                    )
                    
                    if recomendacion:
                        recomendaciones.append(recomendacion)
                        
            except EstadisticaComparativa.DoesNotExist:
                continue
        
        return recomendaciones
    
    def _analizar_presupuestos(self):
        """Analiza presupuestos y genera alertas"""
        recomendaciones = []
        
        presupuestos_vigentes = Presupuesto.objects.filter(
            id_usuario=self.usuario,
            activo=True,
            fecha_inicio__lte=self.hoy,
            fecha_fin__gte=self.hoy
        )
        
        for presupuesto in presupuestos_vigentes:
            porcentaje_usado = presupuesto.get_porcentaje_usado()
            
            if porcentaje_usado > 80:  # Cerca del límite o excedido
                if porcentaje_usado > 100:
                    titulo = f"Presupuesto Excedido: {presupuesto.categoria.get_nombre_display()}"
                    mensaje = (
                        f"Has excedido tu presupuesto de {presupuesto.categoria.get_nombre_display()} "
                        f"en un {porcentaje_usado - 100:.1f}%. "
                        f"Gastado: S/. {presupuesto.get_gasto_total_actual():.2f} "
                        f"de S/. {presupuesto.monto_maximo:.2f} presupuestados."
                    )
                    prioridad = 'CRITICA'
                else:
                    titulo = f"Cerca del Límite: {presupuesto.categoria.get_nombre_display()}"
                    mensaje = (
                        f"Has usado {porcentaje_usado:.1f}% de tu presupuesto en "
                        f"{presupuesto.categoria.get_nombre_display()}. "
                        f"Te quedan S/. {presupuesto.get_monto_restante():.2f} para el resto del período."
                    )
                    prioridad = 'ALTA'
                
                recomendacion = self._crear_recomendacion(
                    tipo='ALERTA_LIMITE',
                    categoria=presupuesto.categoria,
                    titulo=titulo,
                    mensaje=mensaje,
                    valor_actual=presupuesto.get_gasto_total_actual(),
                    valor_objetivo=presupuesto.monto_maximo,
                    porcentaje_impacto=Decimal(str(porcentaje_usado)).quantize(Decimal('0.01')),
                    prioridad=prioridad
                )
                
                if recomendacion:
                    recomendaciones.append(recomendacion)
        
        return recomendaciones
    
    def _crear_recomendacion(self, tipo, titulo, mensaje, categoria=None, valor_actual=None, 
                           valor_objetivo=None, ahorro_potencial=None, porcentaje_impacto=None, 
                           prioridad='MEDIA'):
        """Crea una nueva recomendación si no existe una similar reciente"""
        
        # Verificar si ya existe una recomendación similar en los últimos 7 días
        fecha_limite = timezone.now() - timedelta(days=7)
        recomendacion_existente = RecomendacionGenerada.objects.filter(
            usuario=self.usuario,
            tipo_recomendacion__nombre=tipo,
            categoria_relacionada=categoria,
            fecha_generacion__gte=fecha_limite,
            activa=True
        ).first()
        
        if recomendacion_existente:
            return None  # Ya existe una recomendación similar reciente
        
        try:
            tipo_rec = TipoRecomendacion.objects.get(nombre=tipo)
        except TipoRecomendacion.DoesNotExist:
            # Crear el tipo si no existe
            tipo_rec = TipoRecomendacion.objects.create(nombre=tipo)
        
        # Calcular fecha de expiración (30 días)
        fecha_expiracion = timezone.now() + timedelta(days=30)
        
        recomendacion = RecomendacionGenerada.objects.create(
            usuario=self.usuario,
            tipo_recomendacion=tipo_rec,
            categoria_relacionada=categoria,
            titulo=titulo,
            mensaje=mensaje,
            valor_actual=valor_actual,
            valor_objetivo=valor_objetivo,
            ahorro_potencial=ahorro_potencial,
            porcentaje_impacto=porcentaje_impacto,
            prioridad=prioridad,
            fecha_expiracion=fecha_expiracion,
            periodo_analisis_dias=30,
            confianza_algoritmo=Decimal('85.00')
        )
        
        return recomendacion
    
    def _actualizar_estadisticas_comparativas(self):
        """Actualiza las estadísticas comparativas del sistema"""
        categorias = TipoGasto.objects.all()
        
        for categoria in categorias:
            # Obtener todos los gastos de esta categoría en los últimos 3 meses
            gastos = Gasto.objects.filter(
                tipo_gasto=categoria,
                fecha__gte=self.hace_90_dias
            )
            
            if gastos.count() < 5:  # Necesitamos datos suficientes
                continue
            
            # Calcular gastos mensuales por usuario
            gastos_mensuales_por_usuario = defaultdict(Decimal)
            usuarios_con_gastos = set()
            
            for gasto in gastos:
                usuario_id = gasto.id_usuario.id
                usuarios_con_gastos.add(usuario_id)
                gastos_mensuales_por_usuario[usuario_id] += gasto.monto
            
            if len(usuarios_con_gastos) < 3:  # Necesitamos al menos 3 usuarios
                continue
            
            # Normalizar a promedio mensual (dividir por 3 meses)
            promedios_mensuales = [float(total / 3) for total in gastos_mensuales_por_usuario.values()]
            promedios_mensuales.sort()
            
            # Calcular estadísticas
            promedio = statistics.mean(promedios_mensuales)
            mediana = statistics.median(promedios_mensuales)
            
            # Calcular percentiles
            def percentil(data, p):
                k = (len(data) - 1) * p / 100
                f = int(k)
                c = k - f
                if f == len(data) - 1:
                    return data[f]
                return data[f] * (1 - c) + data[f + 1] * c
            
            p25 = percentil(promedios_mensuales, 25)
            p75 = percentil(promedios_mensuales, 75)
            p90 = percentil(promedios_mensuales, 90)
            
            # Actualizar o crear estadística comparativa
            stats, created = EstadisticaComparativa.objects.get_or_create(
                categoria=categoria,
                periodo_meses=3,
                defaults={
                    'promedio_sistema': Decimal('0'),
                    'mediana_sistema': Decimal('0'),
                    'percentil_25': Decimal('0'),
                    'percentil_75': Decimal('0'),
                    'percentil_90': Decimal('0'),
                    'usuarios_en_muestra': 0,
                }
            )
            
            stats.promedio_sistema = Decimal(str(promedio)).quantize(Decimal('0.01'))
            stats.mediana_sistema = Decimal(str(mediana)).quantize(Decimal('0.01'))
            stats.percentil_25 = Decimal(str(p25)).quantize(Decimal('0.01'))
            stats.percentil_75 = Decimal(str(p75)).quantize(Decimal('0.01'))
            stats.percentil_90 = Decimal(str(p90)).quantize(Decimal('0.01'))
            stats.usuarios_en_muestra = len(usuarios_con_gastos)
            stats.fecha_calculo = timezone.now()
            stats.save()


class GeneradorRecomendaciones:
    """
    Clase de alto nivel para generar recomendaciones para usuarios
    """
    
    @staticmethod
    def generar_para_usuario(usuario):
        """
        Genera recomendaciones para un usuario específico
        """
        analizador = AnalizadorPatrones(usuario)
        return analizador.generar_todas_recomendaciones()
    
    @staticmethod
    def generar_para_todos_usuarios():
        """
        Genera recomendaciones para todos los usuarios activos
        """
        from authentication.models import Usuario
        
        usuarios_activos = Usuario.objects.filter(is_active=True)
        total_recomendaciones = 0
        
        for usuario in usuarios_activos:
            try:
                recomendaciones = GeneradorRecomendaciones.generar_para_usuario(usuario)
                total_recomendaciones += len(recomendaciones)
                print(f"✅ {len(recomendaciones)} recomendaciones para {usuario.username}")
            except Exception as e:
                print(f"❌ Error generando recomendaciones para {usuario.username}: {e}")
        
        print(f"🎉 Total: {total_recomendaciones} recomendaciones generadas")
        return total_recomendaciones
    
    @staticmethod
    def obtener_recomendaciones_usuario(usuario, solo_activas=True, limite=None):
        """
        Obtiene las recomendaciones de un usuario
        """
        queryset = RecomendacionGenerada.objects.filter(usuario=usuario)
        
        if solo_activas:
            queryset = queryset.filter(activa=True)
        
        queryset = queryset.order_by('-prioridad', '-fecha_generacion')
        
        if limite:
            queryset = queryset[:limite]
        
        return queryset
    
    @staticmethod
    def marcar_recomendacion_vista(recomendacion_id, usuario):
        """
        Marca una recomendación como vista
        """
        try:
            recomendacion = RecomendacionGenerada.objects.get(
                id_recomendacion=recomendacion_id,
                usuario=usuario
            )
            recomendacion.marcar_como_vista()
            return True
        except RecomendacionGenerada.DoesNotExist:
            return False
    
    @staticmethod
    def marcar_recomendacion_aplicada(recomendacion_id, usuario):
        """
        Marca una recomendación como aplicada
        """
        try:
            recomendacion = RecomendacionGenerada.objects.get(
                id_recomendacion=recomendacion_id,
                usuario=usuario
            )
            recomendacion.marcar_como_aplicada()
            return True
        except RecomendacionGenerada.DoesNotExist:
            return False


# Funciones de utilidad para comandos de management
def inicializar_tipos_recomendacion():
    """
    Inicializa los tipos de recomendación básicos
    """
    tipos_basicos = [
        ('REDUCIR_GASTO', 'Reducir Gasto en Categoría Específica'),
        ('OPTIMIZAR_CATEGORIA', 'Optimizar Gastos por Categoría'),
        ('PATRON_TEMPORAL', 'Optimización basada en Patrones Temporales'),
        ('META_AHORRO', 'Establecer Meta de Ahorro'),
        ('ALERTA_LIMITE', 'Alerta de Límite de Presupuesto'),
        ('HABITO_FINANCIERO', 'Mejorar Hábito Financiero'),
        ('COMPARATIVA', 'Comparativa con Promedio de Usuarios'),
    ]
    
    for nombre, descripcion in tipos_basicos:
        TipoRecomendacion.objects.get_or_create(
            nombre=nombre,
            defaults={'descripcion': descripcion}
        )
    
    print("✅ Tipos de recomendación inicializados")


def ejecutar_analisis_completo():
    """
    Ejecuta un análisis completo del sistema y genera recomendaciones
    """
    print("🚀 Iniciando análisis completo del sistema...")
    
    # Inicializar tipos si no existen
    inicializar_tipos_recomendacion()
    
    # Generar recomendaciones para todos los usuarios
    total = GeneradorRecomendaciones.generar_para_todos_usuarios()
    
    print(f"🎉 Análisis completo finalizado. {total} recomendaciones generadas.")
    return total