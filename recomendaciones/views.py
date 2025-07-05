# recomendaciones/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import RecomendacionGenerada, TipoRecomendacion
from gastos.models import Gasto

@login_required
def recomendaciones_view(request):
    """
    Vista principal del módulo de recomendaciones con IA real
    """
    # Generar recomendaciones si el usuario hace clic en el botón
    if request.method == 'POST' and 'generar_recomendaciones' in request.POST:
        try:
            # CORREGIDO: Desactivar recomendaciones anteriores antes de crear nuevas
            RecomendacionGenerada.objects.filter(
                usuario=request.user,
                activa=True
            ).update(activa=False)
            
            # Crear nuevas recomendaciones
            crear_recomendaciones_ejemplo(request.user)
            messages.success(request, '🎉 Se generaron nuevas recomendaciones personalizadas basadas en tus últimos gastos.')
        except Exception as e:
            messages.error(request, f'Error al generar recomendaciones: {str(e)}')
        
        return redirect('recomendaciones:recomendaciones')
    
    # Obtener recomendaciones activas del usuario
    recomendaciones = RecomendacionGenerada.objects.filter(
        usuario=request.user,
        activa=True
    ).order_by('-fecha_generacion')
    
    # Si no hay recomendaciones, crear algunas automáticamente
    if not recomendaciones.exists():
        try:
            crear_recomendaciones_ejemplo(request.user)
            # Volver a obtener las recomendaciones
            recomendaciones = RecomendacionGenerada.objects.filter(
                usuario=request.user,
                activa=True
            ).order_by('-fecha_generacion')
            
            if recomendaciones.exists():
                messages.success(request, '✨ Se generaron recomendaciones personalizadas basadas en tus gastos.')
        except Exception as e:
            messages.error(request, f'Error generando recomendaciones: {str(e)}')
    
    # Obtener estadísticas básicas
    estadisticas = obtener_estadisticas_basicas(request.user)
    
    # Contar recomendaciones por prioridad
    total_recomendaciones = recomendaciones.count()
    criticas = 0
    altas = 0
    medias = 0
    bajas = 0
    
    for rec in recomendaciones:
        if rec.prioridad == 'CRITICA':
            criticas += 1
        elif rec.prioridad == 'ALTA':
            altas += 1
        elif rec.prioridad == 'MEDIA':
            medias += 1
        elif rec.prioridad == 'BAJA':
            bajas += 1
    
    recomendaciones_count = {
        'total': total_recomendaciones,
        'criticas': criticas,
        'altas': altas,
        'medias': medias,
        'bajas': bajas,
    }
    
    context = {
        'recomendaciones': recomendaciones[:10],
        'estadisticas': estadisticas,
        'recomendaciones_count': recomendaciones_count,
        'tiene_gastos_suficientes': Gasto.objects.filter(id_usuario=request.user).count() >= 1,
    }
    
    return render(request, 'recomendaciones/recomendaciones.html', context)

@login_required
def marcar_vista_ajax(request, recomendacion_id):
    """Marca una recomendación como vista vía AJAX"""
    if request.method == 'POST':
        try:
            recomendacion = RecomendacionGenerada.objects.get(
                id_recomendacion=recomendacion_id,
                usuario=request.user
            )
            recomendacion.vista = True
            recomendacion.save()
            return JsonResponse({'success': True})
        except RecomendacionGenerada.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Recomendación no encontrada'})
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def marcar_aplicada_ajax(request, recomendacion_id):
    """Marca una recomendación como aplicada vía AJAX"""
    if request.method == 'POST':
        try:
            recomendacion = RecomendacionGenerada.objects.get(
                id_recomendacion=recomendacion_id,
                usuario=request.user
            )
            recomendacion.aplicada = True
            recomendacion.vista = True
            recomendacion.save()
            return JsonResponse({
                'success': True, 
                'message': '✅ Recomendación marcada como aplicada'
            })
        except RecomendacionGenerada.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Recomendación no encontrada'})
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def descartar_recomendacion(request, recomendacion_id):
    """Descarta una recomendación - CORREGIDO: acepta GET"""
    recomendacion = get_object_or_404(
        RecomendacionGenerada, 
        id_recomendacion=recomendacion_id, 
        usuario=request.user
    )
    
    # CORREGIDO: Funciona con GET (el enlace del template)
    recomendacion.activa = False
    recomendacion.save()
    messages.info(request, '❌ Recomendación descartada correctamente.')
    
    return redirect('recomendaciones:recomendaciones')

@login_required
def detalle_recomendacion(request, recomendacion_id):
    """Vista detallada de una recomendación"""
    recomendacion = get_object_or_404(
        RecomendacionGenerada, 
        id_recomendacion=recomendacion_id, 
        usuario=request.user
    )
    
    if not recomendacion.vista:
        recomendacion.vista = True
        recomendacion.save()
    
    context = {'recomendacion': recomendacion}
    return render(request, 'recomendaciones/detalle_recomendacion.html', context)

@login_required
def regenerar_recomendaciones(request):
    """Regenera todas las recomendaciones"""
    if request.method == 'POST':
        try:
            # Desactivar recomendaciones actuales
            RecomendacionGenerada.objects.filter(
                usuario=request.user,
                activa=True
            ).update(activa=False)
            
            # Generar nuevas
            crear_recomendaciones_ejemplo(request.user)
            messages.success(request, '🔄 Se regeneraron todas las recomendaciones.')
        except Exception as e:
            messages.error(request, f'Error al regenerar: {str(e)}')
    
    return redirect('recomendaciones:recomendaciones')

@login_required
def analisis_patrones(request):
    """Vista de análisis de patrones"""
    context = {
        'estadisticas': obtener_estadisticas_basicas(request.user),
    }
    return render(request, 'recomendaciones/analisis_patrones.html', context)

def obtener_estadisticas_basicas(usuario):
    """Obtiene estadísticas básicas del usuario"""
    hoy = timezone.now().date()
    hace_30_dias = hoy - timedelta(days=30)
    
    gastos_30_dias = Gasto.objects.filter(
        id_usuario=usuario,
        fecha__gte=hace_30_dias
    )
    
    total_30_dias = sum(float(gasto.monto) for gasto in gastos_30_dias)
    
    # Categoría principal
    categoria_principal = "N/A"
    if gastos_30_dias.exists():
        gastos_por_categoria = {}
        for gasto in gastos_30_dias:
            categoria = gasto.tipo_gasto.get_nombre_display()
            gastos_por_categoria[categoria] = gastos_por_categoria.get(categoria, 0) + float(gasto.monto)
        
        if gastos_por_categoria:
            categoria_principal = max(gastos_por_categoria, key=gastos_por_categoria.get)
    
    recomendaciones_activas = RecomendacionGenerada.objects.filter(
        usuario=usuario,
        activa=True
    ).count()
    
    return {
        'total_30_dias': total_30_dias,
        'categoria_principal': categoria_principal,
        'transacciones_30_dias': gastos_30_dias.count(),
        'recomendaciones_activas': recomendaciones_activas,
        'tiene_datos_suficientes': gastos_30_dias.count() >= 1,
    }

def crear_recomendaciones_ejemplo(usuario):
    """Crea recomendaciones variadas basadas en los gastos reales del usuario"""
    
    # Crear tipos de recomendación si no existen
    tipo_meta, _ = TipoRecomendacion.objects.get_or_create(
        nombre='META_AHORRO',
        defaults={'descripcion': 'Meta de Ahorro Inteligente'}
    )
    
    tipo_analisis, _ = TipoRecomendacion.objects.get_or_create(
        nombre='ANALISIS_GASTOS',
        defaults={'descripcion': 'Análisis de Gastos'}
    )
    
    tipo_patron, _ = TipoRecomendacion.objects.get_or_create(
        nombre='PATRON_TEMPORAL',
        defaults={'descripcion': 'Patrón de Gastos'}
    )
    
    tipo_comparativa, _ = TipoRecomendacion.objects.get_or_create(
        nombre='COMPARATIVA',
        defaults={'descripcion': 'Comparativa con Promedio'}
    )
    
    tipo_habito, _ = TipoRecomendacion.objects.get_or_create(
        nombre='HABITO_FINANCIERO',
        defaults={'descripcion': 'Hábito Financiero'}
    )
    
    # Obtener gastos del usuario
    gastos_usuario = Gasto.objects.filter(id_usuario=usuario)
    total_gastos = sum(float(gasto.monto) for gasto in gastos_usuario)
    count_gastos = gastos_usuario.count()
    
    # Obtener gastos recientes (últimos 30 días)
    hace_30_dias = timezone.now().date() - timedelta(days=30)
    gastos_recientes = Gasto.objects.filter(
        id_usuario=usuario,
        fecha__gte=hace_30_dias
    )
    total_reciente = sum(float(gasto.monto) for gasto in gastos_recientes)
    
    if total_gastos > 0:
        # RECOMENDACIÓN 1: Meta de ahorro personalizada
        meta_ahorro = total_gastos * 0.15  # 15% de ahorro
        
        RecomendacionGenerada.objects.create(
            usuario=usuario,
            tipo_recomendacion=tipo_meta,
            titulo="🎯 Meta de Ahorro Personalizada",
            mensaje=f"Basado en tus gastos totales de S/. {total_gastos:.2f}, puedes establecer una meta de ahorro de S/. {meta_ahorro:.2f} (15%). Esto es alcanzable optimizando gastos pequeños diarios.",
            valor_actual=Decimal(str(total_gastos)),
            valor_objetivo=Decimal(str(total_gastos - meta_ahorro)),
            ahorro_potencial=Decimal(str(meta_ahorro)),
            porcentaje_impacto=Decimal('15.00'),
            prioridad='MEDIA'
        )
        
        # RECOMENDACIÓN 2: Análisis de frecuencia
        if count_gastos > 5:
            promedio_gasto = total_gastos / count_gastos
            
            RecomendacionGenerada.objects.create(
                usuario=usuario,
                tipo_recomendacion=tipo_analisis,
                titulo="💡 Optimización de Gastos Frecuentes",
                mensaje=f"Has registrado {count_gastos} gastos con un promedio de S/. {promedio_gasto:.2f} por transacción. Revisar tus gastos más frecuentes puede revelar oportunidades de ahorro significativo.",
                valor_actual=Decimal(str(promedio_gasto)),
                prioridad='ALTA'
            )
        
        # RECOMENDACIÓN 3: Análisis por categorías (principal)
        gastos_por_categoria = {}
        for gasto in gastos_usuario:
            categoria = gasto.tipo_gasto.get_nombre_display()
            gastos_por_categoria[categoria] = gastos_por_categoria.get(categoria, 0) + float(gasto.monto)
        
        if gastos_por_categoria:
            categoria_mayor = max(gastos_por_categoria, key=gastos_por_categoria.get)
            monto_mayor = gastos_por_categoria[categoria_mayor]
            porcentaje_categoria = (monto_mayor / total_gastos) * 100
            
            RecomendacionGenerada.objects.create(
                usuario=usuario,
                tipo_recomendacion=tipo_patron,
                titulo=f"⚠️ Alto Gasto en {categoria_mayor}",
                mensaje=f"Tu categoría '{categoria_mayor}' representa {porcentaje_categoria:.1f}% de tus gastos totales (S/. {monto_mayor:.2f}). Considera estrategias específicas para optimizar esta área.",
                valor_actual=Decimal(str(monto_mayor)),
                porcentaje_impacto=Decimal(str(porcentaje_categoria)),
                prioridad='ALTA' if porcentaje_categoria > 40 else 'MEDIA'
            )
        
        # RECOMENDACIÓN 4: Comparativa con promedio ideal
        gasto_promedio_ideal = 500  # Promedio ideal mensual para usuarios similares
        
        if total_reciente > gasto_promedio_ideal:
            diferencia = total_reciente - gasto_promedio_ideal
            RecomendacionGenerada.objects.create(
                usuario=usuario,
                tipo_recomendacion=tipo_comparativa,
                titulo="📊 Comparativa con Promedio Ideal",
                mensaje=f"Tus gastos mensuales (S/. {total_reciente:.2f}) superan el promedio ideal de S/. {gasto_promedio_ideal:.2f} en S/. {diferencia:.2f}. Identifica gastos no esenciales para optimizar.",
                valor_actual=Decimal(str(total_reciente)),
                valor_objetivo=Decimal(str(gasto_promedio_ideal)),
                ahorro_potencial=Decimal(str(diferencia)),
                prioridad='ALTA'
            )
        else:
            RecomendacionGenerada.objects.create(
                usuario=usuario,
                tipo_recomendacion=tipo_comparativa,
                titulo="✅ Gastos Controlados",
                mensaje=f"¡Felicidades! Tus gastos mensuales (S/. {total_reciente:.2f}) están por debajo del promedio ideal. Mantén estos buenos hábitos financieros.",
                valor_actual=Decimal(str(total_reciente)),
                valor_objetivo=Decimal(str(gasto_promedio_ideal)),
                prioridad='BAJA'
            )
        
        # RECOMENDACIÓN 5: Hábito de registro
        if count_gastos >= 10:
            RecomendacionGenerada.objects.create(
                usuario=usuario,
                tipo_recomendacion=tipo_habito,
                titulo="📝 Excelente Hábito de Registro",
                mensaje=f"Has registrado {count_gastos} gastos, demostrando un excelente hábito de seguimiento. Mantén esta disciplina para maximizar el control de tus finanzas.",
                valor_actual=Decimal(str(count_gastos)),
                prioridad='BAJA'
            )
        else:
            RecomendacionGenerada.objects.create(
                usuario=usuario,
                tipo_recomendacion=tipo_habito,
                titulo="📈 Mejora tu Hábito de Registro",
                mensaje=f"Has registrado {count_gastos} gastos. Intenta registrar al menos 15-20 gastos mensuales para obtener insights más precisos y recomendaciones personalizadas.",
                valor_actual=Decimal(str(count_gastos)),
                valor_objetivo=Decimal('20'),
                prioridad='MEDIA'
            )
        
        # RECOMENDACIÓN 6: Específica por categoría principal
        if gastos_por_categoria:
            if categoria_mayor == "Comida":
                ahorro_comida = monto_mayor * 0.25
                RecomendacionGenerada.objects.create(
                    usuario=usuario,
                    tipo_recomendacion=tipo_analisis,
                    titulo="🍽️ Optimiza tus Gastos en Comida",
                    mensaje=f"Gastas S/. {monto_mayor:.2f} en comida. Estrategias: cocinar en casa (3 días/semana), planificar menús, comprar al por mayor. Ahorro estimado: S/. {ahorro_comida:.2f}/mes.",
                    valor_actual=Decimal(str(monto_mayor)),
                    ahorro_potencial=Decimal(str(ahorro_comida)),
                    porcentaje_impacto=Decimal('25.00'),
                    prioridad='MEDIA'
                )
            elif categoria_mayor == "Transporte":
                ahorro_transporte = monto_mayor * 0.20
                RecomendacionGenerada.objects.create(
                    usuario=usuario,
                    tipo_recomendacion=tipo_analisis,
                    titulo="🚗 Optimiza tus Gastos en Transporte",
                    mensaje=f"Gastas S/. {monto_mayor:.2f} en transporte. Considera: transporte público, bicicleta, caminar distancias cortas, carpooling. Ahorro estimado: S/. {ahorro_transporte:.2f}/mes.",
                    valor_actual=Decimal(str(monto_mayor)),
                    ahorro_potencial=Decimal(str(ahorro_transporte)),
                    porcentaje_impacto=Decimal('20.00'),
                    prioridad='MEDIA'
                )
            elif categoria_mayor == "Entretenimiento":
                ahorro_entretenimiento = monto_mayor * 0.30
                RecomendacionGenerada.objects.create(
                    usuario=usuario,
                    tipo_recomendacion=tipo_analisis,
                    titulo="🎮 Optimiza tus Gastos en Entretenimiento",
                    mensaje=f"Gastas S/. {monto_mayor:.2f} en entretenimiento. Busca: actividades gratuitas, promociones 2x1, eventos comunitarios, streaming compartido. Ahorro estimado: S/. {ahorro_entretenimiento:.2f}/mes.",
                    valor_actual=Decimal(str(monto_mayor)),
                    ahorro_potencial=Decimal(str(ahorro_entretenimiento)),
                    porcentaje_impacto=Decimal('30.00'),
                    prioridad='BAJA'
                )
            elif categoria_mayor == "Educación":
                RecomendacionGenerada.objects.create(
                    usuario=usuario,
                    tipo_recomendacion=tipo_analisis,
                    titulo="📚 Inversión en Educación",
                    mensaje=f"Gastas S/. {monto_mayor:.2f} en educación. ¡Excelente inversión! Considera recursos gratuitos online, bibliotecas, cursos en línea masivos para complementar.",
                    valor_actual=Decimal(str(monto_mayor)),
                    prioridad='BAJA'
                )
            else:
                # Para otras categorías
                ahorro_generico = monto_mayor * 0.15
                RecomendacionGenerada.objects.create(
                    usuario=usuario,
                    tipo_recomendacion=tipo_analisis,
                    titulo=f"💰 Optimiza Gastos en {categoria_mayor}",
                    mensaje=f"Tu gasto principal es {categoria_mayor} (S/. {monto_mayor:.2f}). Revisa si todos estos gastos son necesarios y busca alternativas más económicas.",
                    valor_actual=Decimal(str(monto_mayor)),
                    ahorro_potencial=Decimal(str(ahorro_generico)),
                    porcentaje_impacto=Decimal('15.00'),
                    prioridad='MEDIA'
                )
        
        # RECOMENDACIÓN 7: Análisis temporal (si hay gastos recientes)
        if gastos_recientes.exists():
            if total_reciente > total_gastos * 0.5:  # Si el 50% de gastos son del último mes
                RecomendacionGenerada.objects.create(
                    usuario=usuario,
                    tipo_recomendacion=tipo_patron,
                    titulo="📈 Actividad Financiera Reciente",
                    mensaje=f"Has tenido alta actividad financiera reciente (S/. {total_reciente:.2f} en 30 días). Es buen momento para revisar y ajustar tu presupuesto mensual.",
                    valor_actual=Decimal(str(total_reciente)),
                    prioridad='MEDIA'
                )
    else:
        # Para usuarios sin gastos - crear recomendaciones motivacionales
        RecomendacionGenerada.objects.create(
            usuario=usuario,
            tipo_recomendacion=tipo_habito,
            titulo="🚀 Comienza tu Viaje Financiero",
            mensaje="¡Bienvenido a SmartPocket! Registra tus primeros gastos para comenzar a recibir recomendaciones personalizadas. Incluso gastos pequeños ayudan a entender tus patrones.",
            prioridad='ALTA'
        )
        
        RecomendacionGenerada.objects.create(
            usuario=usuario,
            tipo_recomendacion=tipo_meta,
            titulo="🎯 Establece tu Primera Meta",
            mensaje="Define un presupuesto mensual inicial (ej: S/. 500) y comienza a registrar tus gastos. El sistema aprenderá de tus hábitos para generar mejores recomendaciones.",
            valor_objetivo=Decimal('500.00'),
            prioridad='MEDIA'
        )
        
        RecomendacionGenerada.objects.create(
            usuario=usuario,
            tipo_recomendacion=tipo_patron,
            titulo="📊 Descubre tus Patrones",
            mensaje="Registra gastos de diferentes categorías durante una semana. Esto permitirá que la IA identifique tus patrones de consumo y genere insights valiosos.",
            prioridad='MEDIA'
        )
        
        RecomendacionGenerada.objects.create(
            usuario=usuario,
            tipo_recomendacion=tipo_analisis,
            titulo="💡 Consejos para Empezar",
            mensaje="Tips iniciales: 1) Registra TODO gasto (grande o pequeño), 2) Usa categorías correctas, 3) Sé consistente. En 1 semana tendrás tus primeras recomendaciones personalizadas.",
            prioridad='BAJA'
        )