# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.
{
    'name': 'Product Size Chart (eCommerce)',
    'version' : '1.0',
    'summary': 'Product Size Chart support with upload pdf on menage through Html',
    'sequence': 30,
    'description': """Product Size Chart support with upload pdf on menage through Html""",
    'category': 'eCommerce',
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'www.synconics.com',
    'depends': ['website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/assets_registary.xml',
        'views/product.xml',
        'views/product_dimensions_snippets.xml',
        'views/product_dimensions_views.xml',
        'views/product_template.xml',
    ],
    'images': [
        'static/description/main_screen.png',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'price': 49.0,
    'currency': 'EUR',
    'license': 'OPL-1',
    'installable': True,
    'application': True,
    'auto_install': False,
}