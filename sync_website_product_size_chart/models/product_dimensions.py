# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import fields, models


class ProductDimensions(models.Model):
    _name = "product.dimensions"
    _description = "Product Size Chart"

    def _default_html_content(self):
        return self.env['ir.ui.view'].render_template('sync_website_product_size_chart.dimensions_block')

    def _compute_products_count(self):
        for rec in self:
            rec.product_tmpl_count = len(rec.product_tmpl_ids)

    name = fields.Char(string="Name", copy=False, required=True)
    mode = fields.Selection([
        ('html', "HTML"),
        ('pdf', "PDF File"),
    ], string="Display", default="html")
    pdf_file = fields.Binary(string="PDF File", copy=False)
    html_content = fields.Html(string="Html Content", default=_default_html_content, translate=True, sanitize=False)
    product_tmpl_ids = fields.One2many(comodel_name='product.template',
        inverse_name='product_dimension_id', string="Products")
    product_tmpl_count = fields.Integer(string="Total Products",
        compute='_compute_products_count')

    def action_view_products(self):
        self.ensure_one()
        tree_view = self.env.ref('product.product_template_tree_view')
        form_view = self.env.ref('product.product_template_only_form_view')
        return {
            'name': 'Products',
            'domain': [('id', 'in', self.product_tmpl_ids.ids)],
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.template',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': True
        }
