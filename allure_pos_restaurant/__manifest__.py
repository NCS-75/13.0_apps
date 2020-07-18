# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Allure POS Restaurant',
    'category': "Themes/Backend",
    'version': '1.0',
    'license': 'OPL-1',
    'summary': '',
    'description': '',
    'author': 'Synconics Technologies Pvt. Ltd.',
    'depends': ['pos_restaurant','allure_pos_theme'],
    'website': 'www.synconics.com',
    'data': [
        'views/webclient_templates.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    # 'images': [
    #     'static/description/main_screen.png',
    #     'static/description/allure_screenshot.png',
    # ],
    'price': 599.0,
    'currency': 'EUR',
    'installable': True,
    'auto_install': False,
    'bootstrap': True,
    'application': True,
}
