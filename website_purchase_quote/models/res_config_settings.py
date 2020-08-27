# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    po_template_id = fields.Many2one('purchase.quote.template', default_model='purchase.order', string='Default Template', config_parameter="website_purchase_quote.po_template_id")
    module_website_purchase_quote = fields.Boolean("Quotations Templates", config_parameter="website_purchase_quote.module_website_purchase_quote")
    portal_po_confirmation = fields.Boolean('Online Signature', config_parameter="website_purchase_quote.portal_po_confirmation")
    portal_po_confirmation_options = fields.Selection([
        ('sign', 'Signature')], string="Online Signature", config_parameter="website_purchase_quote.portal_po_confirmation_options")

    @api.onchange('portal_po_confirmation')
    def _onchange_portal_po_confirmation(self):
        self.portal_po_confirmation_options = False
        if self.portal_po_confirmation:
            self.portal_po_confirmation_options = 'sign'
