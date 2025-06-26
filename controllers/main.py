from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class PosRestController(http.Controller):

    def _get_or_create_pos_session(self, pos_name='ECommerce'):
        """
        Obtiene o crea una sesión POS para el punto de venta especificado por pos_name.
        Versión mejorada que maneja mejor los duplicados y errores de transacción.
        """
        try:
            # Usar sudo para evitar problemas de permisos
            PosSession = request.env['pos.session'].sudo()
            PosConfig = request.env['pos.config'].sudo()
            
            # 1. Primero buscar cualquier sesión abierta existente (estrategia simple y segura)
            any_open_session = PosSession.search([('state', '=', 'opened')], limit=1)
            if any_open_session:
                _logger.info(f"Usando sesión abierta existente: {any_open_session.id}")
                return any_open_session.id
            
            # 2. Buscar el punto de venta por nombre
            ecommerce_config = PosConfig.search([('name', '=', pos_name)], limit=1)
            
            # Si no existe, crearlo
            if not ecommerce_config:
                try:
                    _logger.info(f"Creando nuevo punto de venta '{pos_name}'")
                    
                    # Obtener company por defecto
                    company = request.env['res.company'].sudo().search([('id', '=', 1)], limit=1)
                    if not company:
                        company = request.env['res.company'].sudo().search([], limit=1)
                    
                    # Obtener o crear un journal específico para POS
                    journal = request.env['account.journal'].sudo().search([
                        ('type', '=', 'general'),
                        ('company_id', '=', company.id),
                        ('code', 'like', 'POS%')
                    ], limit=1)
                    
                    if not journal:
                        # Crear un journal específico para POS con todos los campos requeridos
                        journal = request.env['account.journal'].sudo().create({
                            'name': 'Point of Sale',
                            'code': 'POSS',
                            'type': 'general',
                            'company_id': company.id,
                            'sequence': 10,
                        })
                    
                    # Crear el punto de venta con journal específico
                    ecommerce_config = PosConfig.create({
                        'name': pos_name,
                        'company_id': company.id,
                        'journal_id': journal.id,
                        'invoice_journal_id': journal.id,
                        'pricelist_id': 1,  # Pricelist por defecto
                        'payment_method_ids': [(6, 0, [])],  # Sin métodos de pago específicos
                        'use_pricelist': True,
                        'tax_regime_selection': False,
                        'module_account': True,
                    })
                except Exception as e:
                    _logger.error(f"Error al crear punto de venta: {str(e)}")
                    # Buscar cualquier punto de venta existente
                    ecommerce_config = PosConfig.search([], limit=1)
                    if not ecommerce_config:
                        _logger.error("No se encontró ningún punto de venta")
                        return 1
            
            # 3. Verificar si ya existe una sesión para este punto de venta
            existing_session = PosSession.search([
                ('config_id', '=', ecommerce_config.id)
            ], order="id desc", limit=1)
            
            if existing_session:
                if existing_session.state == 'opened':
                    _logger.info(f"Usando sesión existente abierta: {existing_session.id}")
                    return existing_session.id
                else:
                    # Si la sesión existe pero no está abierta, intentar abrirla
                    try:
                        if existing_session.state == 'opening_control':
                            existing_session.action_pos_session_open()
                            _logger.info(f"Sesión abierta: {existing_session.id}")
                            return existing_session.id
                    except Exception as e:
                        _logger.error(f"Error al abrir sesión existente: {str(e)}")
            
            # 4. Como último recurso, intentar crear una nueva sesión con manejo de duplicados
            try:
                # Obtener un usuario administrador
                admin_user = request.env.ref('base.user_admin', raise_if_not_found=False)
                if not admin_user:
                    admin_user = request.env['res.users'].sudo().search([('id', '=', 1)], limit=1)
                
                user_id = admin_user.id if admin_user else 1
                
                _logger.info(f"Creando nueva sesión para '{pos_name}' con usuario {user_id}")
                
                # Intentar crear sesión de forma directa
                new_session = PosSession.create({
                    'user_id': user_id,
                    'config_id': ecommerce_config.id,
                })
                
                # Intentar abrir la sesión
                try:
                    new_session.action_pos_session_open()
                    _logger.info(f"Nueva sesión creada y abierta: {new_session.id}")
                    return new_session.id
                except Exception as open_error:
                    _logger.warning(f"Sesión creada pero no se pudo abrir: {str(open_error)}")
                    return new_session.id
                        
            except Exception as e:
                _logger.error(f"Error al crear nueva sesión: {str(e)}")
            
            # 5. Si todo falla, buscar cualquier sesión disponible
            fallback_session = PosSession.search([], order="id desc", limit=1)
            if fallback_session:
                _logger.info(f"Usando sesión de respaldo: {fallback_session.id}")
                return fallback_session.id
            
            # 6. Último recurso absoluto
            _logger.warning("Usando ID de sesión fijo como último recurso")
            return 1
            
        except Exception as e:
            _logger.error(f"Error crítico en _get_or_create_pos_session: {str(e)}")
            return 1

    def _get_or_create_partner(self, partner_id=None):
        """
        Obtiene un cliente existente o crea uno nuevo si no se proporciona.
        Versión mejorada que maneja mejor los errores de permisos.
        """
        try:
            Partner = request.env['res.partner'].sudo()
            
            if partner_id:
                partner = Partner.browse(partner_id)
                if partner.exists():
                    return partner_id
            
            # Buscar un cliente existente (que no sea empresa ni proveedor)
            partner = Partner.search([
                ('is_company', '=', False),
                ('supplier_rank', '=', 0)
            ], limit=1)
            
            if partner:
                return partner.id
                
            # Crear un cliente nuevo
            try:
                new_partner = Partner.create({
                    'name': 'Cliente Ecommerce API',
                    'company_id': 1,  # Usar company_id fijo
                    'is_company': False,
                    'customer_rank': 1,
                })
                return new_partner.id
            except Exception as e:
                _logger.error(f"Error al crear nuevo cliente: {str(e)}")
                # Buscar cualquier partner existente
                fallback_partner = Partner.search([], limit=1)
                if fallback_partner:
                    return fallback_partner.id
                return 1  # Partner por defecto
                
        except Exception as e:
            _logger.error(f"Error en _get_or_create_partner: {str(e)}")
            return 1  # Partner por defecto

    def _get_or_create_product(self, product_name, price_unit=0.0):
        """
        Obtiene un producto existente o crea uno nuevo con el sufijo 'D'.
        Versión mejorada que maneja mejor los errores y transacciones abortadas.
        """
        if not product_name:
            _logger.error("Se recibió un nombre de producto vacío")
            return False

        try:
            # Usar un savepoint para manejar transacciones abortadas
            with request.env.cr.savepoint():
                Product = request.env['product.product'].sudo()
                
                # Buscar el producto con el sufijo 'D'
                product_name_with_d = f"{product_name} D"
                _logger.info(f"Buscando producto: {product_name_with_d}")
                
                product = Product.search([('name', '=', product_name_with_d)], limit=1)
                
                if product:
                    _logger.info(f"Producto encontrado: {product_name_with_d} (ID: {product.id})")
                    return product.id
                    
                # Si no existe, crear el producto
                try:
                    _logger.info(f"Intentando crear nuevo producto: {product_name_with_d} con precio {price_unit}")
                        
                    # Obtener company por defecto
                    company = request.env['res.company'].sudo().search([('id', '=', 1)], limit=1)
                    if not company:
                        company = request.env['res.company'].sudo().search([], limit=1)
                    
                    # Obtener la categoría por defecto o crear una
                    category = request.env['product.category'].sudo().search([('name', '=', 'Ecommerce')], limit=1)
                    if not category:
                        try:
                            category = request.env['product.category'].sudo().create({
                                'name': 'Ecommerce',
                                'parent_id': False,
                            })
                        except:
                            category = request.env['product.category'].sudo().search([], limit=1)
                    
                    # Obtener unidades de medida por defecto
                    uom = request.env.ref('uom.product_uom_unit', raise_if_not_found=False)
                    if not uom:
                        uom = request.env['uom.uom'].sudo().search([('category_id.name', '=', 'Unit')], limit=1)
                        if not uom:
                            uom = request.env['uom.uom'].sudo().search([], limit=1)
                    
                    new_product = Product.create({
                        'name': product_name_with_d,
                        'type': 'consu',  # Consumible
                        'available_in_pos': True,
                        'sale_ok': True,
                        'purchase_ok': True,
                        'company_id': company.id if company else False,
                        'default_code': product_name_with_d[:50],  # Limitar tamaño del código
                        'list_price': price_unit,  # Precio de venta según la orden
                        'standard_price': 0.0,  # Precio de costo inicial
                        'uom_id': uom.id if uom else 1,
                        'uom_po_id': uom.id if uom else 1,
                        'categ_id': category.id if category else 1,
                        'taxes_id': [(6, 0, [])],  # Sin impuestos por defecto
                        'supplier_taxes_id': [(6, 0, [])],  # Sin impuestos de proveedor
                    })
                    _logger.info(f"Producto creado exitosamente: {product_name_with_d} (ID: {new_product.id})")
                    return new_product.id
                    
                except Exception as e:
                    _logger.error(f"Error al crear producto {product_name_with_d}: {str(e)}")
                    # Si hay error en la creación, intentar rollback y buscar fallback
                    raise
                    
        except Exception as e:
            _logger.error(f"Error en savepoint al crear producto: {str(e)}")
            
            # Intentar buscar un producto existente como fallback
            try:
                Product = request.env['product.product'].sudo()
                
                # Buscar un producto genérico como fallback
                fallback_product = Product.search([('name', 'ilike', 'producto')], limit=1)
                if not fallback_product:
                    fallback_product = Product.search([('available_in_pos', '=', True)], limit=1)
                if not fallback_product:
                    fallback_product = Product.search([], limit=1)
                
                if fallback_product:
                    _logger.info(f"Usando producto de respaldo: {fallback_product.name} (ID: {fallback_product.id})")
                    return fallback_product.id
                
            except Exception as fallback_error:
                _logger.error(f"Error al buscar producto de respaldo: {str(fallback_error)}")
            
            return False

    def _get_product_image_url(self, product_id, size='1920'):
        """
        Genera la URL de la imagen del producto.
        
        Args:
            product_id: ID del producto
            size: Tamaño de la imagen ('1920', '1024', '512', '256', '128')
        
        Returns:
            str: URL completa de la imagen del producto
        """
        if not product_id:
            return None
            
        base_url = request.httprequest.host_url.rstrip('/')
        image_url = f"{base_url}/web/image/product.product/{product_id}/image_{size}"
        return image_url

    @http.route('/api/pos/order', type='http', auth='none', methods=['POST'], csrf=False)
    def create_pos_order(self):
        try:
            # Usar un savepoint principal para manejar toda la transacción
            with request.env.cr.savepoint():
                # Obtener datos JSON desde la petición HTTP
                order_data = json.loads(request.httprequest.data.decode('utf-8'))

                # Validar que existan líneas de pedido
                if 'lines' not in order_data or not order_data['lines']:
                    return json.dumps({"success": False, "error": "Debe proporcionar al menos una línea de pedido"})

                # Obtener el nombre del punto de venta si se proporciona
                pos_name = order_data.get('pos_name', 'ECommerce')
                if 'pos_name' in order_data:
                    pos_name = f"ECommerce {pos_name}"

                # Obtener o crear una sesión POS para el punto de venta indicado
                session_id = self._get_or_create_pos_session(pos_name)
                
                # Obtener o crear un cliente
                partner_id = self._get_or_create_partner(order_data.get('partner_id'))
            
            # Preparar las líneas de la orden y calcular totales automáticamente
            order_lines = []
            calculated_total = 0.0
            
            for line in order_data['lines']:
                qty = line.get('qty', 0.0)
                base_price_unit = line.get('price_unit', 0.0)
                discount = line.get('discount', 0.0)
                # Permite ambos campos para compatibilidad
                base_note = line.get('customer_note') or line.get('note', '')
                
                # Procesar extras si existen
                extras = line.get('extras', [])
                extras_price = 0.0
                extras_text = ""
                
                if extras:
                    extras_list = []
                    for extra in extras:
                        extra_name = extra.get('name', '')
                        extra_price = extra.get('price', 0.0)
                        
                        if extra_name:
                            if extra_price > 0:
                                extras_list.append(f"+ {extra_name} (+${extra_price:.2f})")
                                extras_price += extra_price
                            else:
                                extras_list.append(f"+ {extra_name}")
                    
                    if extras_list:
                        extras_text = "\nExtras: " + ", ".join(extras_list)
                
                # Calcular el precio unitario total (precio base + extras)
                total_price_unit = base_price_unit + extras_price
                
                # Combinar nota base con extras
                final_note = base_note + extras_text
                
                # Obtener o crear el producto, pasando el precio base
                product_id = self._get_or_create_product(line.get('product_name', ''), base_price_unit)
                if not product_id:
                    return json.dumps({"success": False, "error": f"No se pudo crear/obtener el producto: {line.get('product_name', '')}"})
                
                # Calcular price_subtotal con el precio total (incluyendo extras)
                price_subtotal = qty * total_price_unit * (1 - discount / 100.0)
                
                # Sumar al total calculado
                calculated_total += price_subtotal
                
                order_lines.append((0, 0, {
                    'product_id': product_id,
                    'qty': qty,
                    'price_unit': total_price_unit,  # Precio unitario incluyendo extras
                    'discount': discount,
                    'price_subtotal': price_subtotal,
                    'price_subtotal_incl': price_subtotal,  # También podría incluir impuestos si es necesario
                    'customer_note': final_note,  # Nota que incluye extras
                }))
            
            # Usar el total calculado automáticamente
            amount_total = calculated_total
            amount_tax = order_data.get('amount_tax', 0.0)
            amount_paid = order_data.get('amount_paid', amount_total)  # Si no se especifica, usar el total
            amount_return = order_data.get('amount_return', max(0.0, amount_paid - amount_total))
                    
            # Crear la orden POS con manejo robusto de errores
            order = request.env['pos.order'].sudo().create({
                'partner_id': partner_id,
                'lines': order_lines,
                'session_id': session_id,
                'amount_paid': amount_paid,
                'amount_total': amount_total,
                'amount_tax': amount_tax,
                'amount_return': amount_return,
                'pricelist_id': order_data.get('pricelist_id'),
            })

            # Forzar la actualización de la orden para obtener la referencia
            order._compute_pos_reference() if hasattr(order, '_compute_pos_reference') else None
            
            # Verificar el punto de venta usado
            session = request.env['pos.session'].sudo().browse(session_id)
            config_name = session.config_id.name if session.exists() else "Desconocido"

            # Obtener la referencia de la orden de manera segura
            pos_reference = order.pos_reference if order.pos_reference else f"ORD-{order.id}"

            response = {
                "success": True,
                "order_id": order.id,
                "pos_reference": pos_reference,
                "session_id": session_id,
                "partner_id": partner_id,
                "pos_name": config_name,
                "calculated_totals": {
                    "amount_total": amount_total,
                    "amount_paid": amount_paid,
                    "amount_tax": amount_tax,
                    "amount_return": amount_return
                }
            }
            
            # Enviar notificación de nueva orden de ecommerce con múltiples fallbacks
            notification_sent = False
            notification_count = 0
            
            # Intento 1: Notificación a TODOS los usuarios POS (estrategia agresiva)
            try:
                notification_count = request.env['pos.order'].send_notification_to_all_pos_users(response)
                if notification_count > 0:
                    notification_sent = True
                    _logger.info(f"Notificación masiva enviada a {notification_count} usuarios para la orden {pos_reference}")
            except Exception as e:
                _logger.warning(f"Error en notificación masiva a usuarios POS: {str(e)}")
            
            # Intento 2: Notificación completa con grupos específicos (fallback)
            if not notification_sent:
                try:
                    request.env['pos.order'].send_ecommerce_notification(response)
                    notification_sent = True
                    _logger.info(f"Notificación por grupos enviada para la orden {pos_reference}")
                except Exception as e:
                    _logger.warning(f"Error en notificación por grupos: {str(e)}")
            
            # Intento 3: Notificación por mensaje en la orden (último recurso)
            if not notification_sent:
                try:
                    request.env['pos.order'].send_message_notification(response)
                    notification_sent = True
                    _logger.info(f"Notificación por mensaje enviada para la orden {pos_reference}")
                except Exception as e:
                    _logger.warning(f"Error en notificación por mensaje: {str(e)}")
            
            # Intento 3: Notificación simple por logs
            if not notification_sent:
                try:
                    request.env['pos.order'].send_simple_notification(response)
                    notification_sent = True
                    _logger.info(f"Notificación simple enviada para la orden {pos_reference}")
                except Exception as e:
                    _logger.error(f"Error en notificación simple: {str(e)}")
            
            if not notification_sent:
                _logger.error("No se pudo enviar ningún tipo de notificación")
            
            return json.dumps(response)

        except Exception as e:
            _logger.error(f"Error general en crear orden POS: {str(e)}")
            
            # En caso de error, intentar crear orden con datos mínimos como fallback
            try:
                _logger.info("Intentando crear orden con datos mínimos como fallback")
                
                # Usar datos básicos para el fallback
                fallback_session_id = 1  # Sesión fija de respaldo
                fallback_partner_id = 1  # Cliente fijo de respaldo
                
                # Buscar un producto cualquiera para el fallback
                fallback_product = request.env['product.product'].sudo().search([
                    ('available_in_pos', '=', True)
                ], limit=1)
                
                if not fallback_product:
                    fallback_product = request.env['product.product'].sudo().search([], limit=1)
                
                if fallback_product:
                    fallback_order = request.env['pos.order'].sudo().create({
                        'partner_id': fallback_partner_id,
                        'session_id': fallback_session_id,
                        'amount_paid': 0.0,
                        'amount_total': 0.0,
                        'amount_tax': 0.0,
                        'amount_return': 0.0,
                        'lines': [(0, 0, {
                            'product_id': fallback_product.id,
                            'qty': 1,
                            'price_unit': 0.0,
                            'discount': 0.0,
                            'price_subtotal': 0.0,
                            'price_subtotal_incl': 0.0,
                            'customer_note': f"Orden de emergencia - Error original: {str(e)[:100]}",
                        })]
                    })
                    
                    return json.dumps({
                        "success": True,
                        "order_id": fallback_order.id,
                        "pos_reference": f"ORD-FALLBACK-{fallback_order.id}",
                        "session_id": fallback_session_id,
                        "partner_id": fallback_partner_id,
                        "pos_name": "Fallback",
                        "warning": "Orden creada con datos de respaldo debido a errores en la creación normal",
                        "original_error": str(e)
                    })
                
            except Exception as fallback_error:
                _logger.error(f"Error crítico en fallback: {str(fallback_error)}")
            
            return json.dumps({"success": False, "error": str(e)})

    @http.route('/api/pos/get_product_by_name', type='http', auth='none', methods=['GET'], csrf=False)
    def get_product_by_name(self):
        try:
            product_name = request.httprequest.args.get('product_name') + " D"
            image_size = request.httprequest.args.get('image_size', '1920')  # Tamaño por defecto
            
            if not product_name:
                return json.dumps({"success": False, "error": "Debe proporcionar un nombre de producto"})

            # No necesitamos agregar " D" aquí ya que el producto ya debería tenerlo
            product = request.env['product.product'].sudo().search([('name', '=', product_name)], limit=1)

            if not product:
                return json.dumps({"success": False, "error": "No se encontró el producto"})

            # Obtener la URL de la imagen del producto con el tamaño especificado
            image_url = self._get_product_image_url(product.id, image_size)

            return json.dumps({
                "success": True, 
                "product_id": product.id,
                "name": product.name,
                "list_price": product.list_price,
                "image_url": image_url
            })
        except Exception as e:
            _logger.error(f"Error al buscar producto: {str(e)}")
            return json.dumps({"success": False, "error": str(e)})

    @http.route('/api/pos/get_or_create_product', type='http', auth='none', methods=['GET', 'POST'], csrf=False)
    def get_or_create_product_http(self):
        try:
            if request.httprequest.method == 'POST':
                data = json.loads(request.httprequest.data.decode('utf-8'))
                product_name = data.get('product_name')
                price_unit = data.get('price_unit', 0.0)
                image_size = data.get('image_size', '1920')  # Tamaño por defecto
            else:
                product_name = request.httprequest.args.get('product_name')
                price_unit = request.httprequest.args.get('price_unit', 0.0)
                image_size = request.httprequest.args.get('image_size', '1920')  # Tamaño por defecto
                try:
                    price_unit = float(price_unit)
                except Exception:
                    price_unit = 0.0

            if not product_name:
                return json.dumps({"success": False, "error": "Debe proporcionar un nombre de producto"})

            product_id = self._get_or_create_product(product_name, price_unit)
            if not product_id:
                return json.dumps({"success": False, "error": f"No se pudo crear/obtener el producto: {product_name}"})

            product = request.env['product.product'].sudo().browse(product_id)
            
            # Obtener la URL de la imagen del producto con el tamaño especificado
            image_url = self._get_product_image_url(product.id, image_size)
            
            return json.dumps({
                "success": True,
                "product_id": product.id,
                "name": product.name,
                "list_price": product.list_price,
                "image_url": image_url
            })
        except Exception as e:
            _logger.error(f"Error en get_or_create_product_http: {str(e)}")
            return json.dumps({"success": False, "error": str(e)})

    @http.route('/api/pos/debug/users', type='http', auth='none', methods=['GET'], csrf=False)
    def debug_notification_users(self):
        """
        Endpoint para debugging: obtiene información sobre usuarios y grupos disponibles
        """
        try:
            # Obtener información de grupos
            group_info = request.env['pos.order'].get_notification_groups_info()
            
            # Obtener todos los usuarios internos
            all_users = request.env['res.users'].search([
                ('active', '=', True),
                ('share', '=', False)
            ])
            
            users_info = []
            for user in all_users:
                user_groups = user.groups_id.mapped('name')
                users_info.append({
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'active': user.active,
                    'share': user.share,
                    'groups': user_groups
                })
            
            response = {
                "success": True,
                "total_internal_users": len(all_users),
                "users": users_info,
                "groups_info": group_info,
                "timestamp": str(request.env['ir.fields'].datetime.now())
            }
            
            _logger.info(f"Debug info: {len(all_users)} usuarios internos encontrados")
            return json.dumps(response, indent=2, ensure_ascii=False)
            
        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Error getting debug info: {str(e)}"
            }
            _logger.error(f"Error in debug_notification_users: {str(e)}")
            return json.dumps(error_response)
    
    @http.route('/api/pos/test-notification', type='http', auth='none', methods=['POST'], csrf=False)
    def test_notification_to_all_users(self):
        """
        Endpoint de prueba para enviar notificación a todos los usuarios
        """
        try:
            test_data = {
                'order_id': 99999,
                'pos_reference': 'TEST-NOTIFICATION',
                'partner_id': 1,
                'pos_name': 'Test Store',
                'calculated_totals': {
                    'amount_total': 25.50
                }
            }
            
            notification_count = request.env['pos.order'].send_notification_to_all_pos_users(test_data)
            
            response = {
                "success": True,
                "notifications_sent": notification_count,
                "message": f"Notificación de prueba enviada a {notification_count} usuarios",
                "timestamp": str(request.env['ir.fields'].datetime.now())
            }
            
            _logger.info(f"Notificación de prueba enviada a {notification_count} usuarios")
            return json.dumps(response, indent=2)
            
        except Exception as e:
            error_response = {
                "success": False,
                "error": f"Error sending test notification: {str(e)}"
            }
            _logger.error(f"Error in test_notification_to_all_users: {str(e)}")
            return json.dumps(error_response)