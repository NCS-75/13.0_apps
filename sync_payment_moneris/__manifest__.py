# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': 'Integration of Moneris Payment Acquirer with Odoo',
    'category': 'Accounting/Payment',
    'summary': 'Payment Acquirer: Moneris Implementation',
    'version': '1.0',
    'description': """
    Moneris Payment Acquirer
Moneris
Payment
Website
Acquirer
Payment Acquirer
Canada payment gateway integration
api integration
integration
    """,
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'https://www.synconics.com',
    'depends': ['sale_management', 'account_payment', 'website_sale'],
    'data': [
        'views/moneris.xml',
        'data/moneris.xml',
        'views/payment_acquirer.xml',
        'views/res_partner_view.xml',
    ],
    'demo': [],
    'images': [
        'static/description/main_screen.jpg'
    ],
    'price': 199.0,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'create_missing_journal_for_acquirers',
    'license': 'OPL-1',
}
