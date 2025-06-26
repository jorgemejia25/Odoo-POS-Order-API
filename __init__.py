from . import controllers
from . import models

def post_init_hook(env):
    """
    Hook que se ejecuta después de instalar/actualizar el módulo
    Restaura automáticamente los permisos de POS
    """
    try:
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info("Ejecutando post_init_hook para restaurar permisos de POS...")
        
        # Llamar a la función de restauración de permisos
        users_model = env['res.users']
        users_model.restore_pos_permissions()
        
        _logger.info("Post_init_hook completado exitosamente")
        
    except Exception as e:
        _logger.error(f"Error en post_init_hook: {str(e)}")