# authentication/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Usuario

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Buscar usuario por email
        try:
            user = Usuario.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido {user.getNombre()}!')
                return redirect('authentication:dashboard')  # Redirigir a dashboard (inicio)
            else:
                messages.error(request, 'Credenciales incorrectas.')
        except Usuario.DoesNotExist:
            messages.error(request, 'No existe una cuenta con ese email.')
    
    return render(request, 'authentication/login.html')

@login_required
def dashboard_view(request):
    """Vista del Dashboard - Página principal con resumen financiero"""
    context = {
        'usuario': request.user,
    }
    return render(request, 'authentication/dashboard.html', context)

@login_required
def perfil_view(request):
    """Vista del perfil de usuario"""
    return render(request, 'authentication/perfil.html')

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