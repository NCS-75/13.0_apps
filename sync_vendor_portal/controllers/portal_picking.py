# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from collections import OrderedDict
from operator import itemgetter
from odoo.tools.float_utils import float_is_zero
from odoo import http, tools
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.tools import image_process, groupby as groupbyelem
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.addons.web.controllers.main import Binary


class ShipingPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(ShipingPortal, self)._prepare_portal_layout_values()
        domain = []
        partner = request.env.user.partner_id
        if request.env.user.has_group('base.group_portal'):
            domain += [('partner_id', '=', partner.id)]
        values['shiping_count'] = request.env['stock.picking'].search_count(domain)
        return values

    def _shiping_get_page_view_values(self, order, access_token, **kwargs):
        def resize_to_48(b64source):
            if not b64source:
                b64source = base64.b64encode(Binary().placeholder())
            return image_process(b64source, size=(48, 48))
        res_users = request.env['res.users'].sudo().search([('groups_id', 'in', request.env.ref('stock.group_stock_user').id)])
        values = {
            'shiping_order': order,
            'page_name': 'shiping',
            'resize_to_48': resize_to_48,
            'res_users': res_users,
        }
        return self._get_page_view_values(order, access_token, values, 'shiping_history', True, **kwargs)

    @http.route(['/my/shiping', '/my/shipings/<int:order_id>', '/my/shiping/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_shiping(self, page=1, sortby=None, order_id=None, groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        ShipingOrder = request.env['stock.picking']

        domain = []
        if order_id:
             domain = [('purchase_id', '=', int(order_id))]
        if request.env.user.has_group('base.group_portal'):
            domain += [('partner_id', '=', partner.id)]
        archive_groups = self._get_archive_groups('stock.picking', domain)

        searchbar_sortings = {
            'scheduled_date': {'label': _('Date'), 'order': 'scheduled_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'state': {'label': _('Status'), 'order': 'state desc, id desc'},
        }
        # default sort by value
        if not sortby:
            sortby = 'scheduled_date'
        order = searchbar_sortings[sortby]['order']

        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'state': {'input': 'state', 'label': _('Status')},
        }

        # count for pager
        shiping_count = ShipingOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/shiping",
            total=shiping_count,
            page=page,
            step=self._items_per_page
        )
        grouped_shiping = []
        # search the purchase quotes to display, according to the pager data
        orders = ShipingOrder.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['shiping_history'] = orders.ids[:100]
        grouped_shiping = [orders]
        if groupby == 'state':
            grouped_shiping = [ShipingOrder.concat(*g) for k, g in groupbyelem(orders, itemgetter('state'))]

        values.update({
            'orders': orders,
            'page_name': 'shiping',
            'pager': pager,
            'archive_groups': archive_groups,
            'groupby': groupby,
            'grouped_shiping': grouped_shiping,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'searchbar_sortings': OrderedDict(sorted(searchbar_sortings.items())),
            'default_url': '/my/shiping',
        })
        return request.render("sync_vendor_portal.portal_my_shiping", values)

    @http.route(['/my/shipings/packages/', '/my/shipings/packages/<int:order_id>', '/my/shipings/packages/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_package(self, page=1, sortby=None, order_id=None, groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        Package_obj = request.env['stock.quant.package']
        move_line = order_id and  request.env['stock.picking'].sudo().browse(int(order_id)) or False
        domain = []
        if move_line:
             domain = [('id', 'in', move_line.package_level_ids.mapped('package_id').ids)]
        # count for pager
        package_count = Package_obj.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/shipings/packages",
            total=package_count,
            page=page,
            step=self._items_per_page
        )
        # search the purchase quotes to display, according to the pager data
        orders = Package_obj.search(
            domain,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['package_history'] = orders.ids[:100]
        # grouped_package = [orders]
        # if groupby == 'state':
        #     grouped_shiping = [Package_obj.concat(*g) for k, g in groupbyelem(orders, itemgetter('state'))]

        values.update({
            'orders': orders,
            'page_name': 'packages',
            'pager': pager,
            'default_url': '/my/shipings/packages',
        })
        return request.render("sync_vendor_portal.portal_my_packages", values)

    @http.route(['/my/package/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_package_render(self, order_id=None, error=False, access_token=None, **kw):
        try:
            order_sudo = request.env['stock.quant.package'].sudo().browse(order_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = {'package_id': order_sudo, 'page_name': 'packages',}
        if error:
            values.update({'error': error})
        return request.render("sync_vendor_portal.portal_my_package_view", values)

    @http.route(['/my/shiping/update'], type='http', auth="user", website=True)
    def portal_my_shiping_update(self, access_token=None, **kw):
        name = self.slicedict(kw, 'rec_')
        try:
            order_sudo = self._document_check_access('stock.picking', int(kw.get('order_id')), access_token=access_token)
            for item in name.keys():
                move_line = self._document_check_access('stock.move', int(kw.get(item)), access_token=access_token)
                if move_line.product_id.tracking not in ['serial', 'lot']:
                    move_line.sudo().write({
                        'product_uom_qty': float(kw.pop('product_uom_qty_{}'.format(kw.get(item)))),
                        'quantity_done': float(kw.pop('quantity_done_{}'.format(kw.get(item))))
                    })
            if kw.get('note'):
                order_sudo.sudo().write({'note': kw.get('note')})
            if kw.get('priority'):
                order_sudo.sudo().write({'priority': kw.get('priority')})
            return request.redirect('/my/shiping/%s' % order_sudo.id)
        except Exception as e:
            return request.redirect('/my/shiping/%s?error=%s' % (order_sudo.id, tools.ustr(e)))

    @http.route(['/my/shiping/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_shiping_order(self, order_id=None, error=False, access_token=None, **kw):
        try:
            self._document_check_access('stock.picking', int(order_id), access_token=access_token)
            order_sudo = request.env['stock.picking'].sudo().browse(order_id)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = self._shiping_get_page_view_values(order_sudo, access_token, **kw)
        if error:
            values.update({'error': error})
        return request.render("sync_vendor_portal.portal_my_shiping_order", values)

    @http.route(['/my/shiping/print/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_shiping_print(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('stock.picking', int(order_id), access_token=access_token)
            if order_sudo.state in ['assigned', 'partially_available']:
                return self._show_report(model=order_sudo, report_type='pdf', report_ref='stock.action_report_delivery', download=False)
            else:
                return self._show_report(model=order_sudo, report_type='pdf', report_ref='stock.action_report_delivery', download=False)
        except Exception as e:
            return request.redirect('/my/shiping/%s?error=%s' % (order_sudo.id, tools.ustr(e)))

    @http.route(['/my/package/print/<int:package_id>'], type='http', auth="user", website=True)
    def portal_my_package_print(self, package_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('stock.quant.package', int(package_id), access_token=access_token)
            return self._show_report(model=order_sudo, report_type='pdf', report_ref='stock.action_report_quant_package_barcode', download=False)
        except Exception as e:
            return request.redirect('/my/package/%s?error=%s' % (order_sudo.id, tools.ustr(e)))

    @http.route(['/my/picking/print/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_picking_print(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('stock.picking', int(order_id), access_token=access_token)
            return self._show_report(model=order_sudo, report_type='pdf', report_ref='stock.action_report_picking', download=False)
        except Exception as e:
            return request.redirect('/my/shiping/%s?error=%s' % (order_sudo.id, tools.ustr(e)))


    @http.route(['/my/shiping/cancel/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_shiping_cancel(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('stock.picking', int(order_id), access_token=access_token)
            order_sudo.action_cancel()
            return request.redirect('/my/shiping/%s' % order_sudo.id)
        except Exception as e:
            return request.redirect('/my/shiping/%s?error=%s' % (order_sudo.id, tools.ustr(e)))

    @http.route(['/my/shiping/unlock/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_shiping_unlock(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('stock.picking', int(order_id), access_token=access_token)
            order_sudo.action_toggle_is_locked()
            return request.redirect('/my/shiping/%s' % order_sudo.id)
        except Exception as e:
            return request.redirect('/my/shiping/%s?error=%s' % (order_sudo.id, tools.ustr(e)))

    @http.route(['/my/shiping/put/into_pack/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_shiping_put_into_pack(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('stock.picking', int(order_id), access_token=access_token)
            order_sudo.put_in_pack()
            return request.redirect('/my/shiping/%s' % order_sudo.id)
        except Exception as e:
            return request.redirect('/my/shiping/%s?error=%s' % (order_sudo.id, tools.ustr(e)))

    @http.route(['/my/shiping/immediate/validate/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_shiping_immediate_validate(self, order_id=None, **kw):
        try:
            view = request.env.ref('stock.view_immediate_transfer')
            order_sudo = self._document_check_access('stock.picking', int(order_id), access_token=False)
            wiz = request.env['stock.immediate.transfer'].sudo().create({'pick_ids': [(4, order_sudo.id)]})
            wiz.process()
            return request.redirect('/my/shiping/%s'%order_sudo.id)
        except Exception as e:
            return request.redirect('/my/shiping/%s?error=%s' % (order_sudo.id, tools.ustr(e)))

    @http.route(['/my/shiping/initial/validate/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_shiping_initial_validate(self, order_id=None, **kw):
        try:
            view = request.env.ref('stock.view_immediate_transfer')
            order_sudo = self._document_check_access('stock.picking', int(order_id), access_token=False)
            wiz = request.env['stock.overprocessed.transfer'].sudo().create({'picking_id': order_sudo.id})
            wiz.action_confirm()
            return request.redirect('/my/shiping/%s'%order_sudo.id)
        except Exception as e:
            return request.redirect('/my/shiping/%s?error=%s' % (order_sudo.id, tools.ustr(e)))

    @http.route(['/my/shiping/backorder/validate/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_shiping_backorder_validate(self, order_id=None, **kw):
        try:
            view = request.env.ref('stock.view_immediate_transfer')
            order_sudo = self._document_check_access('stock.picking', int(order_id), access_token=False)
            wiz = request.env['stock.backorder.confirmation'].sudo().create({'pick_ids': [(4, order_sudo.id)]})
            wiz.process()
            return request.redirect('/my/shiping/%s'%order_sudo.id)
        except Exception as e:
            return request.redirect('/my/shiping/%s?error=%s' % (order_sudo.id, tools.ustr(e)))

    @http.route(['/my/shiping/nobackorder/validate/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_shiping_nobackorder_validate(self, order_id=None, **kw):
        try:
            view = request.env.ref('stock.view_immediate_transfer')
            order_sudo = self._document_check_access('stock.picking', int(order_id), access_token=False)
            wiz = request.env['stock.backorder.confirmation'].sudo().create({'pick_ids': [(4, order_sudo.id)]})
            wiz.process_cancel_backorder()
            return request.redirect('/my/shiping/%s'%order_sudo.id)
        except Exception as e:
            return request.redirect('/my/shiping/%s?error=%s' % (order_sudo.id, tools.ustr(e)))

    @http.route(['/my/shiping/validate'], type='json', auth="user", website=True)
    def portal_my_shiping_validate(self, order_id, **kw):
        try:
            precision_digits = request.env['decimal.precision'].precision_get('Product Unit of Measure')
            order_sudo = self._document_check_access('stock.picking', int(order_id), access_token=False)
            no_quantities_done = all(float_is_zero(move_line.qty_done, precision_digits=precision_digits) for move_line in order_sudo.move_line_ids.filtered(lambda m: m.state not in ('done', 'cancel')))
            no_reserved_quantities = all(float_is_zero(move_line.product_qty, precision_rounding=move_line.product_uom_id.rounding) for move_line in order_sudo.move_line_ids)
            html = request.env.ref("sync_vendor_portal.portal_immediate_transfer_form")
            if no_reserved_quantities and no_quantities_done:
                return {'html':html.render({
                        'move': order_sudo,
                        'type': 'qty_not_done',
                    })
                }
            elif no_quantities_done:
                return {'html':html.render({
                        'move': order_sudo,
                        'type': 'immediate',
                    })
                }
            # elif order_sudo._get_overprocessed_stock_moves() and not order_sudo._context.get('skip_overprocessed_check'):
            #     moves = order_sudo._get_overprocessed_stock_moves()
            #     overprocessed_product_name = moves[0].product_id.display_name
            #     return {'html':html.render({
            #             'move': order_sudo,
            #             'type': 'initially',
            #             'overprocessed_product_name': overprocessed_product_name,
            #         })
            #     }
            elif order_sudo._check_backorder():
                moves = order_sudo._get_overprocessed_stock_moves()
                return {'html':html.render({
                        'move': order_sudo,
                        'type': 'backorder',
                        'if_moves': moves or False,
                    })
                }
            else:
                order_sudo.button_validate()
            return request.redirect('/my/shiping/%s' % order_sudo.id)
        except (AccessError, MissingError):
            return request.redirect('/my')

    @http.route(['/my/shiping/confirm/<int:order_id>'], type='http', auth="user", website=True)
    def portal_my_shiping_confirm(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('stock.picking', int(order_id), access_token=access_token)
            order_sudo.action_confirm()
            return request.redirect('/my/shiping/%s' % order_sudo.id)
        except Exception as e:
            return request.redirect('/my/shiping/%s?error=%s' % (order_sudo.id, tools.ustr(e)))

    @http.route(['/detialed/operations'],type='json', auth='user', website=True)
    def detailed_operations(self, move_id, stock_id,**form_data):
        uom_ids = []
        if move_id:
            package_ids = request.env['stock.quant.package'].sudo().search_read([], ['id', 'name'])
            move = request.env['stock.move'].sudo().browse(int(move_id))
            if move and request.env.user.user_has_groups('uom.group_uom'):
                uom_ids = request.env['uom.uom'].search_read([('category_id', '=', move.product_id.uom_id.category_id.id)], ['id', 'name'])
            stock = request.env['stock.picking'].sudo().browse(int(stock_id))
            lot_ids = request.env['stock.production.lot'].sudo().search_read([('product_id', '=', move.product_id.id)], ['id', 'name'])
            location_ids = request.env['stock.location'].sudo().search_read([('id', 'child_of', stock.location_dest_id.ids)], ['id', 'name'])
            values = {'html': request.env['ir.ui.view'].with_context(lang=False).render_template('sync_vendor_portal.portal_detailed_operation_form',{
                    'move': move,
                    'package_ids': package_ids,
                    'location_ids': location_ids,
                    'uom_ids': uom_ids,
                    'lot_ids': lot_ids,
                    'is_uom': request.env.user.user_has_groups('uom.group_uom')}),
                    'move': move,
                    'package_ids': package_ids,
                    'location_ids': location_ids,
                    'is_serial_with_text': True and move.product_id.tracking in ['serial', 'lot'] and move.picking_type_id.use_create_lots or False,
                    'is_serial_with_selection': True and move.product_id.tracking in ['serial', 'lot'] and move.picking_type_id.use_existing_lots or False,
                    'is_uom': request.env.user.user_has_groups('uom.group_uom'),
                    'uom_name': move.product_uom.name or '',
                    'location_dest_name': move.location_dest_id.name or '',
                    'lot_ids': lot_ids}
            return values

    def slicedict(self, d, s):
        return {k: v for k, v in d.items() if k.startswith(s)}

    @http.route(['/create/detailed/operation'],type='http', auth='user', website=True)
    def create_detailed_operations(self, **form_data):
        #Work is remaining in this method for move line in stock move
        result_package_id = self.slicedict(form_data, 'result_package_id')
        operation_rec = []
        move = request.env['stock.move'].sudo().browse(int(form_data.get('move')))
        if move:
            if move.move_line_nosuggest_ids:
                move.write({'move_line_nosuggest_ids': [(3, f.id) for f in move.move_line_nosuggest_ids]})
            if move.move_line_ids:
                move.write({'move_line_ids': [(3, f.id) for f in move.move_line_ids]})
        for item in result_package_id.keys():
            operations_dic = {}
            rec = int(item.split('_')[3])
            if move and move.location_dest_id:
                operations_dic.update({'location_dest_id': move.location_dest_id.id})
            if form_data.get('result_package_id_{}'.format(rec)):
                operations_dic.update({'result_package_id': form_data.pop('result_package_id_{}'.format(rec))})
            if form_data.get('qty_done_{}'.format(rec)):
                operations_dic.update({'qty_done': form_data.pop('qty_done_{}'.format(rec))})
            if move.has_tracking in ['serial', 'lot'] and move.picking_type_id.use_create_lots:
                if form_data.get('lot_name_{}'.format(rec)):
                    operations_dic.update({'lot_name': form_data.pop('lot_name_{}'.format(rec))})
            if move.has_tracking in ['serial', 'lot'] and move.picking_type_id.use_existing_lots:
                if form_data.get('lot_id_{}'.format(rec)):
                    operations_dic.update({'lot_id': form_data.pop('lot_id_{}'.format(rec))})
            if move.product_uom:
                operations_dic.update({'product_uom_id': move.product_uom.id,
                    'location_id': move.location_id.id,
                    'product_id': move.product_id.id,
                    'picking_id': move.picking_id.id})
            if operations_dic:
                operation_rec.append(operations_dic)
        if operation_rec:
            if move.picking_type_id.show_reserved:
                move.write({'move_line_ids': [(0, 0, f) for f in operation_rec]})
            else:
                move.write({'move_line_nosuggest_ids': [(0, 0, f) for f in operation_rec]})
        return request.redirect('/my/shiping/%s' % move.picking_id.id)
