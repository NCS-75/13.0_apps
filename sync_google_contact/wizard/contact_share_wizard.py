# -*- coding: utf-8 -*-
# Part of Synconics. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class ContactShare(models.TransientModel):
    _name = "contact.share.wizard"
    _description = "Share contact with users"

    user_ids = fields.Many2many('res.users', string='Users')

    def action_apply(self):
        if self.user_ids:
            for partner in self._context.get('active_ids', []):
                partner = self.env['res.partner'].browse(partner)
                if partner.user_ids:
                    user_ids = partner.user_ids.ids + self.user_ids.ids
                else:
                    user_ids = self.user_ids.ids
                partner.user_ids = [(6, 0, user_ids)]

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4: