# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import logging

from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MonerisController(http.Controller):

    @http.route(['/payment/moneris/s2s/create'], type='json', auth='public', csrf=False)
    def moneris_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        token = False
        acquirer = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id')))
        try:
            if not kwargs.get('partner_id'):
                kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
            token = acquirer.s2s_process(kwargs)
        except ValidationError as e:
            message = e.args[0]
            if isinstance(message, dict) and 'missing_fields' in message:
                msg = _("The transaction cannot be processed because some contact details are missing or invalid: ")
                message = msg + ', '.join(message['missing_fields']) + '. '
                if request.env.user._is_public():
                    message += _("Please sign in to complete your profile.")
                    # update message if portal mode = b2b
                    if request.env['ir.config_parameter'].sudo().get_param('auth_signup.allow_uninvited', 'False').lower() == 'false':
                        message += _("If you don't have any account, please ask your salesperson to update your profile.")
                else:
                    message += _("Please complete your profile. ")

            return {
                'error': message
            }
        if not token:
            return {'result': False}
        res = {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
            '3d_secure': False,
            'verified': False,
        }
        if verify_validity != False:
            token.validate()
            res['verified'] = token.verified
        return res

    @http.route('/payment/moneris/validate', type='http', auth='public', csrf=False, website=True)
    def moneris_form_feedback(self, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction.
        """
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'moneris')
            return request.redirect("/payment/process")

    @http.route('/payment/moneris/cancel', type='http', auth='public', csrf=False, website=True)
    def moneris_payment_cancel(self, **post):
        tx = None
        if post and post.get('order_id'):
            tx = request.env['payment.transaction'].sudo().search([('reference', '=', post['order_id'])])
        if not tx:
            tx_id = (request.session.get('sale_transaction_id') or request.session.get('website_payment_tx_id'))
            if tx_id:
                tx = request.env['payment.transaction'].sudo().browse(literal_eval(tx_id))
        if tx:
            reference = tx.reference.split('-')
            if 'x' in tx.reference:
                reference = tx.reference.split('x')
            if reference:
                invoice = request.env['account.move'].sudo().search([('name', '=', reference[0])], limit=1)
            if not invoice:
                order_id = request.env['sale.order'].sudo().search([('name', '=', reference[0])], limit=1)
            if invoice:
                return request.redirect('/my/invoices/%s' % (invoice.id))
            elif order_id:
                return request.redirect("/shop/payment")
            _logger.info('Beginning Moneris cancel with post data %s' % (post))
        return request.redirect("/payment/process")
