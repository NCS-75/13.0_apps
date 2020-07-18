# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = 'pos.config'

    default_view = fields.Selection([
        ('oe_kanban', 'Kanban'),
        ('oe_list', 'List'),
        ('oe_barcode', 'Barcode'),
    ], required=True, default='oe_kanban',
        help="Select default layout type")