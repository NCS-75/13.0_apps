# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, models, _


class IrModelFields(models.Model):
    _inherit = "ir.model.fields"

    def unlink(self):
        # Prevent the deletion of the field "website_description"
        self = self.filtered(
            lambda rec: not (
                rec.model in ('product.product', 'product.template') and
                rec.name == 'website_description'
            )
        )
        return super(IrModelFields, self).unlink()
