# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import werkzeug
from odoo import exceptions, fields, http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, get_records_pager
from odoo.addons.portal.controllers.mail import _message_post_helper
from werkzeug.exceptions import NotFound


class CustomerPortal(CustomerPortal):

    @http.route()
    def portal_porder_page(self, order=None, access_token=None, **kw):
        try:
            order_sudo = self._order_check_access_purchase(order, access_token=access_token)
        except exceptions.AccessError:
            pass
        else:
            if order_sudo.po_template_id and order_sudo.po_template_id.active:
                return request.redirect('/purchase/%s/%s' % (order, access_token or ''))
        return super(CustomerPortal, self).portal_porder_page(order=order, access_token=access_token, **kw)

    def _portal_pquote_user_can_accept(self, order_id):
        result = super(CustomerPortal, self)._portal_pquote_user_can_accept(order_id)
        order_sudo = request.env['purchase.order'].sudo().browse(order_id)
        # either use quote template settings or fallback on default behavior
        return not order_sudo.require_payment if order_sudo.po_template_id else result


class PurchaseQuote(http.Controller):

    @http.route("/purchase/<int:order_id>", type='http', auth="user", website=True)
    def view_user(self, *args, **kwargs):
        return self.view(*args, **kwargs)

    @http.route("/purchase/<int:order_id>/<token>", type='http', auth="public", website=True)
    def view(self, order_id, pdf=None, token=None, message=False, **post):
        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        now = fields.Date.today()
        if token:
            order = request.env['purchase.order'].sudo().search([('id', '=', order_id), ('access_token', '=', token)], limit=1)
        else:
            order = request.env['purchase.order'].sudo().browse(int(order_id))
        # Log only once a day
        if order and request.session.get('view_quote_%s' % order.id) != now and request.env.user.share:
            request.session['view_quote_%s' % order.id] = now
            body = _('Quotation viewed by customer')
            _message_post_helper(res_model='purchase.order', res_id=order.id, message=body, token=token, message_type='notification', subtype="mail.mt_note", partner_ids=order.create_uid.sudo().partner_id.ids)
        if not order:
            raise NotFound()
        # Token or not, sudo the order, since portal user has not access on
        # taxes, required to compute the total_amout of SO.
        order_sudo = order.sudo()

        days = 0
        if order_sudo.validity_date:
            days = (fields.Date.from_string(order_sudo.validity_date) - fields.Date.from_string(fields.Date.today())).days + 1
        if pdf:
            pdf = request.env.ref('website_purchase_quote.report_web_purchase_quote').sudo().with_context(set_viewport_size=True).render_qweb_pdf([order_sudo.id])[0]#
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        values = {
            'quotation': order_sudo,
            'message': message and int(message) or False,
            'option': any(not x.line_id for x in order_sudo.options),
            'order_valid': (not order_sudo.validity_date) or (now <= order_sudo.validity_date),
            'days_valid': days,
            'action': request.env.ref('purchase.purchase_rfq').id,
            'no_breadcrumbs': request.env.user.partner_id.commercial_partner_id not in order_sudo.message_partner_ids,
            'token': token,
            'bootstrap_formatting': True,
            'partner_id': order_sudo.partner_id.id,
        }
        history = request.session.get('my_quotes_history', [])
        values.update(get_records_pager(history, order_sudo))
        return request.render('website_purchase_quote.purchase_quotation', values)

    @http.route(['/purchase/<int:order_id>/<token>/decline'], type='http', auth="public", methods=['POST'], website=True)
    def decline(self, order_id, token, **post):
        order = request.env['purchase.order'].sudo().browse(order_id)
        if token != order.access_token:
            raise NotFound()
        if order.state != 'sent':
            return werkzeug.utils.redirect("/purchase/%s/%s?message=4" % (order_id, token))
        order.action_cancel()
        message = post.get('decline_message')
        if message:
            _message_post_helper(message=message, res_id=order_id, res_model='purchase.order', **{'token': token} if token else {})
        return werkzeug.utils.redirect("/purchase/%s/%s?message=2" % (order_id, token))

    @http.route(['/purchase/update_line'], type='json', auth="public", website=True)
    def update(self, line_id, remove=False, unlink=False, order_id=None, token=None, **post):
        order = request.env['purchase.order'].sudo().browse(int(order_id))
        if token != order.access_token:
            raise NotFound()
        if order.state not in ('draft', 'sent'):
            return False
        order_line = request.env['purchase.order.line'].sudo().browse(int(line_id))
        if unlink:
            order_line.unlink()
            return False
        number = -1 if remove else 1
        quantity = order_line.product_uom_qty + number
        order_line.write({'product_uom_qty': quantity})
        return [str(quantity), str(order.amount_total)]

    @http.route(["/purchase/template/<model('purchase.quote.template'):quote>"], type='http', auth="user", website=True)
    def template_view(self, quote, **post):
        values = {'template': quote}
        return request.render('website_purchase_quote.purchase_quotation_template', values)

    # @http.route(["/purchase/add_line/<int:option_id>/<int:order_id>/<token>"], type='http', auth="public", website=True)
    # def add(self, option_id, order_id, token, **post):
    #     order = request.env['purchase.order'].sudo().browse(order_id)
    #     date = ''
    #     for rec in order.order_line:
    #         date = rec.date_planned
    #     if token != order.access_token:
    #         raise NotFound()
    #     if order.state not in ['draft', 'sent']:
    #         return request.render('website.http_error', {'status_code': 'Forbidden', 'status_message': _('You cannot add options to a confirmed order.')})
    #     option = request.env['purchase.order.option'].sudo().browse(option_id)
    #     vals = {
    #         'price_unit': option.price_unit,
    #         'website_description': option.website_description,
    #         'name': option.name,
    #         'order_id': order.id,
    #         'product_id': option.product_id.id,
    #         'layout_category_id': option.layout_category_id.id,
    #         'product_uom_qty': option.quantity,
    #         'product_uom': option.uom_id.id,
    #         'discount': option.discount,
    #         'product_qty' : option.quantity,
    #         'date_planned': date
    #     }

    #     order_line = request.env['purchase.order.line'].sudo().create(vals)
    #     order_line._compute_tax_id()
    #     option.write({'line_id': order_line.id})
    #     return werkzeug.utils.redirect("/purchase/%s/%s#pricing" % (order.id, token))
