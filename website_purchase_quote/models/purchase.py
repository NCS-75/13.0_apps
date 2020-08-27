# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import uuid
from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from itertools import groupby


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _get_default_access_token(self):
        return str(uuid.uuid4())

    access_token = fields.Char('Security Token', copy=False, default=_get_default_access_token)
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)

    def _generate_access_token(self):
        for order in self:
            order.access_token = self._get_default_access_token()

    def order_lines_layouted(self):
        """
        Returns this order lines classified by purchase_layout_category and separated in
        pages according to the category pagebreaks. Used to render the report.
        """
        self.ensure_one()
        report_pages = [[]]
        for category, lines in groupby(self.order_line, lambda l: l.layout_category_id):
            # If last added category induced a pagebreak, this one will be on a new page
            if report_pages[-1] and report_pages[-1][-1]['pagebreak']:
                report_pages.append([])
            # Append category to current report page
            report_pages[-1].append({
                'name': category and category.name or _('Uncategorized'),
                'subtotal': category and category.subtotal,
                'pagebreak': category and category.pagebreak,
                'lines': list(lines)
            })

        return report_pages

    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to the online order for
        portal users or if force_website=True in the context. """
        # TDE note: read access on purchase order to portal users granted to followed purchase orders
        self.ensure_one()

        if self.state != 'cancel' and (self.state != 'draft' or self.env.context.get('mark_so_as_sent')):
            user, record = self.env.user, self
            if access_uid:
                user = self.env['res.users'].sudo().browse(access_uid)
                record = self.sudo(user)
            if user.share or self.env.context.get('force_website'):
                try:
                    record.check_access_rule('read')
                except AccessError:
                    if self.env.context.get('force_website'):
                        return {
                            'type': 'ir.actions.act_url',
                            'url': '/my/purchase_orders/%s' % self.id,
                            'target': 'self',
                            'res_id': self.id,
                        }
                    else:
                        pass
                else:
                    return {
                        'type': 'ir.actions.act_url',
                        'url': '/my/purchase_orders/%s?access_token=%s' % (self.id, self.access_token),
                        'target': 'self',
                        'res_id': self.id,
                    }
        return super(PurchaseOrder, self).get_access_action(access_uid)

    def get_mail_url(self):
        return self.get_share_url()

    def get_portal_confirmation_action(self):
        # return self.env['ir.config_parameter'].sudo().get_param('purchase.purchase_portal_confirmation_options', default='none')

        return self.env['ir.config_parameter'].sudo().get_param('website_purchase_quote.portal_po_confirmation_options', default='none')

    def action_cancel(self):
        return self.write({'state': 'cancel'})
