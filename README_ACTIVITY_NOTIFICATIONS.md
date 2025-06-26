# 🔔 Sistema de Notificaciones de Actividades para POS Order API

## Descripción

El módulo POS Order API ahora incluye un sistema robusto de notificaciones basado en **actividades de Odoo** que aparecen directamente en el **buzón de entrada** de los usuarios cuando se recibe una nueva orden desde el ecommerce.

## ✨ Funcionalidades Principales

### 🎯 **Notificaciones en el Buzón de Entrada**
- **Actividades automáticas**: Cada orden crea una actividad visible en el buzón de entrada
- **Múltiples usuarios**: Notifica automáticamente a usuarios de ventas y administradores
- **Información completa**: Incluye todos los datos relevantes de la orden
- **Formato HTML**: Mensajes formateados con estilos visuales atractivos

### 📱 **Tipos de Notificación**
1. **Actividad Principal**: Aparece en el buzón de entrada de usuarios
2. **Mensaje en Chatter**: Se agrega al historial de la orden
3. **Logs detallados**: Para seguimiento técnico

### 👥 **Usuarios Notificados**
El sistema busca usuarios en este orden de prioridad:
1. **Usuarios del grupo de ventas** (`sales_team.group_sale_salesman`)
2. **Usuarios administradores** (`base.group_system`)  
3. **Usuario administrador principal** (`base.user_admin`)
4. **Cualquier usuario interno activo** (como fallback)

## 🛠️ Configuración

### Dependencias Requeridas
```python
'depends': ["point_of_sale", "base", "mail", "bus"]
```

### Instalación Automática
Al instalar o actualizar el módulo, se configura automáticamente:
- ✅ Tipo de actividad "Nueva Orden Ecommerce"
- ✅ Sistema de notificaciones activado
- ✅ Detección automática de usuarios a notificar

## 📋 Formato de Notificación

### En el Buzón de Entrada
```
🛒 Nueva Orden Ecommerce: ORD-135

┌─────────────────────────────────────┐
│ 🛒 Nueva Orden de Ecommerce         │
│                                     │
│ 📋 Referencia: ORD-135             │
│ 👤 Cliente: Brandon Freeman        │
│ 💰 Total: $20.00                  │
│ 🏪 Tienda: ECommerce               │
│ 🆔 ID Orden: 135                   │
│                                     │
│ ✅ Orden procesada exitosamente    │
└─────────────────────────────────────┘
```

### En el Chatter de la Orden
```
🛒 Orden Ecommerce Creada

📋 Referencia: ORD-135
👤 Cliente: Brandon Freeman  
💰 Total: $20.00
🏪 Tienda: ECommerce
📢 Notificaciones enviadas a 3 usuario(s)
```

## 🧪 Pruebas y Verificación

### 1. **Verificar en el Buzón de Entrada**
1. Inicia sesión en Odoo: `http://localhost:8069`
2. Ve al **Buzón de Entrada** (icono de sobre en la barra superior)
3. Busca actividades del tipo "Nueva Orden Ecommerce"

### 2. **Enviar Orden de Prueba**
```http
POST http://localhost:8069/api/pos/order
Content-Type: application/json

{
  "partner_id": 7,
  "lines": [
    {
      "product_name": "Test Actividad - Pizza",
      "qty": 1,
      "price_unit": 25.50,
      "note": "Prueba del sistema de actividades"
    }
  ]
}
```

### 3. **Verificar en Actividades**
1. Ve a **Aplicaciones** → **Conversaciones** → **Actividades**
2. Busca actividades con resumen "🛒 Nueva Orden Ecommerce"
3. Verifica que aparezcan para múltiples usuarios

## 📊 Logs Esperados

### Éxito Completo
```
INFO: Encontrados 2 usuarios del grupo de ventas
INFO: Tipo de actividad creado: 1
INFO: Actividad creada para usuario Administrator: 15
INFO: Actividad creada para usuario Usuario Ventas: 16
INFO: Mensaje agregado al chatter de la orden 135
INFO: Sistema de notificaciones completado para orden ORD-135
```

### Con Fallbacks
```
WARNING: No se pudo encontrar grupo de ventas: [error details]
INFO: Encontrados 1 usuarios administradores
INFO: Usando tipo de actividad existente: 1
INFO: Total usuarios únicos para notificar: 1
INFO: Sistema de notificaciones completado para orden ORD-136
```

## 🎯 Ventajas del Sistema de Actividades

### ✅ **Versus Canales**
- **Más visible**: Aparece directamente en el buzón principal
- **Individual**: Cada usuario recibe su propia notificación
- **Persistente**: No se pierde entre otros mensajes
- **Organizado**: Se puede marcar como completado

### ✅ **Versus Notificaciones Bus**
- **Garantizado**: No depende de conexión websocket
- **Persistente**: Permanece hasta ser marcada como leída
- **Accesible**: Visible desde cualquier parte de Odoo
- **Historial**: Se mantiene registro de todas las notificaciones

## 🔧 Personalización

### Modificar Usuarios Notificados
Edita el método `_get_users_to_notify()` en `models/pos_order.py`:

```python
def _get_users_to_notify(self):
    # Agregar grupo personalizado
    custom_group = self.env.ref('tu_modulo.group_custom')
    if custom_group:
        return custom_group.users
    # ... resto del código
```

### Personalizar Tipo de Actividad
Modifica `_get_or_create_activity_type()`:

```python
activity_type = self.env['mail.activity.type'].create({
    'name': 'Tu Nombre Personalizado',
    'summary': 'Tu descripción personalizada',
    'icon': 'fa-custom-icon',
    'decoration_type': 'warning',  # o 'danger', 'success'
})
```

### Modificar Mensaje de Actividad
Personaliza el contenido en `send_ecommerce_notification()`:

```python
'note': f'''
    <div style="padding: 10px; border-left: 4px solid #ff6b35;">
        <h4>🔥 Tu Mensaje Personalizado</h4>
        <p>Contenido personalizado aquí...</p>
    </div>
'''
```

## 🚨 Solución de Problemas

### La actividad no aparece en el buzón
1. **Verifica permisos**: El usuario debe tener permisos para ver actividades
2. **Revisa logs**: Busca errores en `docker logs odoo-container`
3. **Comprueba grupo**: Asegúrate de que el usuario esté en un grupo notificado

### Múltiples notificaciones duplicadas
1. **Revisa usuarios**: Verifica que no haya usuarios duplicados en grupos
2. **Logs únicos**: El sistema elimina duplicados automáticamente
3. **Reinicia módulo**: Actualiza el módulo si es necesario

### Tipo de actividad no se crea
1. **Permisos**: Verifica permisos de administrador
2. **Módulos**: Asegúrate de que el módulo `mail` esté instalado
3. **Base de datos**: Verifica que no haya restricciones

## 📈 Beneficios del Negocio

### 🎯 **Para Administradores**
- **Visibilidad inmediata**: Saber al instante sobre nuevos pedidos
- **Control centralizado**: Todas las notificaciones en un lugar
- **Seguimiento**: Historial completo de órdenes recibidas

### 🎯 **Para Equipos de Ventas**
- **Respuesta rápida**: Atender pedidos inmediatamente
- **Organización**: Gestionar pendientes desde el buzón
- **Eficiencia**: No perderse ningún pedido importante

### 🎯 **Para Desarrolladores**
- **Escalable**: Fácil agregar más tipos de notificaciones
- **Mantenible**: Código limpio y bien estructurado  
- **Robusto**: Múltiples niveles de fallback incluidos

---

¡El sistema de notificaciones de actividades está listo para usar! 🎉

**Próximos pasos sugeridos:**
1. Envía una orden de prueba
2. Verifica las notificaciones en el buzón
3. Personaliza según tus necesidades específicas
4. ¡Disfruta de las notificaciones instantáneas! 