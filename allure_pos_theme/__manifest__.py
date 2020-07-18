# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Allure POS Theme',
    'category': "Sales/Point Of Sale",
    'version': '1.0',
    'summary': 'Flexible, Powerful and Fully Responsive Customized POS Theme with many features in Community Edition.',
    'description': """ Flexible, Powerful and Fully Responsive Customized Backend Theme with many features(Tree, kanban and Barcode scan views of Products, Fuzzy search for product).

    allure pos theme
    POS Theme
    pos theme
    single screen
    single screen theme
    single theme
    """,
    'author': 'Synconics Technologies Pvt. Ltd.',
    'depends': ['point_of_sale'],
    'website': 'www.synconics.com',
    'data': [
        'data/theme_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/pos_config_view.xml',
        'views/webclient_templates.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    # 'images': [
    #     'static/description/main_screen.png',
    # ],
    'price': 189.0,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    'application': True,
    'bootstrap': True,
    'license': 'OPL-1',
}
