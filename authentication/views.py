# authentication/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import timedelta
from decimal import Decimal
from PIL import Image
import os
from io import BytesIO
from .models import Usuario
from .forms import PerfilForm, CambioContrasenaForm

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Buscar usuario por email
        try:
            user = Usuario.objects.get(email=email)
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido {user.getNombre()}!')
                return redirect('authentication:dashboard')
            else:
                messages.error(request, 'Credenciales incorrectas.')
        except Usuario.DoesNotExist:
            messages.error(request, 'No existe una cuenta con ese email.')
    
    return render(request, 'authentication/login.html')

@login_required
def dashboard_view(request):
    """Vista del Dashboard - Página principal con resumen financiero DINÁMICO"""
    usuario = request.user
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    hace_30_dias = hoy - timedelta(days=30)
    hace_7_dias = hoy - timedelta(days=7)
    
    # === IMPORTAR MODELOS NECESARIOS ===
    try:
        from gastos.models import Gasto, TipoGasto
        from presupuestos.models import Presupuesto, AlertaPresupuesto
        from recomendaciones.models import RecomendacionGenerada
    except ImportError:
        # Si algunos módulos no están disponibles, usar valores por defecto
        context = {
            'usuario': usuario,
            'fecha_actual': hoy,
            'tiene_datos': False,
            'total_gastos_mes': 0,
            'count_gastos_mes': 0,
            'promedio_diario': 0,
            'total_presupuesto': 0,
            'presupuesto_restante': 0,
            'porcentaje_presupuesto_usado': 0,
            'categoria_principal': 'N/A',
            'ahorros_potenciales': 0,
            'actividad_reciente': [],
            'presupuestos_activos_count': 0,
            'recomendaciones_activas': 0,
            'mensaje_sin_datos': 'Para comenzar, registra tus primeros gastos y presupuestos.'
        }
        return render(request, 'authentication/dashboard.html', context)
    
    # === ANÁLISIS DE GASTOS ===
    # Gastos del mes actual
    gastos_mes = Gasto.objects.filter(
        id_usuario=usuario,
        fecha__gte=inicio_mes,
        fecha__lte=hoy
    )
    total_gastos_mes = gastos_mes.aggregate(total=Sum('monto'))['total'] or Decimal('0')
    count_gastos_mes = gastos_mes.count()
    
    # Gastos de los últimos 30 días
    gastos_30_dias = Gasto.objects.filter(
        id_usuario=usuario,
        fecha__gte=hace_30_dias
    )
    total_30_dias = gastos_30_dias.aggregate(total=Sum('monto'))['total'] or Decimal('0')
    count_gastos_30_dias = gastos_30_dias.count()
    
    # === ANÁLISIS DE PRESUPUESTOS ===
    # Presupuestos activos y vigentes
    presupuestos_activos = Presupuesto.objects.filter(
        id_usuario=usuario,
        activo=True,
        fecha_inicio__lte=hoy,
        fecha_fin__gte=hoy
    )
    
    total_presupuesto = presupuestos_activos.aggregate(total=Sum('monto_maximo'))['total'] or Decimal('0')
    presupuesto_restante = total_presupuesto - total_gastos_mes
    
    # Porcentaje de presupuesto usado
    porcentaje_presupuesto_usado = 0
    if total_presupuesto > 0:
        porcentaje_presupuesto_usado = (float(total_gastos_mes) / float(total_presupuesto)) * 100
    
    # === CATEGORÍA PRINCIPAL ===
    categoria_principal = "N/A"
    monto_categoria_principal = Decimal('0')
    
    if gastos_30_dias.exists():
        categoria_top = gastos_30_dias.values(
            'tipo_gasto__nombre'
        ).annotate(
            total=Sum('monto')
        ).order_by('-total').first()
        
        if categoria_top:
            categoria_principal = dict(TipoGasto.CATEGORIAS).get(
                categoria_top['tipo_gasto__nombre'], 
                'N/A'
            )
            monto_categoria_principal = categoria_top['total']
    
    # === COMPARACIÓN CON MES ANTERIOR ===
    inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)
    fin_mes_anterior = inicio_mes - timedelta(days=1)
    
    gastos_mes_anterior = Gasto.objects.filter(
        id_usuario=usuario,
        fecha__gte=inicio_mes_anterior,
        fecha__lte=fin_mes_anterior
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0')
    
    # Calcular cambio porcentual
    cambio_porcentual = 0
    if gastos_mes_anterior > 0:
        cambio_porcentual = ((total_gastos_mes - gastos_mes_anterior) / gastos_mes_anterior) * 100
    
    # === PROMEDIO DIARIO ===
    promedio_diario = Decimal('0')
    if count_gastos_30_dias > 0:
        promedio_diario = total_30_dias / count_gastos_30_dias
    
    # === AHORROS POTENCIALES ===
    # Estimación basada en optimización del 12% de gastos actuales
    ahorros_potenciales = total_30_dias * Decimal('0.12') if total_30_dias > 0 else Decimal('0')
    
    # === ACTIVIDAD RECIENTE ===
    # Últimos 6 gastos del usuario con detalles
    gastos_recientes = Gasto.objects.filter(
        id_usuario=usuario
    ).select_related('tipo_gasto').order_by('-fecha', '-fecha_registro')[:6]
    
    # Calcular tiempo relativo para cada gasto
    actividad_reciente = []
    for gasto in gastos_recientes:
        # Calcular tiempo relativo
        if gasto.fecha == hoy:
            if gasto.fecha_registro:
                # Si es de hoy y tiene timestamp, calcular diferencia en tiempo real
                diferencia = timezone.now() - gasto.fecha_registro
                if diferencia.seconds < 3600:  # Menos de 1 hora
                    minutos = diferencia.seconds // 60
                    if minutos == 0:
                        tiempo_relativo = "Hace unos segundos"
                    elif minutos == 1:
                        tiempo_relativo = "Hace 1 minuto"
                    else:
                        tiempo_relativo = f"Hace {minutos} minutos"
                elif diferencia.seconds < 86400:  # Menos de 24 horas
                    horas = diferencia.seconds // 3600
                    if horas == 1:
                        tiempo_relativo = "Hace 1 hora"
                    else:
                        tiempo_relativo = f"Hace {horas} horas"
                else:
                    tiempo_relativo = "Hoy"
            else:
                tiempo_relativo = "Hoy"
        else:
            # Si no es de hoy, calcular diferencia en días
            diferencia = hoy - gasto.fecha
            if diferencia.days == 1:
                tiempo_relativo = "Ayer"
            elif diferencia.days < 7:
                tiempo_relativo = f"Hace {diferencia.days} días"
            else:
                tiempo_relativo = gasto.fecha.strftime("%d/%m/%Y")
        
        # Agregar gasto con tiempo calculado
        gasto.tiempo_relativo = tiempo_relativo
        actividad_reciente.append(gasto)
    
    # === RECOMENDACIONES ACTIVAS ===
    recomendaciones_activas = RecomendacionGenerada.objects.filter(
        usuario=usuario,
        activa=True
    ).count()
    
    # === ALERTAS DE PRESUPUESTO ===
    alertas_presupuesto = AlertaPresupuesto.objects.filter(
        presupuesto__id_usuario=usuario,
        vista=False
    ).order_by('-fecha_creacion')[:3]
    
    # === CREAR ALERTAS AUTOMÁTICAS ===
    # Verificar presupuestos y crear alertas si es necesario
    for presupuesto in presupuestos_activos:
        if presupuesto.esta_excedido() or presupuesto.esta_cerca_del_limite():
            AlertaPresupuesto.crear_alerta_automatica(presupuesto)
    
    # === DATOS PARA GRÁFICOS ===
    # Top 4 categorías para el gráfico circular
    top_categorias = gastos_30_dias.values(
        'tipo_gasto__nombre'
    ).annotate(
        total=Sum('monto'),
        count=Count('id_gasto')
    ).order_by('-total')[:4]
    
    # Convertir para el template
    categorias_grafico = []
    for cat in top_categorias:
        nombre_categoria = dict(TipoGasto.CATEGORIAS).get(cat['tipo_gasto__nombre'], cat['tipo_gasto__nombre'])
        categorias_grafico.append({
            'nombre': nombre_categoria,
            'total': float(cat['total']),
            'count': cat['count']
        })
    
    # === FUNCIÓN PARA OBTENER EMOJI DE CATEGORÍA ===
    def get_emoji_categoria(nombre_categoria):
        emoji_map = {
            'COMIDA': '🍽️',
            'TRANSPORTE': '🚗',
            'ENTRETENIMIENTO': '🎮',
            'EDUCACION': '📚',
            'INTERNET': '💻',
            'VIAJES': '✈️',
            'ROPA': '👕',
            'OTROS': '📦',
        }
        return emoji_map.get(nombre_categoria, '💰')
    
    # === FUNCIÓN PARA TIEMPO RELATIVO ===
    def tiempo_relativo(fecha):
        diferencia = hoy - fecha
        if diferencia.days == 0:
            return "Hoy"
        elif diferencia.days == 1:
            return "Ayer"
        elif diferencia.days < 7:
            return f"Hace {diferencia.days} días"
        else:
            return fecha.strftime("%d/%m/%Y")
    
    # === CONTEXTO COMPLETO PARA EL TEMPLATE ===
    context = {
        # Datos básicos
        'usuario': usuario,
        'fecha_actual': hoy,
        'tiene_datos': count_gastos_30_dias > 0,
        
        # Métricas principales
        'total_gastos_mes': float(total_gastos_mes),
        'total_30_dias': float(total_30_dias),
        'count_gastos_mes': count_gastos_mes,
        'count_gastos_30_dias': count_gastos_30_dias,
        'promedio_diario': float(promedio_diario),
        
        # Presupuestos
        'total_presupuesto': float(total_presupuesto),
        'presupuesto_restante': float(presupuesto_restante),
        'porcentaje_presupuesto_usado': round(porcentaje_presupuesto_usado, 1),
        'presupuestos_activos_count': presupuestos_activos.count(),
        
        # Análisis
        'categoria_principal': categoria_principal,
        'monto_categoria_principal': float(monto_categoria_principal),
        'ahorros_potenciales': float(ahorros_potenciales),
        'cambio_porcentual': round(cambio_porcentual, 1),
        
        # Actividad y recomendaciones
        'actividad_reciente': actividad_reciente,
        'recomendaciones_activas': recomendaciones_activas,
        'alertas_presupuesto': alertas_presupuesto,
        
        # Datos para gráficos
        'categorias_grafico': categorias_grafico,
        
        # Funciones auxiliares
        'get_emoji_categoria': get_emoji_categoria,
        'tiempo_relativo': tiempo_relativo,
        
        # Estados del dashboard
        'tiene_presupuestos': presupuestos_activos.exists(),
        'tiene_alertas': alertas_presupuesto.exists(),
        'mensaje_sin_datos': 'Para comenzar, registra tus primeros gastos en la sección "💰 Gastos".' if count_gastos_30_dias == 0 else None,
    }
    
    return render(request, 'authentication/dashboard.html', context)

@login_required
def perfil_view(request):
    """
    Vista principal del perfil de usuario con funcionalidades completas
    """
    usuario = request.user
    
    # Inicializar formularios
    perfil_form = PerfilForm(instance=usuario)
    password_form = CambioContrasenaForm(user=usuario)
    
    if request.method == 'POST':
        # Determinar qué formulario se envió
        if 'actualizar_perfil' in request.POST:
            return manejar_actualizacion_perfil(request, usuario)
        elif 'cambiar_contrasena' in request.POST:
            return manejar_cambio_contrasena(request, usuario)
    
    # Obtener estadísticas del usuario para mostrar en el perfil
    estadisticas_usuario = obtener_estadisticas_usuario(usuario)
    
    context = {
        'perfil_form': perfil_form,
        'password_form': password_form,
        'usuario': usuario,
        'estadisticas': estadisticas_usuario,
    }
    
    return render(request, 'authentication/perfil.html', context)

def manejar_actualizacion_perfil(request, usuario):
    """Maneja la actualización de información del perfil"""
    perfil_form = PerfilForm(request.POST, request.FILES, instance=usuario)
    
    if perfil_form.is_valid():
        # Procesar foto de perfil si se subió una nueva
        if 'foto_perfil' in request.FILES:
            foto_antigua = usuario.foto_perfil
            
            # Procesar y redimensionar la nueva imagen
            nueva_foto = procesar_foto_perfil(request.FILES['foto_perfil'], usuario.username)
            
            if nueva_foto:
                # Eliminar foto anterior si existe
                if foto_antigua:
                    try:
                        default_storage.delete(foto_antigua.name)
                    except:
                        pass  # Si no se puede eliminar, continuar
                
                # Asignar nueva foto
                usuario.foto_perfil = nueva_foto
        
        # Guardar cambios
        perfil_form.save()
        messages.success(request, '✅ Perfil actualizado correctamente.')
        
        return redirect('authentication:perfil')
    else:
        # Si hay errores, mostrar mensaje
        messages.error(request, '❌ Error al actualizar el perfil. Revisa los campos.')
        
        # Re-crear el contexto con errores
        password_form = CambioContrasenaForm(user=usuario)
        estadisticas_usuario = obtener_estadisticas_usuario(usuario)
        
        context = {
            'perfil_form': perfil_form,
            'password_form': password_form,
            'usuario': usuario,
            'estadisticas': estadisticas_usuario,
        }
        
        return render(request, 'authentication/perfil.html', context)

def manejar_cambio_contrasena(request, usuario):
    """Maneja el cambio de contraseña"""
    password_form = CambioContrasenaForm(user=usuario, data=request.POST)
    
    if password_form.is_valid():
        # Guardar nueva contraseña
        password_form.save()
        
        # Mantener la sesión activa después del cambio
        update_session_auth_hash(request, usuario)
        
        messages.success(request, '🔐 Contraseña cambiada exitosamente.')
        return redirect('authentication:perfil')
    else:
        # Si hay errores, mostrar mensaje
        messages.error(request, '❌ Error al cambiar la contraseña. Verifica los datos.')
        
        # Re-crear el contexto con errores
        perfil_form = PerfilForm(instance=usuario)
        estadisticas_usuario = obtener_estadisticas_usuario(usuario)
        
        context = {
            'perfil_form': perfil_form,
            'password_form': password_form,
            'usuario': usuario,
            'estadisticas': estadisticas_usuario,
        }
        
        return render(request, 'authentication/perfil.html', context)

def procesar_foto_perfil(imagen, username):
    """
    Procesa y redimensiona la foto de perfil
    """
    try:
        # Abrir imagen con PIL
        img = Image.open(imagen)
        
        # Convertir a RGB si es necesario
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Redimensionar manteniendo proporción (máximo 400x400)
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        
        # Crear imagen cuadrada (crop centrado)
        width, height = img.size
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        
        img = img.crop((left, top, right, bottom))
        img = img.resize((300, 300), Image.Resampling.LANCZOS)
        
        # Guardar en memoria
        output = BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        # Crear nombre único para el archivo
        filename = f'perfiles/{username}_perfil.jpg'
        
        # Guardar en el storage
        return default_storage.save(filename, ContentFile(output.read()))
        
    except Exception as e:
        print(f"Error procesando imagen: {e}")
        return None

def obtener_estadisticas_usuario(usuario):
    """Obtiene estadísticas básicas del usuario para mostrar en el perfil"""
    from django.utils import timezone
    from datetime import timedelta
    
    try:
        from gastos.models import Gasto
        from presupuestos.models import Presupuesto
        from recomendaciones.models import RecomendacionGenerada
    except ImportError:
        # Si los módulos no están disponibles, retornar estadísticas básicas
        return {
            'total_gastos': 0,
            'gastos_mes_actual': 0,
            'presupuestos_activos': 0,
            'recomendaciones_pendientes': 0,
            'dias_en_sistema': (timezone.now().date() - usuario.fecha_registro.date()).days,
            'fecha_registro': usuario.fecha_registro,
        }
    
    hoy = timezone.now().date()
    hace_30_dias = hoy - timedelta(days=30)
    
    # Gastos
    total_gastos = Gasto.objects.filter(id_usuario=usuario).count()
    gastos_mes_actual = Gasto.objects.filter(
        id_usuario=usuario,
        fecha__gte=hace_30_dias
    ).count()
    
    # Presupuestos
    presupuestos_activos = Presupuesto.objects.filter(
        id_usuario=usuario,
        activo=True
    ).count()
    
    # Recomendaciones
    recomendaciones_pendientes = RecomendacionGenerada.objects.filter(
        usuario=usuario,
        activa=True,
        aplicada=False
    ).count()
    
    # Fecha de registro
    dias_en_sistema = (hoy - usuario.fecha_registro.date()).days
    
    return {
        'total_gastos': total_gastos,
        'gastos_mes_actual': gastos_mes_actual,
        'presupuestos_activos': presupuestos_activos,
        'recomendaciones_pendientes': recomendaciones_pendientes,
        'dias_en_sistema': dias_en_sistema,
        'fecha_registro': usuario.fecha_registro,
    }

@login_required
def eliminar_foto_perfil(request):
    """Elimina la foto de perfil del usuario"""
    if request.method == 'POST':
        usuario = request.user
        
        if usuario.foto_perfil:
            try:
                # Eliminar archivo físico
                default_storage.delete(usuario.foto_perfil.name)
                
                # Limpiar campo en la base de datos
                usuario.foto_perfil = None
                usuario.save()
                
                messages.success(request, '🗑️ Foto de perfil eliminada correctamente.')
            except Exception as e:
                messages.error(request, '❌ Error al eliminar la foto de perfil.')
        else:
            messages.info(request, 'ℹ️ No tienes foto de perfil para eliminar.')
    
    return redirect('authentication:perfil')

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        telefono = request.POST.get('telefono', '')
        
        # Verificar si el usuario ya existe
        if Usuario.objects.filter(username=username).exists():
            messages.error(request, 'Ya existe un usuario con ese nombre.')
            return render(request, 'authentication/register.html')
        
        if Usuario.objects.filter(email=email).exists():
            messages.error(request, 'Ya existe una cuenta con ese email.')
            return render(request, 'authentication/register.html')
        
        # Crear usuario
        user = Usuario.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            telefono=telefono
        )
        
        messages.success(request, 'Cuenta creada exitosamente. Puedes iniciar sesión.')
        return redirect('authentication:login')
    
    return render(request, 'authentication/register.html')

def logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada exitosamente.')
    return redirect('authentication:login')