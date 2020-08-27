# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import OrderedDict
from operator import itemgetter
from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.tools import image_process, groupby as groupbyelem
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.addons.web.controllers.main import Binary


class VendorPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        quotation_domain, order_domian = [('state', 'in', ['draft', 'cancel', 'to approve', 'sent'])], [('state', 'in', ['purchase', 'done'])]
        values = super(VendorPortal, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        if request.env.user.has_group('base.group_portal'):
            quotation_domain += [('partner_id', '=', partner.id)]
            order_domian += [('partner_id', '=', partner.id)]
        values['purchase_quote_count'] = request.env['purchase.order'].search_count(quotation_domain)
        values['purchase_count'] = request.env['purchase.order'].search_count(order_domian)
        return values

    def _purchase_quote_get_page_view_values(self, order, access_token, **kwargs):
        def resize_to_48(b64source):
            if not b64source:
                b64source = base64.b64encode(Binary().placeholder())
            return image_process(b64source, size=(48, 48))

        values = {
            'quote_order': order,
            'resize_to_48': resize_to_48,
        }
        if order.state in ['purchase', 'done']:
            values.update({'p_order': True})
            history = request.session.get('my_purchase_quote_history', [])
            return self._get_page_view_values(order, access_token, values, 'my_purchases_history', True, **kwargs)
        return self._get_page_view_values(order, access_token, values, 'my_purchase_quote_history', True, **kwargs)

    @http.route(['/my/purchase/quote', '/my/purchase/quote/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_quote_orders(self, page=1, sortby=None, filterby=None, groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PurchaseOrder = request.env['purchase.order']

        domain = [('state', 'in', ['draft', 'cancel', 'to approve', 'sent'])]

        if request.env.user.has_group('base.group_portal'):
            domain += [('partner_id', '=', partner.id)]

        archive_groups = self._get_archive_groups('purchase.order', domain)

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('state', 'in', ['draft', 'cancel', 'to approve', 'sent'])]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
            'draft': {'label': _('RFQ'), 'domain': [('state', '=', 'draft')]},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'state': {'input': 'state', 'label': _('Status')},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # count for pager
        purchase_quote_count = PurchaseOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/purchase/quote",
            total=purchase_quote_count,
            page=page,
            step=self._items_per_page
        )
        grouped_purchase = []
        # search the purchase quotes to display, according to the pager data
        orders = PurchaseOrder.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['my_purchase_quote_history'] = orders.ids[:100]
        grouped_purchase = [orders]
        if groupby == 'state':
            grouped_purchase = [PurchaseOrder.concat(*g) for k, g in groupbyelem(orders, itemgetter('state'))]

        values.update({
            'orders': orders,
            'page_name': 'purchase_quote',
            'pager': pager,
            'archive_groups': archive_groups,
            'groupby': groupby,
            'grouped_purchase': grouped_purchase,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': '/my/purchase/quote',
        })
        return request.render("sync_vendor_portal.portal_my_purchase_quote_orders", values)

    @http.route(['/my/purchase', '/my/purchase/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        PurchaseOrder = request.env['purchase.order']

        domain = []

        if request.env.user.has_group('base.group_portal'):
            domain += [('partner_id', '=', partner.id)]

        archive_groups = self._get_archive_groups('purchase.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'state': {'input': 'state', 'label': _('Status')},
        }

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('state', 'in', ['purchase', 'done'])]},
            'purchase': {'label': _('Purchase Order'), 'domain': [('state', '=', 'purchase')]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
            'done': {'label': _('Locked'), 'domain': [('state', '=', 'done')]},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # count for pager
        purchase_count = PurchaseOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/purchase",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=purchase_count,
            page=page,
            step=self._items_per_page
        )
        # search the purchase orders to display, according to the pager data
        orders = PurchaseOrder.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['my_purchases_history'] = orders.ids[:100]
        grouped_purchase = [orders]
        if groupby == 'state':
            grouped_purchase = [PurchaseOrder.concat(*g) for k, g in groupbyelem(orders, itemgetter('state'))]

        values.update({
            'date': date_begin,
            'orders': orders,
            'page_name': 'purchase',
            'pager': pager,
            'groupby': groupby,
            'grouped_purchase': grouped_purchase,
            'searchbar_groupby': searchbar_groupby,
            'archive_groups': archive_groups,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': '/my/purchase',
        })
        return request.render("sync_vendor_portal.portal_my_purchase_quote_orders", values)

    @http.route(['/my/purchase/qoute/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_purchase_qoute_order(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = self._purchase_quote_get_page_view_values(order_sudo, access_token, **kw)
        return request.render("sync_vendor_portal.portal_my_purchase_quote_order", values)

    @http.route(['/my/purchase/qoute/create_bill/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_purchase_qoute_create_bill(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
            order_sudo.with_context(create_bill=True).sudo().action_view_invoice()
            return request.redirect('/my/purchase/qoute/%s' % order_sudo.id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = self._purchase_quote_get_page_view_values(order_sudo, access_token, **kw)
        return request.render("sync_vendor_portal.portal_my_purchase_quote_order", values)

    def slicedict(self, d, s):
        return {k: v for k, v in d.items() if k.startswith(s)}

    @http.route(['/my/purchase/qoute/update'], type='http', auth="user", website=True)
    def portal_my_purchase_qoute_update(self, access_token=None, **kw):
        name = self.slicedict(kw, 'rec_')
        try:
            order_sudo = self._document_check_access('purchase.order', int(kw.get('order_id')), access_token=access_token)
            for item in name.keys():
                purchase_line = self._document_check_access('purchase.order.line', int(kw.get(item)), access_token=access_token)
                purchase_line.write({
                    'product_qty': float(kw.pop('product_qty_{}'.format(kw.get(item)))),
                    'price_unit': float(kw.pop('price_unit_{}'.format(kw.get(item))))
                    })
            if kw.get('notes'):
                order_sudo.write({'notes': kw.get('notes')})
            return request.redirect('/my/purchase/qoute/%s' % order_sudo.id)
        except (AccessError, MissingError):
            return request.redirect('/my')

    @http.route(['/my/purchase/qoute/confirm/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_purchase_qoute_confirm(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', int(order_id), access_token=access_token)
            order_sudo.button_confirm()
            return request.redirect('/my/purchase/qoute/%s' % order_sudo.id)
        except (AccessError, MissingError):
            return request.redirect('/my')

    @http.route(['/my/purchase/qoute/cancel/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_purchase_qoute_cancel(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', int(order_id), access_token=access_token)
            order_sudo.button_cancel()
            return request.redirect('/my/purchase/qoute/%s' % order_sudo.id)
        except (AccessError, MissingError):
            return request.redirect('/my')

    @http.route(['/my/vendor/bill/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_vendor_bill(self, order_id=None, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        order_id = request.env['purchase.order'].sudo().browse(int(order_id))
        AccountInvoice = request.env['account.move']

        domain = [('type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')), ('id', 'in', order_id.invoice_ids.ids)]

        searchbar_sortings = {
            'date': {'label': _('Invoice Date'), 'order': 'invoice_date desc'},
            'duedate': {'label': _('Due Date'), 'order': 'invoice_date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        # default sort by order
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('account.move', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        invoice_count = AccountInvoice.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/vendor/bill",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        invoices = AccountInvoice.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_invoices_history'] = invoices.ids[:100]

        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'invoice',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/vendor/bill',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("account.portal_my_invoices", values)

    @http.route(['/my/purchase/qoute/draft/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_purchase_qoute_draft(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', int(order_id), access_token=access_token)
            order_sudo.button_draft()
            return request.redirect('/my/purchase/qoute/%s' % order_sudo.id)
        except (AccessError, MissingError):
            return request.redirect('/my')

    @http.route(['/my/purchase/qoute/unlock/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_purchase_qoute_unlock(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', int(order_id), access_token=access_token)
            order_sudo.button_unlock()
            return request.redirect('/my/purchase/qoute/%s' % order_sudo.id)
        except (AccessError, MissingError):
            return request.redirect('/my')

    @http.route(['/my/purchase/qoute/lock/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_purchase_qoute_lock(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', int(order_id), access_token=access_token)
            order_sudo.button_done()
            return request.redirect('/my/purchase/qoute/%s' % order_sudo.id)
        except (AccessError, MissingError):
            return request.redirect('/my')

    @http.route(['/my/purchase/qoute/print/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_purchase_qoute_print(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', int(order_id), access_token=access_token)
            return self._show_report(model=order_sudo, report_type='pdf', report_ref='purchase.report_purchase_quotation', download=False)
        except (AccessError, MissingError):
            return request.redirect('/my')
