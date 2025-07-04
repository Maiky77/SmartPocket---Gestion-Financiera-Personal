# presupuestos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from datetime import datetime
from .models import Presupuesto, AlertaPresupuesto
from .forms import PresupuestoForm, FiltroPresupuestosForm
from gastos.models import TipoGasto

@login_required
def presupuestos_view(request):
    """
    Vista principal del módulo de presupuestos
    """
    # Procesar formulario de creación de presupuesto (CORREGIDO para template HTML)
    if request.method == 'POST' and 'crear_presupuesto' in request.POST:
        try:
            # Obtener datos del formulario HTML personalizado
            categoria_id = request.POST.get('categoria')
            monto_maximo = request.POST.get('monto_maximo')
            fecha_inicio = request.POST.get('fecha_inicio')
            fecha_fin = request.POST.get('fecha_fin')
            
            # Validar datos básicos
            if not all([categoria_id, monto_maximo, fecha_inicio, fecha_fin]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return redirect('presupuestos:presupuestos')
            
            # Convertir y validar tipos
            categoria = TipoGasto.objects.get(id=categoria_id)
            monto_maximo = float(monto_maximo)
            fecha_inicio_obj = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            
            # Validaciones
            if monto_maximo <= 0:
                messages.error(request, 'El monto máximo debe ser mayor a 0.')
                return redirect('presupuestos:presupuestos')
            
            if fecha_fin_obj <= fecha_inicio_obj:
                messages.error(request, 'La fecha de fin debe ser posterior a la fecha de inicio.')
                return redirect('presupuestos:presupuestos')
            
            # Verificar que no exista presupuesto activo para la misma categoría
            presupuestos_existentes = Presupuesto.objects.filter(
                id_usuario=request.user,
                categoria=categoria,
                activo=True,
                fecha_inicio__lte=fecha_fin_obj,
                fecha_fin__gte=fecha_inicio_obj
            )
            
            if presupuestos_existentes.exists():
                messages.error(request, f'Ya existe un presupuesto activo para {categoria.get_nombre_display()} en el período seleccionado.')
                return redirect('presupuestos:presupuestos')
            
            # Crear el presupuesto
            presupuesto = Presupuesto.objects.create(
                id_usuario=request.user,
                categoria=categoria,
                monto_maximo=monto_maximo,
                fecha_inicio=fecha_inicio_obj,
                fecha_fin=fecha_fin_obj
            )
            
            messages.success(request, f'✅ Presupuesto para {categoria.get_nombre_display()} creado exitosamente.')
            return redirect('presupuestos:presupuestos')
            
        except TipoGasto.DoesNotExist:
            messages.error(request, 'Categoría no válida.')
        except ValueError as e:
            messages.error(request, f'Error en los datos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al crear el presupuesto: {str(e)}')
            
        return redirect('presupuestos:presupuestos')
    
    # Crear formulario para el template (aunque usemos HTML personalizado)
    form = PresupuestoForm(usuario=request.user)
    
    # Procesar filtros
    filtro_form = FiltroPresupuestosForm(request.GET)
    presupuestos = Presupuesto.objects.filter(id_usuario=request.user)
    
    if filtro_form.is_valid():
        categoria = filtro_form.cleaned_data.get('categoria')
        estado = filtro_form.cleaned_data.get('estado')
        fecha_desde = filtro_form.cleaned_data.get('fecha_desde')
        fecha_hasta = filtro_form.cleaned_data.get('fecha_hasta')
        
        if categoria:
            presupuestos = presupuestos.filter(categoria=categoria)
        
        if fecha_desde:
            presupuestos = presupuestos.filter(fecha_fin__gte=fecha_desde)
        
        if fecha_hasta:
            presupuestos = presupuestos.filter(fecha_inicio__lte=fecha_hasta)
        
        # Filtrar por estado
        if estado == 'activo':
            presupuestos = presupuestos.filter(activo=True)
        elif estado == 'vigente':
            hoy = timezone.now().date()
            presupuestos = presupuestos.filter(
                fecha_inicio__lte=hoy,
                fecha_fin__gte=hoy,
                activo=True
            )
        elif estado == 'expirado':
            hoy = timezone.now().date()
            presupuestos = presupuestos.filter(fecha_fin__lt=hoy)
        elif estado == 'excedido':
            # Este filtro se aplicará en el template ya que requiere cálculos
            pass
        elif estado == 'cerca_limite':
            # Este filtro se aplicará en el template ya que requiere cálculos
            pass
    
    # Aplicar filtros que requieren cálculos
    if filtro_form.is_valid():
        estado = filtro_form.cleaned_data.get('estado')
        if estado in ['excedido', 'cerca_limite']:
            presupuestos_filtrados = []
            for presupuesto in presupuestos:
                if estado == 'excedido' and presupuesto.esta_excedido():
                    presupuestos_filtrados.append(presupuesto)
                elif estado == 'cerca_limite' and presupuesto.esta_cerca_del_limite():
                    presupuestos_filtrados.append(presupuesto)
            presupuestos = presupuestos_filtrados
    
    # Generar alertas automáticas para presupuestos vigentes
    generar_alertas_automaticas(request.user)
    
    # Obtener alertas no vistas
    alertas = AlertaPresupuesto.objects.filter(
        presupuesto__id_usuario=request.user,
        vista=False
    ).order_by('-fecha_creacion')[:5]
    
    # Obtener estadísticas generales
    hoy = timezone.now().date()
    presupuestos_vigentes = Presupuesto.objects.filter(
        id_usuario=request.user,
        fecha_inicio__lte=hoy,
        fecha_fin__gte=hoy,
        activo=True
    )
    
    total_presupuestado = sum(float(p.monto_maximo) for p in presupuestos_vigentes)
    total_gastado = sum(float(p.get_gasto_total_actual()) for p in presupuestos_vigentes)
    
    context = {
        'form': form,
        'filtro_form': filtro_form,
        'presupuestos': presupuestos,
        'alertas': alertas,
        'tipos_gasto': TipoGasto.objects.all(),
        'presupuestos_vigentes': presupuestos_vigentes,
        'total_presupuestado': total_presupuestado,
        'total_gastado': total_gastado,
        'count_presupuestos': len(presupuestos) if isinstance(presupuestos, list) else presupuestos.count(),
    }
    
    return render(request, 'presupuestos/presupuestos.html', context)

@login_required
def editar_presupuesto_view(request, id_presupuesto):
    """
    Vista para editar un presupuesto existente
    """
    presupuesto = get_object_or_404(Presupuesto, id_presupuesto=id_presupuesto, id_usuario=request.user)
    
    if request.method == 'POST':
        form = PresupuestoForm(request.POST, instance=presupuesto, usuario=request.user)
        if form.is_valid():
            presupuesto_actualizado = form.save()
            messages.success(request, f'Presupuesto para {presupuesto_actualizado.categoria.get_nombre_display()} actualizado exitosamente.')
            return redirect('presupuestos:presupuestos')
        else:
            messages.error(request, 'Error al actualizar el presupuesto. Verifica los datos.')
    else:
        form = PresupuestoForm(instance=presupuesto, usuario=request.user)
    
    context = {
        'form': form,
        'presupuesto': presupuesto,
        'editando': True,
    }
    
    return render(request, 'presupuestos/editar_presupuesto.html', context)

@login_required
def eliminar_presupuesto_view(request, id_presupuesto):
    """
    Vista para eliminar un presupuesto
    """
    presupuesto = get_object_or_404(Presupuesto, id_presupuesto=id_presupuesto, id_usuario=request.user)
    
    if request.method == 'POST':
        categoria_nombre = presupuesto.categoria.get_nombre_display()
        presupuesto.delete()
        messages.success(request, f'Presupuesto para {categoria_nombre} eliminado exitosamente.')
        return redirect('presupuestos:presupuestos')
    
    context = {
        'presupuesto': presupuesto,
    }
    
    return render(request, 'presupuestos/confirmar_eliminar.html', context)

@login_required
def toggle_presupuesto_view(request, id_presupuesto):
    """
    Vista para activar/desactivar un presupuesto
    """
    presupuesto = get_object_or_404(Presupuesto, id_presupuesto=id_presupuesto, id_usuario=request.user)
    
    if request.method == 'POST':
        presupuesto.activo = not presupuesto.activo
        presupuesto.save()
        
        estado = "activado" if presupuesto.activo else "desactivado"
        messages.success(request, f'Presupuesto para {presupuesto.categoria.get_nombre_display()} {estado} exitosamente.')
    
    return redirect('presupuestos:presupuestos')

@login_required
def marcar_alerta_vista(request, id_alerta):
    """
    Marca una alerta como vista
    """
    alerta = get_object_or_404(AlertaPresupuesto, id_alerta=id_alerta, presupuesto__id_usuario=request.user)
    alerta.vista = True
    alerta.save()
    return redirect('presupuestos:presupuestos')

def generar_alertas_automaticas(usuario):
    """
    Genera alertas automáticas para presupuestos del usuario
    """
    hoy = timezone.now().date()
    presupuestos_vigentes = Presupuesto.objects.filter(
        id_usuario=usuario,
        fecha_inicio__lte=hoy,
        fecha_fin__gte=hoy,
        activo=True
    )
    
    for presupuesto in presupuestos_vigentes:
        AlertaPresupuesto.crear_alerta_automatica(presupuesto)