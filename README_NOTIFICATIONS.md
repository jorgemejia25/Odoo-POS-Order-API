# 🔔 Sistema de Notificaciones para POS Order API

## Descripción

El módulo POS Order API ahora incluye un sistema completo de notificaciones que alerta automáticamente cuando se recibe una nueva orden desde el ecommerce.

## Funcionalidades

### ✨ Características principales:

1. **Notificaciones automáticas**: Cada orden creada vía API genera una notificación instantánea
2. **Canal dedicado**: Se crea automáticamente un canal "Notificaciones Ecommerce" 
3. **Información completa**: Las notificaciones incluyen todos los datos relevantes de la orden
4. **Tiempo real**: Las notificaciones aparecen inmediatamente tras crear la orden

### 📱 Tipos de notificación:

- **Canal de mensajes**: Mensaje detallado en el canal "Notificaciones Ecommerce"
- **Bus notification**: Notificación en tiempo real para interfaces reactivas

## Configuración

### Dependencias agregadas:
- `mail`: Para sistema de mensajería de Odoo
- `bus`: Para notificaciones en tiempo real

### Instalación automática:
Al instalar o actualizar el módulo, se configurará automáticamente:
- Canal "Notificaciones Ecommerce"
- Usuario administrador agregado al canal
- Sistema de notificaciones activado

## Uso

### Para ver las notificaciones:

1. **Inicia sesión en Odoo**
   ```
   http://localhost:8069
   ```

2. **Ve al módulo "Conversaciones"**
   - En el menú principal, busca "Conversaciones"
   - Haz clic en "Canales"

3. **Localiza el canal "Notificaciones Ecommerce"**
   - Se crea automáticamente la primera vez que se envía una orden
   - Únete al canal si no estás incluido automáticamente

4. **Envía una orden de prueba**
   - Usa cualquier endpoint del API
   - Ve inmediatamente la notificación en el canal

### Formato de notificación:

```
🛒 Nueva orden de ecommerce recibida

📋 Referencia: POS/2024/12/0001
👤 Cliente: Juan Pérez
💰 Total: $45.50
🏪 Punto de venta: ECommerce
🆔 ID de orden: 123

¡Orden procesada exitosamente!
```

## Pruebas

### Órdenes de prueba incluidas en `sample.http`:

1. **Pedido simple**: Producto individual para probar notificación básica
2. **Pedido con extras**: Múltiples productos con extras para probar cálculos
3. **Punto de venta personalizado**: Prueba con nombre de tienda específico

### Ejemplo de prueba:

```http
POST http://localhost:8069/api/pos/order
Content-Type: application/json
Cookie: session_id=tu_session_id

{
  "partner_id": 7,
  "lines": [
    {
      "product_name": "Prueba Notificación - Pizza",
      "qty": 1,
      "price_unit": 25.50,
      "note": "Orden de prueba para notificaciones"
    }
  ]
}
```

## Logs y debugging

### Logs de notificaciones:
- Notificación enviada: `INFO: Notificación enviada al canal para la orden POS/...`
- Error en notificación: `ERROR: Error al enviar notificación: ...`
- Canal creado: `INFO: Canal 'Notificaciones Ecommerce' creado exitosamente`

### Verificación en logs:
```bash
# Ver logs en tiempo real
docker logs -f odoo-container-name

# Buscar logs específicos de notificaciones
docker logs odoo-container-name | grep "Notificación"
```

## Beneficios

### 🎯 Para el negocio:
- **Respuesta inmediata**: Saber al instante cuando llega un pedido
- **Control total**: Ver todos los pedidos centralizados en un lugar
- **Eficiencia**: No necesidad de revisar manualmente el sistema

### 🔧 Para desarrolladores:
- **Escalable**: Fácil agregar más tipos de notificaciones
- **Configurable**: Canal y mensaje personalizables
- **Robusto**: Manejo de errores incluido

## Personalización

### Modificar el mensaje de notificación:
Edita el método `send_ecommerce_notification` en `models/pos_order.py`:

```python
message = f"""
🛒 Tu mensaje personalizado aquí
📋 Referencia: {pos_reference}
...
"""
```

### Agregar más canales:
Crea nuevos canales modificando `_get_or_create_ecommerce_channel()`:

```python
channel = Channel.sudo().create({
    'name': 'Tu Canal Personalizado',
    'description': 'Descripción del canal',
    'channel_type': 'channel',
    'public': 'public',
})
```

### Notificaciones por email:
Puedes extender el sistema para enviar emails:

```python
# En el método send_ecommerce_notification
template = self.env.ref('tu_modulo.email_template_nueva_orden')
template.send_mail(order.id, force_send=True)
```

## Solución de problemas

### La notificación no aparece:
1. Verifica que tengas la cookie de sesión correcta
2. Asegúrate de estar en el canal "Notificaciones Ecommerce"
3. Revisa los logs de Odoo para errores

### El canal no se crea:
1. Verifica que el módulo `mail` esté instalado
2. Comprueba que el usuario tenga permisos de administrador
3. Reinstala el módulo si es necesario

### Errores de bus notification:
1. Verifica que el módulo `bus` esté instalado
2. Asegúrate de que el servicio de WebSocket esté funcionando
3. Revisa la consola del navegador por errores JavaScript

---

¡Disfruta del nuevo sistema de notificaciones para tu ecommerce! 🎉 