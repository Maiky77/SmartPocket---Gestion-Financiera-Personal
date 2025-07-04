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
            crear_recomendaciones_ejemplo(request.user)
            messages.success(request, 'Se generaron nuevas recomendaciones personalizadas.')
        except Exception as e:
            messages.error(request, f'Error al generar recomendaciones: {str(e)}')
        
        return redirect('recomendaciones:recomendaciones')
    
    # Obtener recomendaciones activas del usuario (SIN filtros complejos)
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
                messages.success(request, 'Se generaron recomendaciones personalizadas basadas en tus gastos.')
        except Exception as e:
            messages.error(request, f'Error generando recomendaciones: {str(e)}')
    
    # Obtener estadísticas básicas
    estadisticas = obtener_estadisticas_basicas(request.user)
    
    # Contar recomendaciones por prioridad (SIN usar queryset sliced)
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
        'recomendaciones': recomendaciones[:10],  # Limitar a 10 en el template
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
            return JsonResponse({'success': False})
    return JsonResponse({'success': False})

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
            return JsonResponse({'success': True})
        except RecomendacionGenerada.DoesNotExist:
            return JsonResponse({'success': False})
    return JsonResponse({'success': False})

@login_required
def descartar_recomendacion(request, recomendacion_id):
    """Descarta una recomendación"""
    recomendacion = get_object_or_404(
        RecomendacionGenerada, 
        id_recomendacion=recomendacion_id, 
        usuario=request.user
    )
    
    if request.method == 'POST':
        recomendacion.activa = False
        recomendacion.save()
        messages.info(request, 'Recomendación descartada.')
    
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
            messages.success(request, 'Se regeneraron las recomendaciones.')
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
    """Crea recomendaciones de ejemplo basadas en los gastos reales del usuario"""
    # Verificar si ya existen recomendaciones recientes
    fecha_limite = timezone.now() - timedelta(hours=1)  # 1 hora
    if RecomendacionGenerada.objects.filter(
        usuario=usuario,
        fecha_generacion__gte=fecha_limite,
        activa=True
    ).exists():
        return  # Ya hay recomendaciones muy recientes
    
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
    
    # Obtener gastos del usuario
    gastos_usuario = Gasto.objects.filter(id_usuario=usuario)
    total_gastos = sum(float(gasto.monto) for gasto in gastos_usuario)
    count_gastos = gastos_usuario.count()
    
    if total_gastos > 0:
        # Recomendación 1: Meta de ahorro
        meta_ahorro = total_gastos * 0.15  # 15% de ahorro
        
        RecomendacionGenerada.objects.create(
            usuario=usuario,
            tipo_recomendacion=tipo_meta,
            titulo="Meta de Ahorro Personalizada",
            mensaje=f"Basado en tus gastos totales de S/. {total_gastos:.2f}, puedes establecer una meta de ahorro de S/. {meta_ahorro:.2f} (15%). Esto es alcanzable optimizando gastos pequeños diarios.",
            valor_actual=Decimal(str(total_gastos)),
            valor_objetivo=Decimal(str(total_gastos - meta_ahorro)),
            ahorro_potencial=Decimal(str(meta_ahorro)),
            porcentaje_impacto=Decimal('15.00'),
            prioridad='MEDIA'
        )
        
        # Recomendación 2: Análisis de frecuencia
        if count_gastos > 5:
            promedio_gasto = total_gastos / count_gastos
            
            RecomendacionGenerada.objects.create(
                usuario=usuario,
                tipo_recomendacion=tipo_analisis,
                titulo="Optimización de Gastos Frecuentes",
                mensaje=f"Has registrado {count_gastos} gastos con un promedio de S/. {promedio_gasto:.2f} por transacción. Revisar tus gastos más frecuentes puede revelar oportunidades de ahorro significativo.",
                valor_actual=Decimal(str(promedio_gasto)),
                prioridad='ALTA'
            )
        
        # Recomendación 3: Análisis por categorías
        gastos_por_categoria = {}
        for gasto in gastos_usuario:
            categoria = gasto.tipo_gasto.get_nombre_display()
            gastos_por_categoria[categoria] = gastos_por_categoria.get(categoria, 0) + float(gasto.monto)
        
        if gastos_por_categoria:
            categoria_mayor = max(gastos_por_categoria, key=gastos_por_categoria.get)
            monto_mayor = gastos_por_categoria[categoria_mayor]
            porcentaje_categoria = (monto_mayor / total_gastos) * 100
            
            if porcentaje_categoria > 30:  # Si una categoría es más del 30%
                RecomendacionGenerada.objects.create(
                    usuario=usuario,
                    tipo_recomendacion=tipo_patron,
                    titulo=f"Alto Gasto en {categoria_mayor}",
                    mensaje=f"Tu categoría '{categoria_mayor}' representa {porcentaje_categoria:.1f}% de tus gastos totales (S/. {monto_mayor:.2f}). Considera estrategias específicas para optimizar esta área.",
                    valor_actual=Decimal(str(monto_mayor)),
                    porcentaje_impacto=Decimal(str(porcentaje_categoria)),
                    prioridad='ALTA'
                )
    else:
        # Recomendación para usuarios sin gastos
        RecomendacionGenerada.objects.create(
            usuario=usuario,
            tipo_recomendacion=tipo_patron,
            titulo="Comienza a Registrar tus Gastos",
            mensaje="Para generar recomendaciones personalizadas precisas, comienza registrando tus gastos diarios. Incluso gastos pequeños pueden revelar patrones importantes para tu salud financiera.",
            prioridad='BAJA'
        )