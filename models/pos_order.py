from odoo import models, api, fields
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def send_ecommerce_notification(self, order_data):
        """
        Envía una actividad/notificación visible en el panel de actividades
        cuando se crea una orden desde el ecommerce
        """
        try:
            # Trabajar con sudo para tener permisos completos
            self = self.sudo()
            
            # Obtener información de la orden
            order_id = order_data.get('order_id')
            pos_reference = order_data.get('pos_reference')
            partner_id = order_data.get('partner_id')
            amount_total = order_data.get('calculated_totals', {}).get('amount_total', 0.0)
            pos_name = order_data.get('pos_name', 'ECommerce')
            
            # Obtener el nombre del cliente
            partner = self.env['res.partner'].browse(partner_id)
            partner_name = partner.name if partner.exists() else 'Cliente Desconocido'
            
            # Obtener usuarios que deben recibir la notificación
            users_to_notify = self._get_users_to_notify()
            
            if not users_to_notify:
                _logger.warning("No se encontraron usuarios para notificar")
                return
            
            # Crear actividad directa en el sistema usando el modelo res.users
            for user in users_to_notify:
                try:
                    # Crear actividad en el modelo res.users para que aparezca en actividades
                    activity_vals = {
                        'activity_type_id': 1,  # Usar el primer tipo disponible (Todo)
                        'summary': f'🛒 Nueva Orden Ecommerce: {pos_reference}',
                        'note': f'''Nueva orden recibida:
• Referencia: {pos_reference}
• Cliente: {partner_name}  
• Total: ${amount_total:.2f}
• Tienda: {pos_name}
• ID: {order_id}''',
                        'res_model_id': self.env['ir.model']._get('res.users').id,
                        'res_id': user.id,
                        'user_id': user.id,
                        'date_deadline': fields.Date.today(),
                    }
                    
                    activity = self.env['mail.activity'].create(activity_vals)
                    _logger.info(f"Actividad creada para usuario {user.name}: {activity.id}")
                    
                except Exception as activity_error:
                    _logger.error(f"Error al crear actividad: {str(activity_error)}")
                    
                    # Fallback: Crear notificación directa con bus
                    try:
                        self.env['bus.bus']._sendone(
                            user.partner_id,
                            'simple_notification',
                            {
                                'type': 'success',
                                'title': '🛒 Nueva Orden Ecommerce',
                                'message': f'Orden {pos_reference} - Cliente: {partner_name} - Total: ${amount_total:.2f}',
                                'sticky': True
                            }
                        )
                        _logger.info(f"Notificación bus enviada a {user.name}")
                    except Exception as bus_error:
                        _logger.error(f"Error en notificación bus: {str(bus_error)}")
            
            # Crear mensaje en la orden también
            try:
                order_record = self.browse(order_id)
                if order_record.exists():
                    order_record.message_post(
                        body=f'''
                        <div style="background: #e8f5e8; padding: 10px; border-left: 3px solid #28a745;">
                            <h4>🛒 Orden Ecommerce Procesada</h4>
                            <p><strong>Ref:</strong> {pos_reference} | <strong>Cliente:</strong> {partner_name} | <strong>Total:</strong> ${amount_total:.2f}</p>
                            <p>📢 {len(users_to_notify)} usuario(s) notificado(s)</p>
                        </div>
                        ''',
                        subject=f"Orden Ecommerce: {pos_reference}",
                        message_type='comment'
                    )
                    _logger.info(f"Mensaje agregado al chatter de la orden {order_id}")
            except Exception as chatter_error:
                _logger.error(f"Error al agregar mensaje al chatter: {str(chatter_error)}")
            
            _logger.info(f"Sistema de notificaciones completado para orden {pos_reference}")
            
        except Exception as e:
            _logger.error(f"Error en sistema de notificación de ecommerce: {str(e)}")
    
    @api.model
    def _get_users_to_notify(self):
        """
        Obtiene la lista de usuarios que deben recibir notificaciones
        Prioriza usuarios de Point of Sale y ventas
        """
        try:
            users_to_notify = []
            
            # Opción 1: Buscar usuarios del grupo Point of Sale Manager
            try:
                pos_manager_group = self.env.ref('point_of_sale.group_pos_manager', raise_if_not_found=False)
                if pos_manager_group:
                    pos_manager_users = pos_manager_group.users
                    if pos_manager_users:
                        users_to_notify.extend(pos_manager_users)
                        _logger.info(f"Encontrados {len(pos_manager_users)} usuarios del grupo POS Manager")
            except Exception as e:
                _logger.warning(f"No se pudo encontrar grupo POS Manager: {str(e)}")
            
            # Opción 2: Buscar usuarios del grupo Point of Sale User
            try:
                pos_user_group = self.env.ref('point_of_sale.group_pos_user', raise_if_not_found=False)
                if pos_user_group:
                    pos_user_users = pos_user_group.users
                    if pos_user_users:
                        users_to_notify.extend(pos_user_users)
                        _logger.info(f"Encontrados {len(pos_user_users)} usuarios del grupo POS User")
            except Exception as e:
                _logger.warning(f"No se pudo encontrar grupo POS User: {str(e)}")
            
            # Opción 3: Buscar usuarios del grupo de ventas
            try:
                sales_group = self.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
                if sales_group:
                    sales_users = sales_group.users
                    if sales_users:
                        users_to_notify.extend(sales_users)
                        _logger.info(f"Encontrados {len(sales_users)} usuarios del grupo de ventas")
            except Exception as e:
                _logger.warning(f"No se pudo encontrar grupo de ventas: {str(e)}")
            
            # Opción 4: Buscar usuarios que tengan acceso a cualquier punto de venta
            try:
                # Buscar usuarios que estén asignados a alguna sesión de POS activa o reciente
                pos_sessions = self.env['pos.session'].search([
                    ('state', 'in', ['opened', 'closing_control', 'closed'])
                ], limit=50)
                
                pos_session_users = pos_sessions.mapped('user_id')
                if pos_session_users:
                    users_to_notify.extend(pos_session_users)
                    _logger.info(f"Encontrados {len(pos_session_users)} usuarios con sesiones de POS")
            except Exception as e:
                _logger.warning(f"No se pudo encontrar usuarios de sesiones POS: {str(e)}")
            
            # Opción 5: Si no hay usuarios específicos de POS, buscar administradores
            if not users_to_notify:
                try:
                    admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
                    if admin_group:
                        admin_users = admin_group.users
                        if admin_users:
                            users_to_notify.extend(admin_users)
                            _logger.info(f"Encontrados {len(admin_users)} usuarios administradores")
                except Exception as e:
                    _logger.warning(f"No se pudo encontrar grupo de administradores: {str(e)}")
            
            # Opción 6: Como último recurso, el usuario administrador principal
            if not users_to_notify:
                try:
                    admin_user = self.env.ref('base.user_admin', raise_if_not_found=False)
                    if admin_user:
                        users_to_notify.append(admin_user)
                        _logger.info("Usando usuario administrador principal")
                except Exception as e:
                    _logger.warning(f"No se pudo encontrar usuario administrador: {str(e)}")
            
            # Opción 7: Buscar cualquier usuario activo (último recurso)
            if not users_to_notify:
                active_users = self.env['res.users'].search([
                    ('active', '=', True),
                    ('share', '=', False)  # Usuarios internos solamente
                ], limit=10)
                if active_users:
                    users_to_notify.extend(active_users)
                    _logger.info(f"Usando {len(active_users)} usuarios activos como último recurso")
            
            # Filtrar usuarios válidos (activos y no compartidos)
            valid_users = []
            for user in users_to_notify:
                if user.active and not user.share:
                    valid_users.append(user)
            
            # Eliminar duplicados manteniendo el orden
            seen = set()
            unique_users = []
            for user in valid_users:
                if user.id not in seen:
                    seen.add(user.id)
                    unique_users.append(user)
            
            _logger.info(f"Total usuarios únicos para notificar: {len(unique_users)}")
            
            # Log de usuarios específicos para debugging
            for user in unique_users:
                _logger.info(f"Usuario a notificar: {user.name} (ID: {user.id}) - Email: {user.email}")
            
            return unique_users
            
        except Exception as e:
            _logger.error(f"Error al obtener usuarios para notificar: {str(e)}")
            return []
    
    @api.model
    def send_simple_notification(self, order_data):
        """
        Versión simplificada de notificación que solo usa logs
        """
        try:
            order_id = order_data.get('order_id')
            pos_reference = order_data.get('pos_reference', 'N/A')
            partner_id = order_data.get('partner_id')
            amount_total = order_data.get('calculated_totals', {}).get('amount_total', 0.0)
            pos_name = order_data.get('pos_name', 'ECommerce')
            
            # Obtener nombre del cliente de forma segura
            try:
                partner = self.env['res.partner'].sudo().browse(partner_id)
                partner_name = partner.name if partner.exists() else 'Cliente Desconocido'
            except:
                partner_name = f'Cliente ID: {partner_id}'
            
            # Crear mensaje simple
            notification_message = (
                f"🛒 NUEVA ORDEN ECOMMERCE - "
                f"Ref: {pos_reference} | "
                f"Cliente: {partner_name} | "
                f"Total: ${amount_total:.2f} | "
                f"Tienda: {pos_name} | "
                f"ID: {order_id}"
            )
            
            _logger.info(notification_message)
            _logger.info("=" * 80)
            
        except Exception as e:
            _logger.error(f"Error en notificación simple: {str(e)}")
    
    @api.model
    def send_message_notification(self, order_data):
        """
        Método alternativo usando mail.message directamente
        """
        try:
            order_id = order_data.get('order_id')
            pos_reference = order_data.get('pos_reference', 'N/A')
            partner_id = order_data.get('partner_id')
            amount_total = order_data.get('calculated_totals', {}).get('amount_total', 0.0)
            
            # Crear un mensaje en la orden directamente
            message_body = f"""
            <div style="background: #f0f8ff; padding: 15px; border-left: 4px solid #007bff; margin: 10px 0;">
                <h3 style="color: #007bff; margin: 0 0 10px 0;">🛒 Nueva Orden Ecommerce</h3>
                <p><strong>📋 Referencia:</strong> {pos_reference}</p>
                <p><strong>💰 Total:</strong> ${amount_total:.2f}</p>
                <p><strong>🆔 ID Orden:</strong> {order_id}</p>
                <p style="color: #28a745;"><strong>✅ Orden procesada exitosamente</strong></p>
            </div>
            """
            
            # Crear mensaje en la orden
            if order_id:
                order_record = self.sudo().browse(order_id)
                if order_record.exists():
                    order_record.message_post(
                        body=message_body,
                        subject=f"Nueva Orden Ecommerce: {pos_reference}"
                    )
                    _logger.info(f"Mensaje creado en la orden {order_id}")
            
        except Exception as e:
            _logger.error(f"Error en notificación por mensaje: {str(e)}")

    @api.model
    def get_notification_groups_info(self):
        """
        Método para debugging: obtiene información sobre los grupos disponibles
        """
        try:
            group_info = []
            
            # Verificar grupos específicos de POS
            pos_groups = [
                ('point_of_sale.group_pos_manager', 'POS Manager'),
                ('point_of_sale.group_pos_user', 'POS User'),
                ('sales_team.group_sale_salesman', 'Sales User'),
                ('sales_team.group_sale_manager', 'Sales Manager'),
                ('base.group_user', 'Internal User'),
                ('base.group_system', 'Settings'),
            ]
            
            for group_ref, group_name in pos_groups:
                try:
                    group = self.env.ref(group_ref, raise_if_not_found=False)
                    if group:
                        users_count = len(group.users)
                        active_users = group.users.filtered('active')
                        group_info.append({
                            'name': group_name,
                            'xml_id': group_ref,
                            'total_users': users_count,
                            'active_users': len(active_users),
                            'user_names': [u.name for u in active_users]
                        })
                        _logger.info(f"Grupo {group_name}: {len(active_users)} usuarios activos")
                    else:
                        group_info.append({
                            'name': group_name,
                            'xml_id': group_ref,
                            'error': 'Grupo no encontrado'
                        })
                        _logger.warning(f"Grupo {group_name} no encontrado")
                except Exception as e:
                    group_info.append({
                        'name': group_name,
                        'xml_id': group_ref,
                        'error': str(e)
                    })
                    _logger.error(f"Error verificando grupo {group_name}: {str(e)}")
            
            return group_info
            
        except Exception as e:
            _logger.error(f"Error obteniendo información de grupos: {str(e)}")
            return []

    @api.model 
    def send_notification_to_all_pos_users(self, order_data):
        """
        Método alternativo que envía notificaciones a TODOS los usuarios con acceso a POS
        usando una estrategia más agresiva para encontrar usuarios
        """
        try:
            order_id = order_data.get('order_id')
            pos_reference = order_data.get('pos_reference', 'N/A')
            partner_id = order_data.get('partner_id')
            amount_total = order_data.get('calculated_totals', {}).get('amount_total', 0.0)
            pos_name = order_data.get('pos_name', 'ECommerce')
            
            # Obtener el nombre del cliente
            partner = self.env['res.partner'].browse(partner_id)
            partner_name = partner.name if partner.exists() else 'Cliente Desconocido'
            
            # Estrategia 1: Buscar TODOS los usuarios internos activos
            all_internal_users = self.env['res.users'].search([
                ('active', '=', True),
                ('share', '=', False),  # Solo usuarios internos (no portal)
            ])
            
            notification_count = 0
            
            for user in all_internal_users:
                try:
                    # Enviar notificación bus a cada usuario
                    self.env['bus.bus']._sendone(
                        user.partner_id,
                        'simple_notification',
                        {
                            'type': 'success',
                            'title': '🛒 Nueva Orden Ecommerce',
                            'message': f'Orden {pos_reference} - Cliente: {partner_name} - Total: ${amount_total:.2f}',
                            'sticky': True
                        }
                    )
                    
                    # También crear actividad para cada usuario
                    activity_vals = {
                        'activity_type_id': 1,  # Todo
                        'summary': f'🛒 Nueva Orden Ecommerce: {pos_reference}',
                        'note': f'''
                        <p><strong>Nueva orden recibida desde ecommerce</strong></p>
                        <ul>
                            <li><strong>Referencia:</strong> {pos_reference}</li>
                            <li><strong>Cliente:</strong> {partner_name}</li>
                            <li><strong>Total:</strong> ${amount_total:.2f}</li>
                            <li><strong>Tienda:</strong> {pos_name}</li>
                            <li><strong>ID:</strong> {order_id}</li>
                        </ul>
                        ''',
                        'res_model_id': self.env['ir.model']._get('res.users').id,
                        'res_id': user.id,
                        'user_id': user.id,
                        'date_deadline': fields.Date.today(),
                    }
                    
                    self.env['mail.activity'].create(activity_vals)
                    notification_count += 1
                    _logger.info(f"Notificación enviada a usuario: {user.name} ({user.email})")
                    
                except Exception as user_error:
                    _logger.warning(f"Error enviando notificación a {user.name}: {str(user_error)}")
            
            _logger.info(f"Notificaciones enviadas a {notification_count} usuarios internos")
            return notification_count
            
        except Exception as e:
            _logger.error(f"Error en notificación masiva a usuarios POS: {str(e)}")
            return 0
