# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'Repair Service - Vendor Portal',
    'version': '1.0',
    'category': 'Website',
    'author': 'Synconics Technologies Pvt. Ltd.',
    'summary': 'Allows to vendor can online confirm purchase order',
    'website': 'www.synconics.com',
    'description': """
Repair Service - Vendor Portal
==============================
* This application allows to vendor can online confirm purchase order.
""",
    'depends': ['purchase', 'website_mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/website_purchase_quote_data.xml',
        'data/mail_template_data.xml',
        'report/purchase_order_reports.xml',
        'report/purchase_order_templates.xml',
        'report/website_purchase_quote_templates.xml',
        'views/purchase_order_views.xml',
        'views/purchase_quote_views.xml',
        'views/res_config_settings_views.xml',
        'views/po_intro_template.xml',
        'views/website_quote_templates.xml',
        'menu.xml',
    ],
    'demo': [
        'data/website_purchase_quote_demo.xml'
    ],
    'images': ['static/description/main_screen.jpg'],
    'price': 70.0,
    'currency': 'EUR',
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
}