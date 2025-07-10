# authentication/utils.py
import base64
import os
from django.conf import settings
from django.templatetags.static import static

def get_logo_base64():
    """
    Convierte el logo a base64 para incrustarlo en emails
    Returns: str - Logo en formato base64 o None si no existe
    """
    try:
        # Buscar el logo en diferentes ubicaciones posibles
        logo_paths = [
            os.path.join(settings.BASE_DIR, 'static', 'images', 'LogoSP.png'),
            os.path.join(settings.BASE_DIR, 'staticfiles', 'images', 'LogoSP.png'),
            os.path.join(settings.BASE_DIR, 'authentication', 'static', 'images', 'LogoSP.png'),
        ]
        
        logo_path = None
        for path in logo_paths:
            if os.path.exists(path):
                logo_path = path
                break
        
        if not logo_path:
            print("⚠️ Logo LogoSP.png no encontrado en ninguna ubicación")
            return None
        
        # Leer y convertir a base64
        with open(logo_path, 'rb') as img_file:
            img_data = img_file.read()
            base64_string = base64.b64encode(img_data).decode('utf-8')
            return f"data:image/png;base64,{base64_string}"
    
    except Exception as e:
        print(f"❌ Error convirtiendo logo a base64: {e}")
        return None

def get_icon_svg(icon_name):
    """
    Retorna SVG icons profesionales para reemplazar emojis
    """
    icons = {
        'money': '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L15 4L12 5.5L9 4L3 7V9H4V19H20V9H21ZM18 17H6V9H18V17ZM12 10C10.9 10 10 10.9 10 12S10.9 14 12 14S14 13.1 14 12S13.1 10 12 10Z" fill="currentColor"/>
        </svg>''',
        
        'chart': '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M19 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19V5C21 3.9 20.1 3 19 3ZM19 19H5V5H19V19ZM17 17H7V10H17V17ZM11 6H13V9H11V6ZM15 7H17V9H15V7ZM7 7H9V9H7V7Z" fill="currentColor"/>
        </svg>''',
        
        'target': '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C6.48 2 2 6.48 2 12S6.48 22 12 22S22 17.52 22 12S17.52 2 12 2ZM12 20C7.59 20 4 16.41 4 12S7.59 4 12 4S20 7.59 20 12S16.41 20 12 20ZM12 6C8.69 6 6 8.69 6 12S8.69 18 12 18S18 15.31 18 12S15.31 6 12 6ZM12 16C9.79 16 8 14.21 8 12S9.79 8 12 8S16 9.79 16 12S14.21 16 12 16ZM12 10C10.9 10 10 10.9 10 12S10.9 14 12 14S14 13.1 14 12S13.1 10 12 10Z" fill="currentColor"/>
        </svg>''',
        
        'bulb': '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M9 21C9 21.6 9.4 22 10 22H14C14.6 22 15 21.6 15 21V20H9V21ZM12 2C8.1 2 5 5.1 5 9C5 11.4 6.2 13.5 8 14.7V17C8 17.6 8.4 18 9 18H15C15.6 18 16 17.6 16 17V14.7C17.8 13.5 19 11.4 19 9C19 5.1 15.9 2 12 2ZM14.5 13L14 13.3V16H10V13.3L9.5 13C8.1 12.2 7 10.7 7 9C7 6.2 9.2 4 12 4S17 6.2 17 9C17 10.7 15.9 12.2 14.5 13Z" fill="currentColor"/>
        </svg>''',
        
        'celebration': '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M2 20H22L20 17H4L2 20ZM5.27 15H18.73L17.73 13H6.27L5.27 15ZM7.54 11H16.46L15.46 9H8.54L7.54 11ZM4 7V5H6V4H4V2H2V4H0V5H2V7H4ZM10.5 3.5L9.5 1.5L8.5 3.5L6.5 2.5L7.5 4.5L5.5 5.5L7.5 6.5L6.5 8.5L8.5 7.5L9.5 9.5L10.5 7.5L12.5 8.5L11.5 6.5L13.5 5.5L11.5 4.5L12.5 2.5L10.5 3.5ZM19 2V4H21V5H19V7H18V5H16V4H18V2H19Z" fill="currentColor"/>
        </svg>''',
        
        'security': '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 1L3 5V11C3 16.55 6.84 21.74 12 23C17.16 21.74 21 16.55 21 11V5L12 1ZM19 11C19 15.52 16.02 19.69 12 20.74C7.98 19.69 5 15.52 5 11V6.3L12 3.18L19 6.3V11ZM15 9H9V7H15V9ZM15 13H9V11H15V13ZM15 17H9V15H15V17Z" fill="currentColor"/>
        </svg>''',
    }
    
    return icons.get(icon_name, '')

def optimize_email_headers():
    """
    Retorna headers optimizados para evitar SPAM
    """
    return {
        'X-Priority': '3',
        'X-MSMail-Priority': 'Normal',
        'X-Mailer': 'SmartPocket Financial System',
        'X-MimeOLE': 'Produced By SmartPocket',
        'Importance': 'Normal',
        'List-Unsubscribe': '<mailto:unsubscribe@smartpocket.com>',
        'X-Auto-Response-Suppress': 'OOF, DR, RN, NRN',
    }

def get_professional_subject(tipo, usuario_nombre):
    """
    Genera asuntos profesionales para evitar SPAM
    """
    subjects = {
        'bienvenida': f'Cuenta creada - SmartPocket | {usuario_nombre}',
        'recuperacion': f'Verificación de seguridad - SmartPocket | Código: ',
    }
    return subjects.get(tipo, 'SmartPocket - Notificación')