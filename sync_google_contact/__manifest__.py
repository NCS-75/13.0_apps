# -*- coding: utf-8 -*-
# Part of Synconics. See LICENSE file for full copyright and licensing details.

{
    'name': 'Google Contact Synchronization',
    'version': '1.0',
    'summary': """Fetch Contacts from Google and create in odoo
                 Fetch Contacts from Odoo and create in google""",
    'sequence': 1,
    'description': """
Fetch Contacts from Google and create in odoo
Fetch Contacts from Odoo and create in google
    """,
    'category': "Tools",
    'author': 'Synconics Technologies Pvt. Ltd.',
    'website': 'http://www.synconics.com',
    'depends': ['google_account', 'contacts'],
    'external_dependencies': {
            'python': ['gdata', 'oauth2client']},
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/ir_cron.xml',
        'views/res_partner_views.xml',
        'views/config_settings_views.xml',
        'views/google_contacts_views.xml',
        'views/res_users_views.xml',
        'wizard/contact_share_wizard_view.xml',
    ],
    'demo': [],

    'images': [
        'static/description/main_screen.jpg'
    ],
    'price': 130.0,
    'currency': 'EUR',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
