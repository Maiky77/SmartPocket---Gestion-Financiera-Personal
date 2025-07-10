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
# ==================== IMPORTS PARA EMAIL HTML ====================
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from .utils import get_logo_base64, optimize_email_headers, get_professional_subject

# ==================== NUEVOS IMPORTS PARA RECUPERACIÓN ====================
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.http import JsonResponse
import json

from .models import Usuario, TokenRecuperacion
from .forms import (
    PerfilForm, CambioContrasenaForm, SolicitudRecuperacionForm, 
    VerificacionCodigoForm, NuevaContrasenaForm, RegistroUsuarioForm
)

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

# ==================== VISTAS DE RECUPERACIÓN DE CONTRASEÑA ====================

def recuperar_contrasena_solicitud(request):
    """Vista para solicitar recuperación de contraseña"""
    
    if request.method == 'POST':
        form = SolicitudRecuperacionForm(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data['email']
            
            try:
                usuario = Usuario.objects.get(email=email)
                
                # Crear token de recuperación
                ip_address = get_client_ip(request)
                token = TokenRecuperacion.crear_token(usuario, ip_address)
                
                # Enviar email con el código
                if enviar_email_recuperacion(usuario, token):
                    # Guardar email en sesión para los siguientes pasos
                    request.session['recovery_email'] = email
                    request.session['recovery_token_id'] = token.id
                    
                    messages.success(request, 
                        f'📧 Hemos enviado un código de verificación a {email}. '
                        f'Revisa tu bandeja de entrada y spam.'
                    )
                    return redirect('authentication:verificar_codigo')
                else:
                    messages.error(request, 
                        '❌ Error al enviar el email. Intenta de nuevo más tarde.'
                    )
            
            except Usuario.DoesNotExist:
                # Por seguridad, no revelar que el email no existe
                messages.success(request, 
                    f'📧 Si existe una cuenta con {email}, recibirás un código de verificación.'
                )
                return redirect('authentication:login')
    
    else:
        form = SolicitudRecuperacionForm()
    
    context = {
        'form': form,
        'titulo': 'Recuperar Contraseña',
        'subtitulo': 'Ingresa tu email para recibir un código de verificación'
    }
    
    return render(request, 'authentication/recuperacion/solicitud.html', context)

def verificar_codigo_recuperacion(request):
    """Vista para verificar el código de recuperación"""
    
    # Verificar que hay una solicitud de recuperación en curso
    recovery_email = request.session.get('recovery_email')
    recovery_token_id = request.session.get('recovery_token_id')
    
    if not recovery_email or not recovery_token_id:
        messages.error(request, '❌ Sesión de recuperación no válida. Inicia el proceso nuevamente.')
        return redirect('authentication:recuperar_contrasena')
    
    try:
        token = TokenRecuperacion.objects.get(id=recovery_token_id)
        es_valido, mensaje = token.es_valido()
        
        if not es_valido:
            messages.error(request, f'❌ {mensaje}')
            # Limpiar sesión
            request.session.pop('recovery_email', None)
            request.session.pop('recovery_token_id', None)
            return redirect('authentication:recuperar_contrasena')
    
    except TokenRecuperacion.DoesNotExist:
        messages.error(request, '❌ Token de recuperación no encontrado.')
        return redirect('authentication:recuperar_contrasena')
    
    if request.method == 'POST':
        form = VerificacionCodigoForm(request.POST)
        
        if form.is_valid():
            codigo_ingresado = form.cleaned_data['codigo']
            
            if codigo_ingresado == token.codigo:
                # Código correcto
                token.marcar_usado()
                
                # Guardar en sesión para el siguiente paso
                request.session['codigo_verificado'] = True
                
                messages.success(request, '✅ Código verificado correctamente.')
                return redirect('authentication:nueva_contrasena')
            
            else:
                # Código incorrecto
                token.incrementar_intento()
                intentos_restantes = max(0, 5 - token.intentos)
                
                if intentos_restantes > 0:
                    messages.error(request, 
                        f'❌ Código incorrecto. Te quedan {intentos_restantes} intentos.'
                    )
                else:
                    messages.error(request, 
                        '❌ Demasiados intentos fallidos. Solicita un nuevo código.'
                    )
                    # Limpiar sesión
                    request.session.pop('recovery_email', None)
                    request.session.pop('recovery_token_id', None)
                    return redirect('authentication:recuperar_contrasena')
    
    else:
        form = VerificacionCodigoForm()
    
    # Información del token para mostrar en el template
    info_token = token.get_info_seguridad()
    
    context = {
        'form': form,
        'titulo': 'Verificar Código',
        'subtitulo': f'Ingresa el código enviado a {recovery_email}',
        'email': recovery_email,
        'token_info': info_token,
    }
    
    return render(request, 'authentication/recuperacion/verificacion.html', context)

def nueva_contrasena_recuperacion(request):
    """Vista para establecer nueva contraseña"""
    
    # Verificar que el código fue verificado
    recovery_email = request.session.get('recovery_email')
    codigo_verificado = request.session.get('codigo_verificado')
    
    if not recovery_email or not codigo_verificado:
        messages.error(request, '❌ Debes verificar el código primero.')
        return redirect('authentication:recuperar_contrasena')
    
    try:
        usuario = Usuario.objects.get(email=recovery_email)
    except Usuario.DoesNotExist:
        messages.error(request, '❌ Usuario no encontrado.')
        return redirect('authentication:login')
    
    if request.method == 'POST':
        form = NuevaContrasenaForm(request.POST)
        
        if form.is_valid():
            nueva_contrasena = form.cleaned_data['nueva_contrasena']
            
            # Cambiar contraseña
            usuario.set_password(nueva_contrasena)
            usuario.save()
            
            # Limpiar sesión de recuperación
            request.session.pop('recovery_email', None)
            request.session.pop('recovery_token_id', None)
            request.session.pop('codigo_verificado', None)
            
            # Invalidar todos los tokens de recuperación del usuario
            TokenRecuperacion.objects.filter(usuario=usuario).update(usado=True)
            
            messages.success(request, 
                '🎉 ¡Contraseña cambiada exitosamente! Ya puedes iniciar sesión con tu nueva contraseña.'
            )
            return redirect('authentication:login')
    
    else:
        form = NuevaContrasenaForm()
    
    context = {
        'form': form,
        'titulo': 'Nueva Contraseña',
        'subtitulo': 'Establece tu nueva contraseña segura',
        'email': recovery_email,
        'usuario_nombre': usuario.getNombre()
    }
    
    return render(request, 'authentication/recuperacion/nueva_contrasena.html', context)

def reenviar_codigo_recuperacion(request):
    """Vista AJAX para reenviar código de recuperación"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    recovery_email = request.session.get('recovery_email')
    
    if not recovery_email:
        return JsonResponse({'success': False, 'error': 'Sesión no válida'})
    
    try:
        usuario = Usuario.objects.get(email=recovery_email)
        
        ip_address = get_client_ip(request)
        token = TokenRecuperacion.crear_token(usuario, ip_address)
        
        # Actualizar sesión con nuevo token
        request.session['recovery_token_id'] = token.id
        
        # Enviar email
        if enviar_email_recuperacion(usuario, token):
            return JsonResponse({
                'success': True, 
                'message': 'Nuevo código enviado correctamente'
            })
        else:
            return JsonResponse({
                'success': False, 
                'error': 'Error al enviar el email'
            })
    
    except Usuario.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Usuario no encontrado'})

# ==================== REGISTRO MEJORADO ====================

# NUEVA VISTA PARA REGISTRO MEJORADO
def register_view_mejorado(request):
    """Vista mejorada para registro de usuarios con validaciones"""
    
    if request.method == 'POST':
        # Procesar datos del formulario
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        acepto_terminos = request.POST.get('acepto_terminos', '')
        
        # Validaciones
        errores = []
        
        # Verificar campos requeridos
        if not all([first_name, last_name, username, email, password, confirm_password]):
            errores.append('Todos los campos son obligatorios')
        
        # Verificar contraseñas coinciden
        if password != confirm_password:
            errores.append('Las contraseñas no coinciden')
        
        # Verificar email único
        if Usuario.objects.filter(email=email).exists():
            errores.append('Ya existe una cuenta con este email')
        
        # Verificar username único
        if Usuario.objects.filter(username=username).exists():
            errores.append('Este nombre de usuario ya está en uso')
        
        # Verificar términos aceptados
        if not acepto_terminos:
            errores.append('Debes aceptar los términos y condiciones')
        
        if errores:
            # Mostrar errores
            for error in errores:
                messages.error(request, error)
            return render(request, 'authentication/register.html')
        
        try:
            # Crear usuario
            usuario = Usuario.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                telefono=telefono
            )
            
            # Login automático
            login(request, usuario)
            
            messages.success(request, f'¡Bienvenido a SmartPocket, {usuario.getNombre()}!')
            return redirect('authentication:dashboard')
            
        except Exception as e:
            messages.error(request, 'Error al crear la cuenta. Inténtalo de nuevo.')
            print(f"Error creating user: {e}")
    
    return render(request, 'authentication/register.html')

# ==================== REGISTRO BÁSICO (MANTENER COMPATIBILIDAD) ====================

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

# ==================== FUNCIONES AUXILIARES ====================

def get_client_ip(request):
    """Obtiene la IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def enviar_email_recuperacion_optimizado(usuario, token):
    """
    Envía email de recuperación OPTIMIZADO para evitar SPAM
    Returns: bool - True si se envió correctamente
    """
    try:
        print(f"\n🔄 INICIANDO envío de email de recuperación OPTIMIZADO para: {usuario.email}")
        
        # Obtener logo en base64
        logo_base64 = get_logo_base64()
        
        # Datos del contexto para el template
        context = {
            'usuario': usuario,
            'token': token,
            'now': timezone.now(),
            'logo_base64': logo_base64,
        }
        
        print(f"📝 Contexto preparado con logo: {'✅' if logo_base64 else '❌'}")
        
        # Renderizar templates
        html_content = render_to_string('authentication/emails/recuperacion_codigo.html', context)
        
        # Crear versión de texto plano profesional
        text_content = f"""SmartPocket - Verificación de seguridad

Estimado {usuario.getNombre()},

Código de verificación: {token.codigo}

Este código es válido por 15 minutos y puede utilizarse una sola vez.
Máximo 5 intentos de verificación permitidos.

Si no solicitó este restablecimiento, ignore este mensaje.

Detalles de seguridad:
- IP: {token.ip_solicitud or 'No disponible'}
- Fecha: {token.creado_en.strftime('%d/%m/%Y %H:%M')}
- Usuario: {usuario.email}

---
SmartPocket - Sistema de gestión financiera
Mensaje automático del sistema de seguridad
"""
        
        # Configurar email con asunto optimizado
        asunto_optimizado = get_professional_subject('recuperacion', usuario.getNombre()) + token.codigo
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [usuario.email]
        
        print(f"📧 Configurando email OPTIMIZADO:")
        print(f"   Asunto: {asunto_optimizado}")
        print(f"   De: {from_email}")
        print(f"   Para: {to_email}")
        
        # Crear email con headers optimizados
        email = EmailMultiAlternatives(
            subject=asunto_optimizado,
            body=text_content,
            from_email=from_email,
            to=to_email,
            headers=optimize_email_headers()  # ← HEADERS ANTI-SPAM
        )
        
        # Adjuntar contenido HTML
        email.attach_alternative(html_content, "text/html")
        print(f"📎 HTML optimizado adjuntado al email")
        
        # Enviar email
        print(f"🚀 Enviando email optimizado...")
        resultado = email.send()
        
        print(f"📊 Resultado del envío: {resultado}")
        print(f"✅ Email de recuperación OPTIMIZADO enviado exitosamente" if resultado > 0 else "❌ Error en el envío")
        
        return resultado > 0
        
    except Exception as e:
        print(f"❌ Error enviando email de recuperación optimizado: {e}")
        print(f"🔍 Tipo de error: {type(e).__name__}")
        
        return False

def enviar_email_bienvenida_optimizado(usuario):
    """
    Envía email de bienvenida OPTIMIZADO para evitar SPAM
    Returns: bool - True si se envió correctamente
    """
    try:
        print(f"\n🔄 INICIANDO envío de email de bienvenida OPTIMIZADO para: {usuario.email}")
        
        # Obtener logo en base64
        logo_base64 = get_logo_base64()
        
        # Datos del contexto para el template
        context = {
            'usuario': usuario,
            'now': timezone.now(),
            'logo_base64': logo_base64,
        }
        
        print(f"📝 Contexto preparado con logo: {'✅' if logo_base64 else '❌'}")
        
        # Renderizar template HTML optimizado
        html_content = render_to_string('authentication/emails/bienvenida.html', context)
        
        # Crear versión de texto plano profesional
        text_content = f"""SmartPocket - Cuenta creada correctamente

Estimado {usuario.getNombre()},

Su cuenta en SmartPocket ha sido creada exitosamente el {usuario.fecha_registro.strftime('%d/%m/%Y')}.

Funcionalidades disponibles:
- Control de gastos por categorías
- Análisis estadístico avanzado  
- Presupuestos inteligentes
- Recomendaciones personalizadas

Acceda a su cuenta en: http://smart-pocket.loc:8001

Detalles de la cuenta:
- Usuario: {usuario.email}
- Fecha de registro: {usuario.fecha_registro.strftime('%d/%m/%Y %H:%M')}

---
SmartPocket - Sistema de gestión financiera personal
Confirmación automática de registro
"""
        
        # Configurar email con asunto optimizado
        asunto_optimizado = get_professional_subject('bienvenida', usuario.getNombre())
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [usuario.email]
        
        print(f"📧 Configurando email de bienvenida OPTIMIZADO:")
        print(f"   Asunto: {asunto_optimizado}")
        print(f"   De: {from_email}")
        print(f"   Para: {to_email}")
        
        # Crear email con headers optimizados
        email = EmailMultiAlternatives(
            subject=asunto_optimizado,
            body=text_content,
            from_email=from_email,
            to=to_email,
            headers=optimize_email_headers()  # ← HEADERS ANTI-SPAM
        )
        
        # Adjuntar contenido HTML
        email.attach_alternative(html_content, "text/html")
        print(f"📎 HTML optimizado adjuntado al email")
        
        # Enviar email
        print(f"🚀 Enviando email de bienvenida optimizado...")
        resultado = email.send()
        
        print(f"📊 Resultado del envío: {resultado}")
        print(f"✅ Email de bienvenida OPTIMIZADO enviado exitosamente" if resultado > 0 else "❌ Error en el envío")
        
        return resultado > 0
        
    except Exception as e:
        print(f"❌ Error enviando email de bienvenida optimizado: {e}")
        print(f"🔍 Tipo de error: {type(e).__name__}")
        
        return False

# ==================== MODIFICAR FUNCIÓN DE REGISTRO PARA ENVÍO AUTOMÁTICO ====================

def register_view_con_email_automatico(request):
    """Vista de registro con envío automático de email de bienvenida"""
    
    if request.method == 'POST':
        # Procesar datos del formulario
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        acepto_terminos = request.POST.get('acepto_terminos', '')
        
        # Validaciones básicas
        errores = []
        
        if not all([first_name, last_name, username, email, password, confirm_password]):
            errores.append('Todos los campos son obligatorios')
        
        if password != confirm_password:
            errores.append('Las contraseñas no coinciden')
        
        if Usuario.objects.filter(email=email).exists():
            errores.append('Ya existe una cuenta con este email')
        
        if Usuario.objects.filter(username=username).exists():
            errores.append('Este nombre de usuario ya está en uso')
        
        if not acepto_terminos:
            errores.append('Debes aceptar los términos y condiciones')
        
        if errores:
            for error in errores:
                messages.error(request, error)
            return render(request, 'authentication/register.html')
        
        try:
            # Crear usuario
            usuario = Usuario.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                telefono=telefono
            )
            
            print(f"✅ Usuario creado exitosamente: {usuario.email}")
            
            # 🚀 ENVÍO AUTOMÁTICO DE EMAIL DE BIENVENIDA OPTIMIZADO
            try:
                print(f"📧 Intentando enviar email de bienvenida...")
                email_enviado = enviar_email_bienvenida_optimizado(usuario)
                
                if email_enviado:
                    print(f"✅ Email de bienvenida enviado correctamente")
                    messages.success(request, 
                        f'🎉 ¡Bienvenido a SmartPocket, {usuario.getNombre()}! '
                        f'Hemos enviado un email de confirmación a {usuario.email}.'
                    )
                else:
                    print(f"⚠️ Email de bienvenida no se pudo enviar, pero usuario creado")
                    messages.success(request, 
                        f'🎉 ¡Bienvenido a SmartPocket, {usuario.getNombre()}! '
                        f'Tu cuenta ha sido creada exitosamente.'
                    )
                    
            except Exception as email_error:
                print(f"❌ Error en envío de email de bienvenida: {email_error}")
                # No fallar el registro por problemas de email
                messages.success(request, 
                    f'🎉 ¡Bienvenido a SmartPocket, {usuario.getNombre()}! '
                    f'Tu cuenta ha sido creada exitosamente.'
                )
            
            # Login automático
            login(request, usuario)
            
            return redirect('authentication:dashboard')
            
        except Exception as e:
            print(f"❌ Error creando usuario: {e}")
            messages.error(request, 'Error al crear la cuenta. Inténtalo de nuevo.')
    
    return render(request, 'authentication/register.html')

# ==================== ACTUALIZAR FUNCIÓN DE RECUPERACIÓN ====================
# REEMPLAZAR la función enviar_email_recuperacion existente

def enviar_email_recuperacion(usuario, token):
    """
    FUNCIÓN ACTUALIZADA: Usa la versión optimizada
    """
    return enviar_email_recuperacion_optimizado(usuario, token)

def enviar_email_bienvenida(usuario):
    """
    FUNCIÓN ACTUALIZADA: Usa la versión optimizada  
    """
    return enviar_email_bienvenida_optimizado(usuario)

def enviar_email_bienvenida(usuario):
    """
    Envía email de bienvenida al nuevo usuario con template HTML
    Returns: bool - True si se envió correctamente
    """
    try:
        print(f"\n🔄 INICIANDO envío de email de bienvenida para: {usuario.email}")
        
        # Datos del contexto para el template
        context = {
            'usuario': usuario,
            'now': timezone.now(),
        }
        
        print(f"📝 Contexto preparado para {usuario.getNombre()}")
        
        # Renderizar templates HTML y texto
        try:
            html_content = render_to_string('authentication/emails/bienvenida.html', context)
            print(f"✅ Template HTML renderizado correctamente")
        except Exception as template_error:
            print(f"❌ Error en template HTML: {template_error}")
            # Usar template simple como fallback
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px;">
                    <h1>🎉 ¡Bienvenido a SmartPocket, {usuario.getNombre()}!</h1>
                    <p>Tu gestión financiera inteligente</p>
                </div>
                <div style="padding: 30px;">
                    <h2>¡Tu cuenta ha sido creada exitosamente!</h2>
                    <p>Ahora puedes:</p>
                    <ul>
                        <li>💰 Registrar tus gastos diarios</li>
                        <li>📊 Ver estadísticas de tus finanzas</li>
                        <li>🎯 Establecer presupuestos inteligentes</li>
                        <li>💡 Recibir recomendaciones personalizadas</li>
                    </ul>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://smart-pocket.loc:8001" style="background: #667eea; color: white; padding: 15px 30px; text-decoration: none; border-radius: 25px; display: inline-block;">
                            Ir a SmartPocket 🚀
                        </a>
                    </div>
                </div>
                <div style="background: #f8f9fa; padding: 20px; text-align: center; border-radius: 10px; margin-top: 20px;">
                    <p style="color: #6c757d;">SmartPocket - Tu asistente financiero inteligente</p>
                    <p style="color: #6c757d; font-size: 12px;">© {timezone.now().year} SmartPocket. Todos los derechos reservados.</p>
                </div>
            </body>
            </html>
            """
            print(f"🔄 Usando template HTML simple como fallback")
        
        # Crear versión de texto plano
        text_content = f"""
Confirmación de cuenta - SmartPocket

Hola {usuario.getNombre()},

Tu cuenta en SmartPocket ha sido verificada exitosamente.

Detalles de la cuenta:
- Email: {usuario.email}
- Fecha: {usuario.fecha_registro.strftime("%d/%m/%Y %H:%M")}
- Usuario: {usuario.getNombre()}

Puedes acceder en: http://smart-pocket.loc:8001

Funciones disponibles:
- Registrar gastos
- Ver estadísticas  
- Crear presupuestos
- Recibir recomendaciones

---
SmartPocket - Sistema de gestión financiera
Este email confirma la creación de tu cuenta.
        """
        
        # Configurar email
        asunto = f'🎉 ¡Bienvenido a SmartPocket, {usuario.getNombre()}!'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [usuario.email]
        
        print(f"📧 Configurando email:")
        print(f"   Asunto: {asunto}")
        print(f"   De: {from_email}")
        print(f"   Para: {to_email}")
        
        # Crear email con contenido HTML y texto usando EmailMultiAlternatives
        from django.core.mail import EmailMultiAlternatives
        
        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,  # Contenido de texto plano
            from_email=from_email,
            to=to_email
        )
        
        # Adjuntar contenido HTML
        email.attach_alternative(html_content, "text/html")
        print(f"📎 HTML adjuntado al email")
        
        # Enviar email
        print(f"🚀 Enviando email...")
        resultado = email.send()
        
        print(f"📊 Resultado del envío: {resultado}")
        print(f"✅ Email de bienvenida enviado exitosamente" if resultado > 0 else "❌ Error en el envío")
        
        return resultado > 0
        
    except Exception as e:
        print(f"❌ Error enviando email de bienvenida: {e}")
        print(f"🔍 Tipo de error: {type(e).__name__}")
        
        # Fallback a consola
        print(f"\n{'='*50}")
        print(f"📧 FALLBACK - EMAIL DE BIENVENIDA EN CONSOLA")
        print(f"{'='*50}")
        print(f"Para: {usuario.email}")
        print(f"Usuario: {usuario.getNombre()}")
        print(f"Asunto: 🎉 ¡Bienvenido a SmartPocket!")
        print(f"{'='*50}\n")
        
        return False

    
# AGREGAR ESTAS VISTAS AL FINAL DE authentication/views.py

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import make_password
import re

# ==================== VALIDACIONES AJAX PARA REGISTRO MEJORADO ====================

@csrf_exempt
@require_http_methods(["POST"])
def validar_campo_ajax(request):
    """Vista AJAX para validar campos individuales en tiempo real"""
    
    try:
        data = json.loads(request.body)
        campo = data.get('campo')
        valor = data.get('valor', '').strip()
        
        # Validaciones específicas por campo
        if campo == 'username':
            return validar_username_ajax(valor)
        elif campo == 'email':
            return validar_email_ajax(valor)
        elif campo == 'password':
            return validar_password_ajax(valor)
        elif campo == 'confirm_password':
            return validar_confirm_password_ajax(valor, data.get('password', ''))
        elif campo in ['first_name', 'last_name']:
            return validar_nombre_ajax(valor, campo)
        elif campo == 'telefono':
            return validar_telefono_ajax(valor)
        else:
            return JsonResponse({
                'valid': False,
                'message': 'Campo no reconocido'
            })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'valid': False,
            'message': 'Datos inválidos'
        })
    except Exception as e:
        return JsonResponse({
            'valid': False,
            'message': f'Error del servidor: {str(e)}'
        })

def validar_username_ajax(username):
    """Validar nombre de usuario"""
    
    if not username:
        return JsonResponse({
            'valid': False,
            'message': 'El nombre de usuario es obligatorio'
        })
    
    if len(username) < 3:
        return JsonResponse({
            'valid': False,
            'message': 'Mínimo 3 caracteres'
        })
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return JsonResponse({
            'valid': False,
            'message': 'Solo letras, números y guiones bajos'
        })
    
    # Verificar si ya existe
    if Usuario.objects.filter(username=username).exists():
        return JsonResponse({
            'valid': False,
            'message': 'Este nombre de usuario ya está en uso'
        })
    
    return JsonResponse({
        'valid': True,
        'message': 'Nombre de usuario disponible'
    })

def validar_email_ajax(email):
    """Validar email único"""
    
    if not email:
        return JsonResponse({
            'valid': False,
            'message': 'El email es obligatorio'
        })
    
    # Validar formato
    email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_pattern, email):
        return JsonResponse({
            'valid': False,
            'message': 'Formato de email inválido'
        })
    
    # Verificar si ya existe
    if Usuario.objects.filter(email=email).exists():
        return JsonResponse({
            'valid': False,
            'message': 'Ya existe una cuenta con este email'
        })
    
    return JsonResponse({
        'valid': True,
        'message': 'Email disponible'
    })

def validar_password_ajax(password):
    """Validar política de contraseñas"""
    
    if not password:
        return JsonResponse({
            'valid': False,
            'message': 'La contraseña es obligatoria'
        })
    
    errors = []
    
    if len(password) < 8:
        errors.append('Mínimo 8 caracteres')
    
    if password.isdigit():
        errors.append('No puede ser solo números')
    
    if password.isalpha():
        errors.append('Debe incluir al menos un número')
    
    if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        errors.append('Debe contener letras y números')
    
    # Contraseñas comunes
    common_passwords = [
        'password', 'contraseña', '12345678', 'qwerty', 
        'abc123', '123456789', 'password123'
    ]
    if password.lower() in common_passwords:
        errors.append('Esta contraseña es muy común')
    
    if errors:
        return JsonResponse({
            'valid': False,
            'message': errors[0]  # Mostrar el primer error
        })
    
    # Calcular fortaleza
    strength_score = 0
    if len(password) >= 8:
        strength_score += 1
    if re.search(r'[A-Z]', password):
        strength_score += 1
    if re.search(r'[a-z]', password):
        strength_score += 1
    if re.search(r'\d', password):
        strength_score += 1
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        strength_score += 1
    
    strength_levels = ['muy débil', 'débil', 'regular', 'buena', 'fuerte']
    strength = strength_levels[min(strength_score - 1, 4)] if strength_score > 0 else 'muy débil'
    
    return JsonResponse({
        'valid': True,
        'message': f'Contraseña {strength}',
        'strength': strength_score
    })

def validar_confirm_password_ajax(confirm_password, password):
    """Validar confirmación de contraseña"""
    
    if not confirm_password:
        return JsonResponse({
            'valid': False,
            'message': 'Confirma tu contraseña'
        })
    
    if confirm_password != password:
        return JsonResponse({
            'valid': False,
            'message': 'Las contraseñas no coinciden'
        })
    
    return JsonResponse({
        'valid': True,
        'message': 'Las contraseñas coinciden'
    })

def validar_nombre_ajax(nombre, campo):
    """Validar nombres (first_name, last_name)"""
    
    if not nombre:
        return JsonResponse({
            'valid': False,
            'message': 'Este campo es obligatorio'
        })
    
    if len(nombre) < 2:
        return JsonResponse({
            'valid': False,
            'message': 'Mínimo 2 caracteres'
        })
    
    if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
        return JsonResponse({
            'valid': False,
            'message': 'Solo letras y espacios'
        })
    
    campo_nombre = 'Nombre' if campo == 'first_name' else 'Apellido'
    return JsonResponse({
        'valid': True,
        'message': f'{campo_nombre} válido'
    })

def validar_telefono_ajax(telefono):
    """Validar formato de teléfono (opcional)"""
    
    # Si está vacío, es válido porque es opcional
    if not telefono:
        return JsonResponse({
            'valid': True,
            'message': 'Campo opcional'
        })
    
    # Limpiar el teléfono de espacios y caracteres especiales
    telefono_limpio = ''.join(filter(str.isdigit, telefono))
    
    if len(telefono_limpio) < 9:
        return JsonResponse({
            'valid': False,
            'message': 'Mínimo 9 dígitos'
        })
    
    if len(telefono_limpio) > 15:
        return JsonResponse({
            'valid': False,
            'message': 'Máximo 15 dígitos'
        })
    
    # Validar formato peruano (opcional)
    if not re.match(r'^(\+?51)?[9]\d{8}$', telefono.replace(' ', '')):
        return JsonResponse({
            'valid': True,  # Seguir siendo válido aunque no sea formato peruano
            'message': 'Formato recomendado: +51 999 999 999'
        })
    
    return JsonResponse({
        'valid': True,
        'message': 'Teléfono válido'
    })

# ==================== VISTA MEJORADA DE REGISTRO CON AJAX ====================

def register_view_mejorado_ajax(request):
    """Vista mejorada de registro que maneja tanto GET como POST/AJAX"""
    
    if request.method == 'POST':
        # Determinar si es una request AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        form = RegistroUsuarioForm(request.POST)
        
        if form.is_valid():
            try:
                # Crear usuario
                usuario = form.save(commit=False)
                usuario.set_password(form.cleaned_data['password'])
                usuario.save()
                
                # Enviar email de bienvenida (si está configurado)
                try:
                    enviar_email_bienvenida(usuario)
                except:
                    pass  # No fallar si el email no se puede enviar
                
                # Login automático
                login(request, usuario)
                
                # Respuesta para AJAX
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'¡Bienvenido a SmartPocket, {usuario.getNombre()}!',
                        'redirect_url': '/dashboard/'
                    })
                
                # Respuesta para formulario normal
                messages.success(request, 
                    f'🎉 ¡Bienvenido a SmartPocket, {usuario.getNombre()}! '
                    f'Tu cuenta ha sido creada exitosamente.'
                )
                return redirect('authentication:dashboard')
                
            except Exception as e:
                error_msg = 'Error al crear la cuenta. Inténtalo de nuevo.'
                
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': error_msg,
                        'errors': {'general': [str(e)]}
                    })
                
                messages.error(request, error_msg)
        
        else:
            # Errores de validación
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'message': 'Por favor, corrige los errores en el formulario.',
                    'errors': form.errors
                })
            
            # Para formulario normal, mostrar errores en el template
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    else:
        form = RegistroUsuarioForm()
    
    context = {
        'form': form,
        'titulo': 'Crear Cuenta',
        'subtitulo': 'Únete a SmartPocket y toma control de tus finanzas'
    }
    
    return render(request, 'authentication/register.html', context)

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

@csrf_exempt
@require_http_methods(["POST"])
def validar_campo_ajax(request):
    """Vista AJAX para validar campos en tiempo real"""
    
    try:
        data = json.loads(request.body)
        campo = data.get('campo')
        valor = data.get('valor', '').strip()
        
        # Validaciones específicas por campo
        if campo == 'username':
            return validar_username_ajax(valor)
        elif campo == 'email':
            return validar_email_ajax(valor)
        elif campo in ['first_name', 'last_name']:
            return validar_nombre_ajax(valor, campo)
        elif campo == 'telefono':
            return validar_telefono_ajax(valor)
        else:
            return JsonResponse({'valid': True, 'message': ''})
    
    except Exception as e:
        return JsonResponse({'valid': True, 'message': ''})

def validar_username_ajax(username):
    """Validar nombre de usuario único"""
    
    if not username:
        return JsonResponse({
            'valid': False,
            'message': 'El nombre de usuario es obligatorio'
        })
    
    if len(username) < 3:
        return JsonResponse({
            'valid': False,
            'message': 'Mínimo 3 caracteres'
        })
    
    # Verificar si ya existe
    if Usuario.objects.filter(username=username).exists():
        return JsonResponse({
            'valid': False,
            'message': 'Este nombre de usuario ya está en uso'
        })
    
    return JsonResponse({
        'valid': True,
        'message': 'Nombre de usuario disponible'
    })

def validar_email_ajax(email):
    """Validar email único"""
    
    if not email:
        return JsonResponse({
            'valid': False,
            'message': 'El email es obligatorio'
        })
    
    # Verificar si ya existe
    if Usuario.objects.filter(email=email).exists():
        return JsonResponse({
            'valid': False,
            'message': 'Ya existe una cuenta con este email'
        })
    
    return JsonResponse({
        'valid': True,
        'message': 'Email disponible'
    })

def validar_nombre_ajax(nombre, campo):
    """Validar nombres"""
    
    if not nombre:
        return JsonResponse({
            'valid': False,
            'message': 'Este campo es obligatorio'
        })
    
    if len(nombre) < 2:
        return JsonResponse({
            'valid': False,
            'message': 'Mínimo 2 caracteres'
        })
    
    return JsonResponse({
        'valid': True,
        'message': 'Válido'
    })

def validar_telefono_ajax(telefono):
    """Validar teléfono (opcional)"""
    
    if not telefono:
        return JsonResponse({
            'valid': True,
            'message': 'Campo opcional'
        })
    
    if len(telefono) < 9:
        return JsonResponse({
            'valid': False,
            'message': 'Mínimo 9 dígitos'
        })
    
    return JsonResponse({
        'valid': True,
        'message': 'Teléfono válido'
    })


# ==================== VISTA DE PRUEBA PARA EMAILS ====================
@login_required
def test_email_view(request):
    """Vista temporal para probar el envío de emails"""
    
    if request.method == 'POST':
        tipo_email = request.POST.get('tipo_email')
        usuario = request.user
        
        if tipo_email == 'recuperacion':
            # Crear token temporal para prueba
            token = TokenRecuperacion.crear_token(usuario, get_client_ip(request))
            
            # Enviar email de recuperación
            if enviar_email_recuperacion(usuario, token):
                messages.success(request, f'✅ Email de recuperación enviado correctamente a {usuario.email}')
            else:
                messages.error(request, '❌ Error al enviar email de recuperación')
        
        elif tipo_email == 'bienvenida':
            # Enviar email de bienvenida
            if enviar_email_bienvenida(usuario):
                messages.success(request, f'✅ Email de bienvenida enviado correctamente a {usuario.email}')
            else:
                messages.error(request, '❌ Error al enviar email de bienvenida')
    
    # Información de configuración para mostrar
    config_info = {
        'email_backend': settings.EMAIL_BACKEND,
        'email_host': getattr(settings, 'EMAIL_HOST', 'No configurado'),
        'email_port': getattr(settings, 'EMAIL_PORT', 'No configurado'),
        'email_use_tls': getattr(settings, 'EMAIL_USE_TLS', False),
        'email_host_user': getattr(settings, 'EMAIL_HOST_USER', 'No configurado'),
        'default_from_email': settings.DEFAULT_FROM_EMAIL,
    }
    
    context = {
        'config_info': config_info,
        'usuario': request.user,
    }
    
    return render(request, 'authentication/test_email.html', context)


# ==================== FUNCIÓN OPTIMIZADA ANTI-SPAM ====================
# AGREGAR al final de authentication/views.py

def enviar_email_recuperacion_final(usuario, token):
    """
    Envía email de recuperación con MÁXIMA optimización anti-SPAM
    manteniendo tu diseño original
    """
    try:
        print(f"\n🔄 ENVIANDO email de recuperación OPTIMIZADO FINAL para: {usuario.email}")
        
        # Importar utilidades
        from .utils import get_logo_base64
        
        # Obtener logo en base64
        logo_base64 = get_logo_base64()
        
        # Datos del contexto para el template
        context = {
            'usuario': usuario,
            'token': token,
            'now': timezone.now(),
            'logo_base64': logo_base64,
        }
        
        # Renderizar template optimizado
        html_content = render_to_string('authentication/emails/recuperacion_codigo.html', context)
        
        # Crear versión de texto plano PROFESIONAL
        text_content = f"""SMARTPOCKET - Verificación de cuenta

Estimado {usuario.getNombre()},

Código de verificación: {token.codigo}

Instrucciones:
- Válido por 15 minutos únicamente
- Máximo 5 intentos de verificación
- No comparta este código con nadie
- Si no solicitó esto, ignore este mensaje

Detalles de seguridad:
IP: {token.ip_solicitud or 'No disponible'}
Fecha: {token.creado_en.strftime('%d/%m/%Y %H:%M')}
Usuario: {usuario.email}

SmartPocket - Sistema de gestión financiera
Mensaje automático de seguridad - No responder

© {timezone.now().year} SmartPocket. Todos los derechos reservados.
"""
        
        # ASUNTO SUPER OPTIMIZADO para evitar SPAM
        asunto_optimizado = f'Verificación de cuenta SmartPocket - Código {token.codigo}'
        
        # HEADERS ANTI-SPAM PROFESIONALES
        headers_anti_spam = {
            'X-Priority': '1',  # Alta prioridad (transaccional)
            'X-MSMail-Priority': 'High',
            'X-Mailer': 'SmartPocket Security System v1.0',
            'X-MimeOLE': 'SmartPocket Financial Platform',
            'Importance': 'High',
            'X-Auto-Response-Suppress': 'OOF, DR, RN, NRN, AutoReply',
            'List-Unsubscribe': '<mailto:security@smartpocket.com>',
            'X-Entity-ID': f'sp-security-{token.id}',
            'X-Sender-ID': 'smartpocket-auth-system',
            'X-Message-Flag': 'SECURITY_VERIFICATION',
            'X-Classification': 'TRANSACTIONAL',
        }
        
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [usuario.email]
        
        print(f"📧 Configurando email FINAL OPTIMIZADO:")
        print(f"   Asunto: {asunto_optimizado}")
        print(f"   Headers anti-SPAM: {len(headers_anti_spam)} aplicados")
        print(f"   Logo: {'✅ Incluido' if logo_base64 else '❌ Fallback emoji'}")
        
        # Crear email con MÁXIMA optimización
        email = EmailMultiAlternatives(
            subject=asunto_optimizado,
            body=text_content,
            from_email=from_email,
            to=to_email,
            headers=headers_anti_spam  # ← HEADERS PROFESIONALES ANTI-SPAM
        )
        
        # Adjuntar contenido HTML optimizado
        email.attach_alternative(html_content, "text/html")
        
        # Enviar email
        print(f"🚀 Enviando email con optimización MÁXIMA...")
        resultado = email.send()
        
        print(f"📊 Resultado: {'✅ EXITOSO' if resultado > 0 else '❌ ERROR'}")
        
        # Log adicional para debugging
        if settings.DEBUG:
            print(f"\n{'='*60}")
            print(f"📧 EMAIL OPTIMIZADO ENVIADO")
            print(f"{'='*60}")
            print(f"Para: {usuario.email}")
            print(f"Usuario: {usuario.getNombre()}")
            print(f"Código: {token.codigo}")
            print(f"Headers: {len(headers_anti_spam)} aplicados")
            print(f"Logo: {'✅ Base64' if logo_base64 else '❌ Emoji fallback'}")
            print(f"Resultado: {'✅ Exitoso' if resultado else '❌ Error'}")
            print(f"{'='*60}\n")
        
        return resultado > 0
        
    except Exception as e:
        print(f"❌ Error enviando email optimizado: {e}")
        print(f"🔍 Tipo de error: {type(e).__name__}")
        return False

# ==================== REEMPLAZAR FUNCIÓN EXISTENTE ====================
# MODIFICAR la función enviar_email_recuperacion existente:

def enviar_email_recuperacion(usuario, token):
    """
    FUNCIÓN PRINCIPAL con LOGO incluido
    """
    try:
        print(f"\n🔄 ENVIANDO email con LOGO para: {usuario.email}")
        
        # Obtener logo en base64
        logo_base64 = get_logo_base64()
        
        # Datos del contexto para el template
        context = {
            'usuario': usuario,
            'token': token,
            'now': timezone.now(),
            'logo_base64': logo_base64,  # ← IMPORTANTE: Incluir logo
        }
        
        # Renderizar template
        html_content = render_to_string('authentication/emails/recuperacion_codigo.html', context)
        
        # Texto plano
        text_content = f"""SmartPocket - Verificación de seguridad

Estimado {usuario.getNombre()},

Código de verificación: {token.codigo}

Válido por 15 minutos - Máximo 5 intentos
No compartir con terceros

IP: {token.ip_solicitud or 'No disponible'}
Fecha: {token.creado_en.strftime('%d/%m/%Y %H:%M')}

SmartPocket - Sistema financiero
"""
        
        # Configurar email
        asunto = f'Verificación de cuenta SmartPocket - Código {token.codigo}'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [usuario.email]
        
        print(f"📧 Email configurado con logo: {'✅' if logo_base64 else '❌'}")
        
        # Crear email
        email = EmailMultiAlternatives(
            subject=asunto,
            body=text_content,
            from_email=from_email,
            to=to_email,
            headers=optimize_email_headers()
        )
        
        # Adjuntar HTML
        email.attach_alternative(html_content, "text/html")
        
        # Enviar
        resultado = email.send()
        print(f"📊 Email enviado: {'✅' if resultado > 0 else '❌'}")
        
        return resultado > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False