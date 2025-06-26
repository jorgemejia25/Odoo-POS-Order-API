from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def restore_pos_permissions(self):
        """
        Restaura los permisos de POS para usuarios que los han perdido
        Se ejecuta automáticamente al iniciar el módulo
        """
        try:
            _logger.info("Iniciando restauración de permisos de POS...")
            
            # Obtener el grupo de manager de POS
            pos_manager_group = self.env.ref('point_of_sale.group_pos_manager', raise_if_not_found=False)
            pos_user_group = self.env.ref('point_of_sale.group_pos_user', raise_if_not_found=False)
            # Intentar obtener el grupo de ventas (puede no estar disponible en todas las versiones)
            try:
                sales_user_group = self.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
            except:
                try:
                    sales_user_group = self.env.ref('sale.group_sale_salesman', raise_if_not_found=False)
                except:
                    sales_user_group = None
                    _logger.info("Grupo de ventas no encontrado, continuando sin él")
            
            if not pos_manager_group:
                _logger.warning("Grupo 'point_of_sale.group_pos_manager' no encontrado")
                return
            
            # Restaurar permisos del administrador
            admin_user = self.env.ref('base.user_admin', raise_if_not_found=False)
            if admin_user:
                admin_user.sudo().write({
                    'groups_id': [(4, pos_manager_group.id)]
                })
                if pos_user_group:
                    admin_user.sudo().write({
                        'groups_id': [(4, pos_user_group.id)]
                    })
                if sales_user_group:
                    admin_user.sudo().write({
                        'groups_id': [(4, sales_user_group.id)]
                    })
                _logger.info(f"Permisos de POS restaurados para usuario administrador")
            
            # Buscar todos los usuarios activos y restaurar permisos básicos de POS
            active_users = self.search([('active', '=', True), ('share', '=', False)])
            
            users_updated = 0
            for user in active_users:
                try:
                    # Asignar grupo básico de POS si el usuario puede acceder
                    if pos_user_group and not user.has_group('point_of_sale.group_pos_user'):
                        user.sudo().write({
                            'groups_id': [(4, pos_user_group.id)]
                        })
                        users_updated += 1
                        _logger.info(f"Permisos básicos de POS asignados a usuario: {user.name}")
                        
                except Exception as e:
                    _logger.warning(f"No se pudieron restaurar permisos para usuario {user.name}: {str(e)}")
            
            _logger.info(f"Restauración de permisos completada. {users_updated} usuarios actualizados.")
            
            # Guardar parámetro de configuración para marcar que se ejecutó
            self.env['ir.config_parameter'].sudo().set_param(
                'pos_order_api.last_permission_restore', 
                fields.Datetime.now()
            )
            
        except Exception as e:
            _logger.error(f"Error durante la restauración de permisos de POS: {str(e)}")

    @api.model
    def _auto_assign_pos_groups(self):
        """
        Auto-asigna grupos de POS a usuarios que los necesiten
        """
        try:
            auto_assign = self.env['ir.config_parameter'].sudo().get_param(
                'pos_order_api.auto_assign_groups', 'True'
            )
            
            if auto_assign.lower() != 'true':
                return
            
            # Grupos necesarios para POS (solo los que sabemos que existen)
            required_groups = [
                'point_of_sale.group_pos_user',
            ]
            
            # Intentar agregar grupo de ventas si está disponible
            try:
                sales_group = self.env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
                if not sales_group:
                    sales_group = self.env.ref('sale.group_sale_salesman', raise_if_not_found=False)
                if sales_group:
                    required_groups.append('sales_team.group_sale_salesman')
            except:
                _logger.info("Grupo de ventas no disponible para auto-asignación")
            
            # Usuarios internos activos
            internal_users = self.search([
                ('active', '=', True),
                ('share', '=', False)
            ])
            
            for user in internal_users:
                for group_xml_id in required_groups:
                    try:
                        group = self.env.ref(group_xml_id, raise_if_not_found=False)
                        if group and not user.has_group(group_xml_id):
                            user.sudo().write({
                                'groups_id': [(4, group.id)]
                            })
                            _logger.info(f"Grupo {group_xml_id} asignado a usuario {user.name}")
                    except Exception as e:
                        _logger.warning(f"Error asignando grupo {group_xml_id} a {user.name}: {str(e)}")
                        
        except Exception as e:
            _logger.error(f"Error en auto-asignación de grupos: {str(e)}")

    @api.model
    def create(self, vals):
        """
        Override para asignar automáticamente grupos de POS a nuevos usuarios
        """
        user = super(ResUsers, self).create(vals)
        
        # Auto-asignar grupos si está habilitado
        try:
            self._auto_assign_pos_groups()
        except Exception as e:
            _logger.warning(f"Error en auto-asignación para nuevo usuario: {str(e)}")
        
        return user 