# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Vendor Portal (Portal Purchase)",
    'version': '1.0',
    'summary': """ Portal Vendor """,
    'description': """
    Portal purchase side
Portal Vendor
portal supplier
vendor portal
supplier portal
vendor purchase
purchase vendor
portal purchase
purchase portal
portal
supplier

    """,
    'category': 'Human Resources',
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'http://www.synconics.com',
    'depends': ['website_purchase_quote', 'portal', 'stock'],
    'data': [
        'security/purchase_security.xml',
        'security/ir.model.access.csv',
        'views/portal_purchase_list.xml',
        'views/portal_purchase_templates.xml',
        'views/portal_picking_menu.xml',
        'views/portal_picking_templates.xml',
        'views/detailed_operation.xml',
        'views/package_template.xml',
    ],
    'demo': [],
    'images': [
        'static/description/main_screen.png'
    ],
    'price': 50,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
}
