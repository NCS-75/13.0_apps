# -*- coding: utf-8 -*-
# Part of Synconics. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class GoogleDetails(models.Model):
    _name = 'google.details'
    _description = 'Google Details'

    google_contacts_id = fields.Char(string="Google Contacts ID")
    google_contacts_account = fields.Char(string="Google Contacts Account")
    user_id = fields.Many2one('res.users', string='User')
    partner_id = fields.Many2one('res.partner', string="Partner", ondelete="cascade")


class ResPartnerGoogleContacts(models.Model):
    _inherit = "res.partner"

    user_ids = fields.Many2many('res.users', string='Users')
    google_contact_ids = fields.One2many('google.details', 'partner_id', string='Google Contact Detail')
    google_contact = fields.Boolean(string='Google Contact')
    home_phone = fields.Char(string='Home Phone')
    home_fax = fields.Char(string='Home Fax')
    fax = fields.Char(string='Work Fax')
    middle_name = fields.Char(string='Middle Name')
    last_name = fields.Char(string='Last Name')

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4: