# -*- coding: utf-8 -*-
# Part of Synconics. See LICENSE file for full copyright and licensing details.

import odoo.http as http
import werkzeug
from odoo.http import request


class GoogleContactsAuthController(http.Controller):

    @http.route('/google/contacts/auth/<string:op>', website=True, type='http', auth="public")
    def google_contacts_auth(self, op, **kw):
        if op == "upload":
            request.env['google.contacts'].export_contacts()
        else:
            request.env['google.contacts'].import_contacts()
        google_contacts_menu = google_contacts_menu_action = False
        try:
            google_contacts_menu = request.env.ref('sync_google_contact.google_contacts_contacts_menu')
            google_contacts_menu_action = request.env.ref('sync_google_contact.google_contacts_contact_action')
        except:
            pass
        if google_contacts_menu and google_contacts_menu_action:
            return werkzeug.utils.redirect("/web?view_type=list&model=res.partner&menu_id=" + str(google_contacts_menu.id) + "&action=" + str(google_contacts_menu_action.id) + "#page=0&limit=80&view_type=list&model=res.partner&menu_id=" + str(google_contacts_menu.id) + "&action=" + str(google_contacts_menu_action.id) )
        return {}
