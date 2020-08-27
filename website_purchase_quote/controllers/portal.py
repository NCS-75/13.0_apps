# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import base64
from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal


class CustomerPortal(CustomerPortal):

    def _order_check_access_purchase(self, order_id, access_token=None):
        order = request.env['purchase.order'].sudo().browse([order_id])
        try:
            order.check_access_rights('read')
            order.check_access_rule('read')
        except AccessError:
            if not access_token or not consteq(order.access_token, access_token):
                raise
        return order

    @http.route(['/my/purchase_orders/<int:order>'], type='http', auth="public", website=True)
    def portal_porder_page(self, order=None, access_token=None, **kw):
        try:
            order_sudo = self._order_check_access_purchase(order, access_token=access_token)
        except AccessError:
            return request.redirect('/my')

        values = self._order_get_page_view_values(order_sudo, access_token, **kw)
        return request.render("purchase.portal_my_purchase_order", values)

    def _portal_pquote_user_can_accept(self, order_id):
        return request.env['ir.config_parameter'].sudo().get_param('website_purchase_quote.portal_po_confirmation_options', default=False) in ('sign')

    @http.route(['/my/purchase/<int:res_id>/accept'], type='json', auth="public", website=True)
    def portal_purchase_accept(self, res_id, access_token=None, partner_name=None, signature=None):
        if not signature:
            return {'error': _('Signature is missing.')}
        try:
            order_sudo = self._order_check_access_purchase(res_id, access_token=access_token)
        except AccessError:
            return {'error': _('Invalid order')}

        if not access_token:
            access_token = order_sudo.access_token

        if order_sudo.state != 'sent':
            return {'error': _('Order is not in a state requiring customer validation.')}

        order_sudo.button_confirm()
        _message_post_helper(
            res_model='purchase.order',
            res_id=order_sudo.id,
            message=_('Order signed by %s') % (partner_name,),
            attachments=[('signature.png', base64.b64decode(signature))] if signature else [],
            **({'token': access_token} if access_token else {}))
        return {
            'success': _('Your Order has been confirmed.'),
            'redirect_url': '/purchase/%s/%s' % (order_sudo.id, access_token),
        }
