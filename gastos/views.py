# gastos/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
from .models import Gasto, TipoGasto
from .forms import GastoForm, FiltroGastosForm

@login_required
def gastos_view(request):
    """Vista principal del módulo de gastos según mockup"""
    # Inicializar formularios
    gasto_form = GastoForm()
    filtro_form = FiltroGastosForm()
    
    # Obtener gastos del usuario actual
    gastos = Gasto.objects.filter(id_usuario=request.user)
    
    # Aplicar filtros si existen
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    categoria = request.GET.get('categoria')
    
    if fecha_inicio:
        gastos = gastos.filter(fecha__gte=fecha_inicio)
    if fecha_fin:
        gastos = gastos.filter(fecha__lte=fecha_fin)
    if categoria:
        gastos = gastos.filter(tipo_gasto__nombre=categoria)
    
    # Procesar formulario de nuevo gasto (CORREGIDO para el template HTML)
    if request.method == 'POST' and 'registrar_gasto' in request.POST:
        try:
            # Obtener datos del formulario HTML personalizado
            fecha = request.POST.get('fecha')
            tipo_gasto_id = request.POST.get('tipo_gasto')  # Del select oculto
            monto = request.POST.get('monto')
            descripcion = request.POST.get('descripcion')
            
            # Validar datos
            if not all([fecha, tipo_gasto_id, monto, descripcion]):
                messages.error(request, 'Todos los campos son obligatorios.')
                return redirect('gastos:gastos')
            
            # Convertir fecha string a objeto date
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
            
            # Obtener el tipo de gasto
            tipo_gasto = TipoGasto.objects.get(id=tipo_gasto_id)
            
            # Crear el gasto
            gasto = Gasto.objects.create(
                id_usuario=request.user,
                tipo_gasto=tipo_gasto,
                monto=float(monto),
                descripcion=descripcion,
                fecha=fecha_obj
            )
            
            messages.success(request, '✅ Gasto registrado exitosamente!')
            return redirect('gastos:gastos')
            
        except ValueError as e:
            messages.error(request, f'Error en los datos: {str(e)}')
        except TipoGasto.DoesNotExist:
            messages.error(request, 'Categoría no válida.')
        except Exception as e:
            messages.error(request, f'Error al registrar el gasto: {str(e)}')
    
    context = {
        'gasto_form': gasto_form,
        'filtro_form': filtro_form,
        'gastos': gastos,
        'total_gastos': sum(float(g.monto) for g in gastos),
        'count_gastos': gastos.count(),
        'tipos_gasto': TipoGasto.objects.all(),
        'fecha_actual': timezone.now().date(),
    }
    
    return render(request, 'gastos/gastos.html', context)

@login_required
def editar_gasto(request, gasto_id):
    """Editar gasto existente"""
    gasto = get_object_or_404(Gasto, id_gasto=gasto_id, id_usuario=request.user)
    
    if request.method == 'POST':
        form = GastoForm(request.POST, instance=gasto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Gasto actualizado exitosamente!')
            return redirect('gastos:gastos')
    else:
        form = GastoForm(instance=gasto)
    
    context = {
        'form': form,
        'gasto': gasto,
        'editando': True,
    }
    
    return render(request, 'gastos/editar_gasto.html', context)

@login_required
def eliminar_gasto(request, gasto_id):
    """Eliminar gasto"""
    gasto = get_object_or_404(Gasto, id_gasto=gasto_id, id_usuario=request.user)
    
    if request.method == 'POST':
        gasto.delete()
        messages.success(request, 'Gasto eliminado exitosamente!')
        return redirect('gastos:gastos')
    
    context = {
        'gasto': gasto,
    }
    
    return render(request, 'gastos/confirmar_eliminar.html', context)