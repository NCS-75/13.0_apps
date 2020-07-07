# -*- coding: utf-8 -*-
# Part of Synconics. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models,_


class ResUsersGoogleContacts(models.Model):
    _inherit = "res.users"

    google_contacts_rtoken = fields.Char(string="Refresh Token")
    google_contacts_token = fields.Char(string="User token")
    google_contacts_token_validity = fields.Datetime(string="Token Validity")
    google_contacts_model = fields.Char(string="Sync Model")
    google_contacts_last_sync_date = fields.Datetime(string="Last synchro date")
    google_contacts_cal_id = fields.Char(string="Calendar ID", help="Last Contact ID who has been synchronized. If it is changed, we remove all links between GoogleID and Odoo Google Internal ID")

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4: