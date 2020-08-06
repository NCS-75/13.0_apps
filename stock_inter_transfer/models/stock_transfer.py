# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError


class StockTransfer(models.Model):
    _name = "stock.transfer"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _description = "Stock Transfer"

    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)

    @api.depends('picking_ids', 'picking_ids.state')
    def check_status(self):
        for rec in self:
            state = rec.state or 'pending'
            if rec.approval_required and rec.is_confirm:
                state = 'confirm'
            if rec.approval_required and rec.is_approved:
                state = 'approved'
            source_picking = rec.sudo().picking_ids.filtered(lambda l: l.state != 'cancel' and (l.picking_type_id.id == rec.picking_type_id.id))
            if rec.picking_ids and source_picking and source_picking[0].state == 'done':
                state = 'deliver_transit'
            dest_picking = rec.sudo().picking_ids.filtered(lambda l: l.state != 'cancel' and (l.location_dest_id.id == rec.location_dest_id.id))
            if rec.picking_ids and dest_picking and dest_picking[0].state == 'done':
                state = 'deliver_dest'
            if rec.is_cancel:
                state = 'cancel'
            rec.state = state

    name = fields.Char('Reference', default=lambda self: _('New'), copy=False,  index=True, readonly=True)
    is_confirm = fields.Boolean(string="Is Confirmed", default=False, copy=False)
    is_cancel = fields.Boolean(string="Is Cancelled", default=False, copy=False)
    picking_count = fields.Integer(compute='_compute_picking_count', string='Picking Count')
    partner_id = fields.Many2one('res.partner', 'Partner', track_visibility='onchange')
    location_id = fields.Many2one('stock.location', "Source Location", required=True, track_visibility='onchange')
    location_dest_id = fields.Many2one('stock.location', "Destination Location", required=True, track_visibility='onchange')
    transit_location_id = fields.Many2one('stock.location', "Transit Location", required=True, track_visibility='onchange')
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', required=True, track_visibility='onchange')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, index=True, required=True, track_visibility='onchange')
    state = fields.Selection(
        [('pending', 'Pending'), ('confirm', 'Waiting Approval'), ('approved', 'Approved'), ('cancel', 'Cancelled'), ('deliver_transit', 'Delivered to Trnasit Location'), ('deliver_dest', 'Delivered to Destination Location')],
        string="Status", compute="check_status", copy=False)
    note = fields.Text('Notes')
    transfer_lines = fields.One2many('stock.transfer.line', 'transfer_id', string="Lines")
    picking_ids = fields.One2many('stock.picking', 'transfer_id', string="Pickings")
    approval_required = fields.Boolean("Approval required")
    is_approved = fields.Boolean("Approved", default=False, help="Transfer Is Approved.", copy=False)
    user_id = fields.Many2one("res.users", string="Responsible", track_visibility='onchange',
                              default=lambda self: self.env.user, help="User responsible for this transfer.")

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Reference must be unique per company!'),
    ]

    @api.model
    def default_get(self, fields):
        res = super(StockTransfer, self).default_get(fields)
        default_approval_required = self.env['ir.config_parameter'].sudo().get_param('transfer_approval_required', False)
        res['approval_required'] = default_approval_required
        return res

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if 'company_id' in vals:
                vals['name'] = self.env['ir.sequence'].with_context(force_company=vals['company_id']).next_by_code('stock.transfer') or _('New')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.transfer') or _('New')
        res = super(StockTransfer, self.sudo()).create(vals)
        res.message_subscribe([res.partner_id.id])
        return res

    def write(self, vals):
        res = super(StockTransfer, self).write(vals)
        if self.partner_id.id not in self.message_partner_ids.ids:
            self.message_subscribe([self.partner_id.id])
        return res

    def unlink(self):
        for transfer in self:
            if transfer.picking_ids:
                raise UserError(_('You can not delete a transfer. You must first delete its internal transfers.'))
        return super(StockTransfer, self).unlink()

    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        if self.picking_type_id:
            self.location_id = self.picking_type_id.default_location_src_id.id
            self.location_dest_id = self.picking_type_id.default_location_dest_id.id

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.picking_type_id = False
        self.location_id = False
        self.location_dest_id = False
        self.transit_location_id = False


    def create_picking(self, location_id, location_dest_id, picking_type_id=False):
        Picking = self.env['stock.picking']
        Move = self.env['stock.move']
        if self.picking_type_id:
            picking_vals = {
                'origin': self.name,
                'partner_id': self.partner_id.id,
                'date_done': fields.Datetime.now(),
                'picking_type_id': picking_type_id.id,
                'company_id': self.company_id.id,
                'move_type': 'direct',
                'note': self.note or "",
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'transfer_id': self.id,
            }
            picking_id = Picking.create(picking_vals.copy())
        for line in self.transfer_lines.filtered(lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.product_uom_qty, precision_rounding=l.product_id.uom_id.rounding)):
            Move.create({
                'name': line.name,
                'product_uom': line.product_uom.id,
                'picking_id': picking_id.id,
                'picking_type_id': picking_type_id.id,
                'product_id': line.product_id.id,
                'product_uom_qty': abs(line.product_uom_qty),
                'state': 'draft',
                'location_id': location_id.id,
                'location_dest_id': location_dest_id.id,
                'company_id': self.company_id.id,
                'note': self.note,
            })
        return True

    def generate_transfer(self):
        if not self.transfer_lines:
            raise UserError(_('Please create operations.'))
        picking_type_id = self.picking_type_id
        self.sudo().create_picking(self.location_id, self.transit_location_id, picking_type_id=picking_type_id)
        warehouse = self.location_dest_id.sudo().get_warehouse()
        if warehouse:
            picking_type_id = warehouse[0].sudo().int_type_id
        self.sudo().create_picking(self.transit_location_id, self.location_dest_id, picking_type_id=picking_type_id)

    def action_view_pickings(self):
        pickings = self.mapped('picking_ids')
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif len(pickings) == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = pickings.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def action_approve(self):
        self.is_approved = True
        self.user_id = self.env.uid
        return True

    def action_confirm(self):
        if not self.transfer_lines:
            raise UserError(_('Please create operations.'))
        self.is_confirm = True

    def action_cancel(self):
        self.is_cancel = True


class StockTransferLine(models.Model):
    _name = "stock.transfer.line"
    _description = "Stock Transfer Lines"

    name = fields.Char('Description', index=True, required=True)
    product_id = fields.Many2one('product.product', string="Product", domain="[('type', 'in', ['product', 'consu'])]")
    transfer_id = fields.Many2one('stock.transfer', string="Transfer")
    product_uom_qty = fields.Float(string="Initial Demand", required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', 'Unit of Measure', required=True)

    _sql_constraints = [
        ('check_qty', 'CHECK(product_uom_qty > 0.0)', 'Initial Demand of product must be greater then 0.'),
    ]

    @api.constrains('product_uom')
    def _check_uom(self):
        transfer_error = self.filtered(lambda transfer: transfer.product_id.uom_id.category_id != transfer.product_uom.category_id)
        if transfer_error:
            user_warning = _('You cannot perform the transfer because the unit of measure has a different category as the product unit of measure.')
            for transfer in transfer_error:
                user_warning += _('\n\n%s --> Product UoM is %s (%s) - Transfer UoM is %s (%s)') % (transfer.product_id.display_name, transfer.product_id.uom_id.name, transfer.product_id.uom_id.category_id.name, transfer.product_uom.name, transfer.product_uom.category_id.name)
            user_warning += _('\n\nBlocking: %s') % ' ,'.join(transfer_error.mapped('name'))
            raise UserError(user_warning)

    @api.onchange('product_id')
    def onchange_product_id(self):
        product = self.product_id.with_context(lang=self.env.user.lang)
        self.name = product.partner_ref
        self.product_uom = product.uom_id.id
        return {'domain': {'product_uom': [('category_id', '=', product.uom_id.category_id.id)]}}
