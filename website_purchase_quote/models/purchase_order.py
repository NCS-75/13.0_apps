# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.tools.translate import html_translate
from odoo.addons import decimal_precision as dp
from time import gmtime, strftime
from werkzeug.urls import url_encode


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"
    _description = "Purchase Order Line"

    website_description = fields.Html('Line Description', sanitize=False, translate=html_translate)
    option_line_id = fields.One2many('purchase.order.option', 'line_id', 'Optional Products Lines')
    layout_category_id = fields.Many2one('purchase.layout_category', string='Section')
    customer_lead = fields.Float(
        'Delivery Lead Time', required=True, default=0.0,
        help="Number of days between the order confirmation and the shipping of the products to the customer", oldname="delay")
    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)

    @api.onchange('product_id')
    def onchange_product_id(self):
        domain = super(PurchaseOrderLine, self).onchange_product_id()
        if self.order_id.po_template_id:
            self.name = next((quote_line.name for quote_line in self.order_id.po_template_id.quote_line if
                             quote_line.product_id.id == self.product_id.id), self.name)
        return domain

    @api.model
    def _get_purchase_price(self, pricelist, product, product_uom, date):
        return {}

    @api.model
    def create(self, values):
        values = self._inject_quote_description(values)
        return super(PurchaseOrderLine, self).create(values)

    def write(self, values):
        values = self._inject_quote_description(values)
        return super(PurchaseOrderLine, self).write(values)

    def _inject_quote_description(self, values):
        values = dict(values or {})
        if not values.get('website_description') and values.get('product_id'):
            product = self.env['product.product'].browse(values['product_id'])
            values['website_description'] = product.quote_description or product.website_description
        return values


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _get_default_template(self):
        template = self.env.ref('website_purchase_quote.website_purchase_quote_template_default', raise_if_not_found=False)
        return template and template.active and template or False

    def _get_default_online_payment(self):
        default_template = self._get_default_template()
        if self.po_template_id:
            return self.po_template_id.require_payment
        elif default_template:
            return default_template.require_payment
        elif self.env['ir.config_parameter'].sudo().get_param('website_purchase_quote.portal_po_confirmation_options', default='none') == 'sign':
            return '0'
        else:
            return '0'

    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Pricelist for current purchase order.")
    po_template_id = fields.Many2one(
        'purchase.quote.template', 'Quotation Template',
        readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=_get_default_template)
    website_description = fields.Html('Description', sanitize_attributes=False, translate=html_translate)
    options = fields.One2many(
        'purchase.order.option', 'order_id', 'Optional Products Lines',
        copy=True, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    amount_undiscounted = fields.Float(
        'Amount Before Discount', compute='_compute_amount_undiscounted', digits=0)
    quote_viewed = fields.Boolean('Quotation Viewed')
    require_payment = fields.Selection([
        ('0', ' Online Signature')], default=_get_default_online_payment, string='Confirmation Mode',
        help="Choose how you want to confirm an order to launch the delivery process. You can either "
             "request a digital signature.")
    validity_date = fields.Date(string='Expiration Date', readonly=True, copy=False, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        help="Manually set the expiration date of your quotation (offer), or it will set the date automatically based on the template if online quotation is installed.")
    purchase_quote = fields.Many2one('purchase.quote.option', string="Purchase Quote")

    def print_report(self):
        data = []
        for rec in self:
            for record in rec.options:
                data1 = {
                    'product_id' : record.product_id.name,
                    'name': record.name,
                    'discount' : record.discount,
                    'price_unit' : record.price_unit,
                }
                data.append(data1)
        return data

    @api.model
    def _get_customer_lead(self, product_tmpl_id):
        return False

    def copy(self, default=None):
        if self.po_template_id and self.po_template_id.number_of_days > 0:
            default = dict(default or {})
            default['validity_date'] = fields.Date.to_string(datetime.now() + timedelta(self.po_template_id.number_of_days))
        return super(PurchaseOrder, self).copy(default=default)

    def _compute_amount_undiscounted(self):
        total = 0.0
        for line in self.order_line:
            total += line.price_subtotal + line.price_unit * ((line.discount or 0.0) / 100.0) * line.product_qty  # why is there a discount in a field named amount_undiscounted ??
        self.amount_undiscounted = total

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        super(PurchaseOrder, self).onchange_partner_id()
        self.notes = self.po_template_id.note or self.notes

    @api.onchange('partner_id')
    def onchange_update_description_lang(self):
        if not self.po_template_id:
            return
        else:
            template = self.po_template_id.with_context(lang=self.partner_id.lang)
            self.website_description = template.website_description

    @api.onchange('po_template_id')
    def onchange_po_template_id(self):
        if not self.po_template_id:
            return
        template = self.po_template_id.with_context(lang=self.partner_id.lang)

        order_lines = [(5, 0, 0)]
        for line in template.quote_line:
            discount = 0
            if self.pricelist_id:
                price = self.pricelist_id.with_context(uom=line.product_uom_id.id).get_product_price(line.product_id, 1, False)
                if self.pricelist_id.discount_policy == 'without_discount' and line.price_unit:
                    discount = (line.price_unit - price) / line.price_unit * 100
                    price = line.price_unit

            else:
                price = line.price_unit

            data = {
                'name': line.name,
                'price_unit': price,
                'discount': 100 - ((100 - discount) * (100 - line.discount)/100),
                'product_uom_qty': line.product_uom_qty,
                'product_id': line.product_id.id,
                'layout_category_id': line.layout_category_id,
                'product_uom': line.product_uom_id.id,
                'website_description': line.website_description,
                'state': 'draft',
                'customer_lead': self._get_customer_lead(line.product_id.product_tmpl_id),
                'date_planned': strftime("%Y-%m-%d %H:%M:%S", gmtime())
            }
            if self.pricelist_id:
                data.update(self.env['purchase.order.line']._get_purchase_price(self.pricelist_id, line.product_id, line.product_uom_id, fields.Date.context_today(self)))
            order_lines.append((0, 0, data))

        self.order_line = order_lines
        self.order_line._compute_tax_id()

        option_lines = []
        for option in template.options:
            if self.pricelist_id:
                price = self.pricelist_id.with_context(uom=option.uom_id.id).get_product_price(option.product_id, 1, False)
            else:
                price = option.price_unit
            data = {
                'product_id': option.product_id.id,
                'layout_category_id': option.layout_category_id,
                'name': option.name,
                'quantity': option.quantity,
                'uom_id': option.uom_id.id,
                'price_unit': price,
                'discount': option.discount,
                'website_description': option.website_description,
            }
            option_lines.append((0, 0, data))
        self.options = option_lines

        if template.number_of_days > 0:
            self.validity_date = fields.Date.to_string(datetime.now() + timedelta(template.number_of_days))

        self.website_description = template.website_description
        self.require_payment = template.require_payment

        if template.note:
            self.notes = template.note

    def open_quotation(self):
        self.ensure_one()
        self.write({'quote_viewed': True})
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/purchase/%s/%s' % (self.id, self.access_token)
        }

    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to the online quote if it exists. """
        self.ensure_one()
        user = access_uid and self.env['res.users'].sudo().browse(access_uid) or self.env.user

        if not self.po_template_id or (not user.share and not self.env.context.get('force_website')):
            return super(PurchaseOrder, self).get_access_action(access_uid)
        return {
            'type': 'ir.actions.act_url',
            'url': '/purchase/%s/%s' % (self.id, self.access_token),
            'target': 'self',
            'res_id': self.id,
        }

    def get_mail_url(self):
        self.ensure_one()
        if self.state not in ['purchase', 'done']:
            auth_param = url_encode(self.partner_id.signup_get_auth_param()[self.partner_id.id])
            return '/purchase/%s/%s?' % (self.id, self.access_token) + auth_param
        return super(PurchaseOrder, self).get_mail_url()

    def get_portal_confirmation_action(self):
        """ Template override default behavior of  sign chosen in purchase settings """
        if self.require_payment is not None or self.require_payment is not False:
            return 'sign' if self.require_payment == 0 else 'none'
        return super(PurchaseOrder, self).get_portal_confirmation_action()

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        for order in self:
            if order.po_template_id and order.po_template_id.mail_template_id:
                order.po_template_id.mail_template_id.send_mail(order.id)
        return res


class PurchaseOrderOption(models.Model):
    _name = "purchase.order.option"
    _description = "Purchase Options"
    _order = 'sequence, id'

    order_id = fields.Many2one('purchase.order', 'Purchase Order Reference', ondelete='cascade', index=True)
    line_id = fields.Many2one('purchase.order.line', on_delete="set null")
    name = fields.Text('Description', required=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('purchase_ok', '=', True)])
    layout_category_id = fields.Many2one('purchase.layout_category', string='Section')
    website_description = fields.Html('Line Description', sanitize_attributes=False, translate=html_translate)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'))
    discount = fields.Float('Discount (%)', digits=dp.get_precision('Discount'))
    uom_id = fields.Many2one('uom.uom', 'Unit of Measure ', required=True)
    quantity = fields.Float('Quantity', required=True, digits=dp.get_precision('Product UoS'), default=1)
    sequence = fields.Integer('Sequence', help="Gives the sequence order when displaying a list of suggested product.")

    @api.onchange('product_id', 'uom_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        product = self.product_id.with_context(lang=self.order_id.partner_id.lang)
        self.price_unit = product.list_price
        self.website_description = product.quote_description or product.website_description
        self.name = product.name
        if product.description_sale:
            self.name += '\n' + product.description_sale
        self.uom_id = self.uom_id or product.uom_id
        pricelist = self.order_id.pricelist_id
        if pricelist and product:
            partner_id = self.order_id.partner_id.id
            self.price_unit = pricelist.with_context(uom=self.uom_id.id).get_product_price(product, self.quantity, partner_id)
        domain = {'uom_id': [('category_id', '=', self.product_id.uom_id.category_id.id)]}
        return {'domain': domain}

    def button_add_to_order(self):
        self.ensure_one()
        order = self.order_id
        if order.state not in ['draft', 'sent']:
            return False

        order_line = order.order_line.filtered(lambda line: line.product_id == self.product_id)
        if order_line:
            order_line = order_line[0]
            order_line.product_uom_qty += 1
        else:
            date = ""
            for rec in self.order_id.order_line:
                date = rec.date_planned
            vals = {
                'price_unit': self.price_unit,
                'website_description': self.website_description,
                'name': self.name,
                'order_id': order.id,
                'product_id': self.product_id.id,
                'layout_category_id': self.layout_category_id.id,
                'product_uom': self.uom_id.id,
                'discount': self.discount,
                'product_qty' : self.quantity,
                'date_planned': date
            }
            order_line = self.env['purchase.order.line'].create(vals)
            order_line._compute_tax_id()

        self.write({'line_id': order_line.id})
        return {'type': 'ir.actions.client', 'tag': 'reload'}
