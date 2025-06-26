{
    "name": "POS Order API",
    "version": "18.0.1.0",
    "depends": ["point_of_sale", "base", "mail", "bus"],
    "summary": "API REST para registrar órdenes en el punto de venta con notificaciones",
    "category": "Point of Sale",
    "license": "LGPL-3",
    "installable": True,
    "application": False,
    "data": [
        "data/ir_config_parameter.xml",
        "data/res_users_data.xml",
        "data/ir_cron.xml",
    ],
    "post_init_hook": "post_init_hook",
}

