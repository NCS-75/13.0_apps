# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):

    _inherit = "product.template"

    product_dimension_id = fields.Many2one('product.dimensions', string="Dimensions")