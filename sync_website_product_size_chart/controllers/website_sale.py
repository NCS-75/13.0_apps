# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class SalWebsiteSale(WebsiteSale):

    @http.route('/shop/get_product_dimension', type='json', auth='public', website=True)
    def get_product_dimension(self, product_dimension_id):
        return request.env['product.dimensions'].sudo().search_read(
                [('id', '=', product_dimension_id)],
                ['name', 'mode', 'html_content']
            )[0]