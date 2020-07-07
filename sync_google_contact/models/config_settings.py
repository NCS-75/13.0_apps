# -*- coding: utf-8 -*-
# Part of Synconics. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):

    _inherit = "res.config.settings"

    def _default_google_contacts_authorization_code(self):
        authorization_code = self.env['ir.config_parameter'].get_param('google_contacts_authorization_code')
        return authorization_code

    def _default_google_contacts_client_id(self):
        google_contacts_client_id = self.env['ir.config_parameter'].get_param('google_contacts_client_id')
        return google_contacts_client_id

    def _default_google_contacts_client_secret(self):
        google_contacts_client_secret = self.env['ir.config_parameter'].get_param('google_contacts_client_secret')
        return google_contacts_client_secret

    @api.depends('google_contacts_client_id','google_contacts_client_secret')
    def _compute_google_contacts_uri(self):
        ir_config_param = self.env['ir.config_parameter']
        config = self
        client_id = config.google_contacts_client_id
        ir_config_param.set_param('google_contacts_client_id', client_id, groups=['base.group_system'])

        client_secret = config.google_contacts_client_secret
        ir_config_param.set_param('google_contacts_client_secret', client_secret, groups=['base.group_system'])

        uri = self.env['google.service']._get_google_token_uri('contacts', scope=self.env['google.contacts'].get_google_scope() )
        self.google_contacts_uri = uri

    google_contacts_client_id = fields.Char(string="Client ID", default=_default_google_contacts_client_id)
    google_contacts_client_secret = fields.Char(string="Client Secret", default=_default_google_contacts_client_secret)
    google_contacts_authorization_code = fields.Char(string="Authorization Code", default=_default_google_contacts_authorization_code)
    google_contacts_uri = fields.Char(string="Google Contacts URI", compute=_compute_google_contacts_uri)
    module_google_contacts = fields.Boolean(string="Google Contacts")

    @api.onchange('module_google_contacts')
    def onhange_module_google_contacts(self):
        if not self.module_google_contacts:
            self.google_contacts_client_secret = False
            self.google_contacts_client_id = False

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        res.update(module_google_contacts=ICPSudo.get_param('module_google_contacts'))
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        config = self.sudo()
        ICPSudo.set_param('module_google_contacts', config.module_google_contacts)
        client_secret = config.google_contacts_client_secret
        ICPSudo.set_param('google_contacts_client_secret', client_secret)
        client_id = config.google_contacts_client_id
        ICPSudo.set_param('google_contacts_client_id', client_id)
        auth_code = config.google_contacts_authorization_code
        if auth_code and auth_code != ICPSudo.get_param('google_contacts_authorization_code'):
            refresh_token = self.env['google.service'].generate_refresh_token('contacts', config.google_contacts_authorization_code)
            ICPSudo.set_param('google_contacts_authorization_code', auth_code)
            ICPSudo.set_param('google_contacts_refresh_token', refresh_token)
