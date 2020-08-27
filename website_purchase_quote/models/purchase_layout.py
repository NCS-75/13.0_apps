# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models


class PurchaseLayoutCategory(models.Model):
    _name = 'purchase.layout_category'
    _order = 'sequence, id'
    _description = 'PurchaseLayoutCategory'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', required=True, default=10)
    subtotal = fields.Boolean('Add subtotal', default=True)
    pagebreak = fields.Boolean('Add pagebreak')
