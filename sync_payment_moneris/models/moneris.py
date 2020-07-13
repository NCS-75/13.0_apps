# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
from datetime import datetime
from . import moneris_vault
from . import moneris_payment

_logger = logging.getLogger(__name__)

declined_response_codes = ['050', '051', '052', '053', '054', '055', '056', '057', '058', '059', '060',
                           '061', '062', '063', '064', '065', '066', '067', '068', '069', '070',
                           '071', '072', '073', '074', '075', '076', '077', '078', '079', '080',
                           '081', '082', '083', '084', '085', '086', '087', '088', '089', '090',
                           '091', '092', '093', '094', '095', '096', '097', '098', '099']
referral_response_codes = ['100', '101', '102', '103', '104', '105', '106', '107', '108', '109', '110',
                           '111', '112', '113', '115', '121', '122']
system_error_response_codes = ['150', '200', '201', '202', '203', '204', '205', '206', '207', '208', '209', '210',
                               '212', '251', '252']
amex_response_codes_declines = ['426', '427', '429', '430', '431', '434', '435', '436', '437', '438', '439', '440',
                                '441']
credit_card_response_codes_declines = ['475', '476', '477', '478', '479', '480', '481', '482', '483', '484', '485',
                                       '486', '487', '489', '490']
system_decline_response_codes = ['800', '801', '802', '809', '810', '811', '821', '877', '878', '880', '881', '889',
                                 '898', '899', '900',
                                 '901', '902', '903', '904', '905', '906', '907', '908', '909']
vault_response_code = ['983', '986', '987', '988']

approve_response_code = ['000', '001', '002', '003', '004', '005', '006', '007', '008', '009', '023',
                         '024', '025', '026', '027', '028', '029']


class AcquirerMoneris(models.Model):
    _inherit = 'payment.acquirer'

    def _get_moneris_urls(self, environment):
        """ Moneris URLS """
        if environment == 'prod':
            return {
                'moneris_form_url': 'https://www3.moneris.com/HPPDP/index.php',
                'moneris_auth_url': 'https://www3.moneris.com/HPPDP/verifyTxn.php',
                'moneris_request_url': 'https://www3.moneris.com/gateway2/servlet/MpgRequest'
            }
        else:
            return {
                'moneris_form_url': 'https://esqa.moneris.com/HPPDP/index.php',
                'moneris_auth_url': 'https://esqa.moneris.com/HPPDP/verifyTxn.php',
                'moneris_request_url': 'https://esqa.moneris.com/gateway2/servlet/MpgRequest'
            }

    provider = fields.Selection(selection_add=[('moneris', 'Moneris')], help="Provider")
    moneris_email_account = fields.Char('PS Store ID', help="Moneris Production store ID")
    moneris_seller_account = fields.Char('HPP Key',
                                         help='The Merchant ID is used to ensure communications coming from Moneris '
                                              'are valid and secured.')
    store_id = fields.Char('Store ID')
    api_token = fields.Char('Api Token')

    @api.model
    def _create_missing_journal_for_acquirers(self, company=None):
        res = super(AcquirerMoneris, self)._create_missing_journal_for_acquirers(company=company)
        company = company or self.env.user.company_id
        acquirers = self.env['payment.acquirer'].search(
            [('provider', '=', 'moneris'), ('journal_id', '=', False), ('company_id', '=', company.id)])
        for acquirer in acquirers.filtered(lambda l: not l.journal_id and l.company_id.chart_template_id):
            acquirer.journal_id = self.env['account.journal'].create(acquirer._prepare_account_journal_vals())
            res += acquirer.journal_id
        return res

    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(AcquirerMoneris, self)._get_feature_support()
        res['authorize'].append('moneris')
        res['tokenize'].append('moneris')
        return res

    def _get_available_payment_input(self, partner=None, company=None):
        """ Generic (model) method that fetches available payment mechanisms
        to use in all portal / eshop pages that want to use the payment form.

        It contains

         * acquirers: record set of both form and s2s acquirers;
         * pms: record set of stored credit card data (aka payment.token)
                connected to a given partner to allow customers to reuse them """
        if not company:
            company = self.env.user.company_id
        if not partner:
            partner = self.env.user.partner_id
        active_acquirers = self.sudo().search([('state', 'in', ['enabled', 'test']), ('company_id', '=', company.id)])
        acquirers = active_acquirers.filtered(lambda acq: (acq.payment_flow == 'form' and acq.view_template_id) or
                                                          (acq.payment_flow == 's2s' and acq.registration_view_template_id))
        return {
            'acquirers': acquirers,
            'pms': self.env['payment.token'].search([
                ('partner_id', '=', partner.id),
                ('acquirer_id', 'in', acquirers.ids)]),
        }

    def moneris_form_generate_values(self, values):
        self.ensure_one()
        moneris_tx_values = dict(values)
        product_data = []
        tx_id = self.env['payment.transaction'].sudo().search([('reference', '=', values['reference'])])
        if tx_id and tx_id.invoice_ids:
            invoice_ids = tx_id.invoice_ids
            count = 1
            for line in invoice_ids.mapped('invoice_line_ids'):
                product_data.append({
                    'id': line.product_id.default_code,
                    'name': line.product_id.name,
                    'quantity': line.quantity,
                    'price': line.price_unit,
                    'subtotal': line.price_subtotal,
                    'count': str(count)
                })
                count += 1
            moneris_tx_values.update({
                'ship_country': invoice_ids[0].partner_shipping_id.country_id and invoice_ids[0].partner_shipping_id.country_id.name or '',
                'ship_company_name': invoice_ids[0].partner_shipping_id.company_name,
                'ship_state_or_province': invoice_ids[0].partner_shipping_id.state_id and invoice_ids[0].partner_shipping_id.state_id.name or '',
                'ship_address_one': invoice_ids[0].partner_shipping_id.street,
                'ship_first_name': invoice_ids[0].partner_shipping_id.name,
                'ship_postal_code': invoice_ids[0].partner_shipping_id.zip,
                'ship_city': invoice_ids[0].partner_shipping_id.city,
                'ship_phone': invoice_ids[0].partner_shipping_id.phone,
                'amount': tx_id.amount,
            })
        elif tx_id and tx_id.sale_order_ids:
            order_ids = tx_id.sale_order_ids
            count = 1
            for line in order_ids.mapped('order_line'):
                product_data.append({
                    'id': line.product_id.default_code,
                    'name': line.product_id.name,
                    'quantity': line.product_uom_qty,
                    'price': line.price_unit,
                    'subtotal': line.price_subtotal,
                    'count': str(count)
                })
                count += 1
            moneris_tx_values.update({
                'ship_country': order_ids[0].partner_shipping_id.country_id and order_ids[0].partner_shipping_id.country_id.name or '',
                'ship_company_name': order_ids[0].partner_shipping_id.company_name,
                'ship_state_or_province': order_ids[0].partner_shipping_id.state_id and order_ids[0].partner_shipping_id.state_id.name or '',
                'ship_address_one': order_ids[0].partner_shipping_id.street,
                'ship_first_name': order_ids[0].partner_shipping_id.name,
                'ship_postal_code': order_ids[0].partner_shipping_id.zip,
                'ship_city': order_ids[0].partner_shipping_id.city,
                'ship_phone': order_ids[0].partner_shipping_id.phone,
                'amount': tx_id.amount,
            })
        moneris_tx_values.update({
            'ps_store_id': self.moneris_email_account,
            'hpp_key': self.moneris_seller_account,
            'cmd': '_xclick',
            'order_id': values['reference'],
            'business': self.moneris_email_account,
            'item_name': values['reference'],
            'item_number': values['reference'],
            'currency_code': values['currency'] and values['currency'].name or '',
            'email': values['partner_email'],
            'bill_address_one': values['partner_address'],
            'bill_city': values['partner_city'],
            'bill_country': values['partner_country'] and values['partner_country'].name or '',
            'bill_state_or_province': values['partner_state'] and values['partner_state'].name or '',
            'bill_postal_code': values['partner_zip'],
            'bill_first_name': values['billing_partner'] and values['billing_partner'].name or '',
            'bill_company_name': values['billing_partner_commercial_company_name'] or '',
            'bill_phone': values['partner_phone'],
            'cust_id': values['partner'] and values['partner'].customer_id or '',
            'items': product_data,
            'rvarreturn_url': moneris_tx_values.get('return_url')
        })
        return moneris_tx_values

    def moneris_get_form_action_url(self):
        self.ensure_one()
        environment = 'prod' if self.state == 'enabled' else 'test'
        return self._get_moneris_urls(environment)['moneris_form_url']

    @api.model
    def moneris_s2s_form_process(self, data):
        """
        This Method is used to create a Token from credit card Information
        """
        values = {
            'cc_number': data.get('cc_number'),
            'cc_holder_name': data.get('cc_holder_name'),
            'cc_expiry': data.get('cc_expiry'),
            'cc_cvc': data.get('cc_cvc'),
            'cc_brand': data.get('cc_brand'),
            'acquirer_id': self.id or int(data.get('acquirer_id')),
            'partner_id': int(data.get('partner_id'))
        }
        PaymentMethod = self.env['payment.token'].sudo().create(values)
        return PaymentMethod

    def moneris_s2s_form_validate(self, data):
        """
        This Method is used to Validate Credit card Information.
        """
        error = dict()
        mandatory_fields = ["cc_number", "cc_cvc", "cc_holder_name", "cc_expiry", "cc_brand"]
        for field_name in mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        expiry_date = data.get('cc_expiry').replace(' ', '')
        if data['cc_expiry'] and datetime.now().strftime('%y%M') > datetime.strptime(expiry_date, '%M/%y').strftime(
                '%y%M'):
            return False
        return False if error else True


class TxMoneris(models.Model):
    _inherit = 'payment.transaction'

    _moneris_valid_tx_status = 27

    cust_id = fields.Char('Customer ID')
    receipt_id = fields.Char('Receipt ID')
    response_code = fields.Char('Response Code')
    cc_number = fields.Char('Credit Card')
    expdate = fields.Char('Expiry Date')
    cardtype = fields.Char('Card Type')
    trans_time = fields.Char('Transaction Time')
    trans_date = fields.Char('Transaction Date')
    payment_type = fields.Char('Payment Type')
    reference_num = fields.Char('Reference Number')
    bank_approval_code = fields.Char('Bank Approval Code')
    trans_id = fields.Char('Transaction ID')

    def action_void(self):
        if any([t.state != 'authorized' and t.acquirer_id.provider != 'moneris' for t in self]):
            raise ValidationError(_('Only transactions having the capture status can be voided.'))
        for tx in self:
            tx.s2s_void_transaction()

    @api.model
    def _moneris_form_get_tx_from_data(self, data):
        reference, txn_id = data.get('response_order_id'), data.get('bank_transaction_id')
        if not reference or not txn_id:
            error_msg = 'Moneris: received data with missing reference (%s) or txn_id (%s)' % (reference, txn_id)
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        tx = self.search([('reference', '=', reference)])
        if not tx or len(tx) > 1:
            error_msg = 'Moneris: received data for reference %s' % reference
            if not tx:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return tx[0]

    def _moneris_form_get_invalid_parameters(self, data):
        invalid_parameters = []

        if self.acquirer_reference and data.get('bank_transaction_id') != self.acquirer_reference:
            invalid_parameters.append(('Transaction Id', data.get('bank_transaction_id'), self.acquirer_reference))
        # check what is buyed
        if float_compare(float(data.get('charge_total', '0.0')), self.amount, 2) != 0:
            invalid_parameters.append(('Amount', data.get('charge_total'), '%.2f' % self.amount))
        return invalid_parameters

    def _moneris_form_validate(self, data):
        if self.state == 'done':
            _logger.warning('Moneris: trying to validate an already validated tx (ref %s)' % self.reference)
            return True
        status_code = data.get('response_code', '0')
        if status_code in approve_response_code:
            if data.get('trans_name', False) in ['purchase']:
                self.write({
                    'acquirer_reference': data.get('bank_transaction_id', False),
                    'date': fields.Datetime.now(),
                    'state_message': str(data.get('message') + ' ' + str(status_code)),
                    'receipt_id': data.get('response_order_id'),
                    'response_code': status_code,
                    'cc_number': data.get('f4l4'),
                    'expdate': data.get('expiry_date'),
                    'cardtype': data.get('card'),
                    'trans_time': data.get('time_stamp'),
                    'trans_date': data.get('date_stamp'),
                    'trans_id': data.get('txn_num', False),
                    'bank_approval_code': data.get('bank_approval_code', False),
                })
                self._set_transaction_done()
            elif data.get('trans_name').lower() in ['preauth']:
                self.write({
                    'acquirer_reference': data.get('bank_transaction_id'),
                    'date': fields.Datetime.now(),
                    'state_message': str(data.get('message') + ' ' + str(status_code)),
                    'receipt_id': data.get('response_order_id'),
                    'response_code': status_code,
                    'cc_number': data.get('f4l4'),
                    'expdate': data.get('expiry_date'),
                    'cardtype': data.get('card'),
                    'trans_time': data.get('time_stamp'),
                    'trans_date': data.get('date_stamp'),
                    'trans_id': data.get('txn_num', False),
                    'bank_approval_code': data.get('bank_approval_code', False),
                })
                self._set_transaction_authorized()
            if self.partner_id and not self.payment_token_id and \
               (self.type == 'form_save' or self.acquirer_id.save_token == 'always'):
                phone = False
                if self.partner_id.phone:
                    phone = self.partner_id.phone[1:] if '+' in self.partner_id.phone else self.partner_id.phone
                try:
                    request = moneris_vault.MonerisTokenizeCard(self.acquirer_id.store_id,
                                                                self.acquirer_id.api_token,
                                                                data.get('response_order_id'),
                                                                data.get('txn_num', False),
                                                                self.partner_id.customer_id,
                                                                self.partner_id.email, phone,
                                                                acquirer_id=self.acquirer_id)
                    response = request.send()
                    if response.get('code') == '001':
                        token_id = self.env['payment.token'].create({
                            'name': '%s - %s' % (data.get('f4l4', False), data.get('cardholder', False)),
                            'acquirer_ref': response.get('datakey'),
                            'acquirer_id': self.acquirer_id.id,
                            'partner_id': self.partner_id.id,
                        })
                        self.payment_token_id = token_id
                        if self.payment_token_id:
                            self.payment_token_id.verified = True
                    else:
                        raise Exception(response.get('message'))
                except Exception as e:
                    raise ValidationError(_("Moneris Error : %s !" % e))
            return True
        elif status_code in declined_response_codes or \
                status_code in referral_response_codes or status_code in system_error_response_codes or \
                status_code in amex_response_codes_declines or status_code in credit_card_response_codes_declines or \
                status_code in system_decline_response_codes or status_code in vault_response_code or \
                status_code == 'null':
            error = data.get('message', False)
            _logger.info(error)
            self.write({
                'acquirer_reference': data.get('bank_transaction_id', False),
                'date': fields.Datetime.now(),
                'state_message': str(data.get('message') + ' ' + str(status_code)),
                'receipt_id': data.get('response_order_id'),
                'response_code': status_code,
                'cc_number': data.get('f4l4'),
                'expdate': data.get('expiry_date'),
                'cardtype': data.get('card'),
                'trans_time': data.get('time_stamp'),
                'trans_date': data.get('date_stamp'),
                'trans_id': data.get('txn_num', False),
                'bank_approval_code': data.get('bank_approval_code', False),
            })
            self._set_transaction_cancel()
            return False

    def _get_model_id(self):
        model_id = False
        reference = self.reference.split('-')
        if 'x' in self.reference:
            reference = self.reference.split('x')
        if reference:
            model_id = self.env['account.move'].sudo().search([('name', '=', reference[0])], limit=1)
            if not model_id:
                model_id = self.env['sale.order'].sudo().search([('name', '=', reference[0])], limit=1)
        return model_id

    def moneris_s2s_do_transaction(self, **data):
        """
        This Method is called when user Make Payment using saved card.
        """
        self.ensure_one()
        acquirer = self.acquirer_id
        partner = self.partner_id
        product_lst = []
        phone = False
        is_sale_payment, is_invoice_payment = False, False
        if self.invoice_ids:
            product_lst = self.invoice_ids.mapped('invoice_line_ids').filtered(lambda l: not l.display_type)
        elif self.sale_order_ids:
            product_lst = self.sale_order_ids.mapped('order_line').filtered(lambda l: not l.display_type)
        if partner.phone:
            phone = partner.phone[1:] if '+' in partner.phone else partner.phone
        model_id = self._get_model_id()
        if model_id and model_id._name == 'account.move':
            is_invoice_payment = True
        elif model_id and model_id._name == 'sale.order':
            is_sale_payment = True

        if acquirer.capture_manually:
            payment_authorize_request = moneris_payment.MonerisAthorizeRequest(acquirer.store_id, acquirer.api_token,
                                                                               self.payment_token_id.acquirer_ref,
                                                                               self.reference, self.amount,
                                                                               partner.customer_id, acquirer_id=acquirer)
            response = payment_authorize_request.send()
        else:
            trxn_type = 'res_purchase_cc'
            payment_request = moneris_payment.MonerisPurchaseRequest(acquirer.store_id, acquirer.api_token,
                                                                     self.payment_token_id.acquirer_ref,
                                                                     self.reference, partner.customer_id,
                                                                     self.amount,
                                                                     partner.email, partner.name,
                                                                     partner.street, partner.city,
                                                                     partner.state_id.name, partner.zip,
                                                                     partner.country_id.name,
                                                                     phone, product_lst, trxn_type, acquirer_id=acquirer,
                                                                     is_invoice_payment=is_invoice_payment, is_sale_payment=is_sale_payment)
            response = payment_request.send()
        return self._moneris_s2s_validate_tree(response)

    def moneris_s2s_do_refund(self):
        self.ensure_one()
        acquirer = self.acquirer_id
        refund_request = moneris_payment.MonerisRefundRequest(acquirer.store_id, acquirer.api_token, self.reference,
                                                              self.amount, self.trans_id, acquirer_id=acquirer)
        response = refund_request.send()
        return self._moneris_s2s_validate_tree(response)

    def moneris_s2s_capture_transaction(self):
        """
        This Method is used to Capture Transaction when it's in 'Authorize' state.
        """
        if not self.receipt_id or not self.trans_id:
            raise ValidationError("Receipt ID or Transaction ID Not Found")
        else:
            capture_request = moneris_payment.MonerisCaptureRequest(self.acquirer_id.store_id,
                                                                    self.acquirer_id.api_token, self.receipt_id,
                                                                    self.amount, self.trans_id, acquirer_id=self.acquirer_id)
            response = capture_request.send()
            return self._moneris_s2s_validate_tree(response)

    def moneris_s2s_void_transaction(self):
        self.ensure_one()
        acquirer = self.acquirer_id
        void_request = moneris_payment.MonerisVoidRequest(acquirer.store_id, acquirer.api_token,
                                                          self.reference, self.trans_id, acquirer_id=acquirer)
        response = void_request.send()
        return self._moneris_s2s_validate_tree(response)

    def _moneris_s2s_validate_tree(self, response):
        return self._moneris_s2s_validate(response)

    def _moneris_s2s_validate(self, response):
        """
           This Method used to validate Transaction when payment is done by saved credit card.
        """
        # if self.state == 'done':
        #     _logger.warning('Moneris: trying to validate an already validated tx (ref %s)' % self.reference)
        #     return True
        trans_type = response.get('trans_type')
        response_code = response.get('response_code')
        data = {
            'state_message': str(response.get('message') + ' ' + response_code),
        }
        if response_code in approve_response_code:
            init_state = self.state
            data.update({
                'reference_num': response.get('reference_num'),
                'cardtype': response.get('cardtype'),
                'receipt_id': response.get('receipt_id'),
                'trans_id': response.get('trans_id'),
                'response_code': response_code,
                'trans_time': response.get('trans_time'),
                'trans_date': response.get('trans_date'),
                'date': fields.datetime.now(),
                'acquirer_reference': response.get('reference_num'),
            })
            if trans_type == '01': # Preauthorize request
                data.update({
                    'cust_id': response.get('cust_id'),
                    'cc_number': response.get('cc_number'),
                    'expdate': str(response.get('expdate')[-2:] + str(response.get('expdate')[:2])),
                    'payment_type': response.get('payment_type'),
                })
                self._set_transaction_authorized()
            elif trans_type == '00': #purchase request
                data.update({
                    'cust_id': response.get('cust_id'),
                    'cc_number': response.get('cc_number'),
                    'expdate': str(response.get('expdate')[-2:] + str(response.get('expdate')[:2])),
                    'payment_type': response.get('payment_type'),
                })
                if init_state != 'authorized':
                    self.execute_callback()
                self._set_transaction_done()
                if self.payment_id and self.state == 'done':
                    self.payment_id.post()
                    self.is_processed = True

            elif trans_type == '02': # for capture
                self.execute_callback()
                self._set_transaction_done()
            elif trans_type == '11': # decline
                self._set_transaction_cancel()
                if self.payment_id:
                    payment_id.cancel()
                    moves = payment_id.mapped('move_line_ids.move_id')
                    moves.filtered(lambda move: move.state == 'posted').button_draft()
                    moves.with_context(force_delete=True).unlink()
            if self.payment_token_id:
                self.payment_token_id.verified = True
            self.write(data)
            return True
        else:
            data.update({
                'state': 'error',
            })
            self.write(data)
            return False


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    @api.model
    def moneris_create(self, values):
        if values.get('cc_number'):
            values['cc_number'] = values['cc_number'].replace(' ', '')
            expiry = str(values['cc_expiry'][-2:] + str(values['cc_expiry'][:2]))
            acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
            partner = self.env['res.partner'].browse(values['partner_id'])
            phone = False
            if partner.phone:
                phone = partner.phone[1:] if '+' in partner.phone else partner.phone
            try:
                request = moneris_vault.MonerisVaultRequest(acquirer.store_id, partner.customer_id, acquirer.api_token,
                                                            phone, partner.email, values['cc_number'], expiry, acquirer_id=acquirer)
                response = request.send()
                if response.get('code') == '001':
                    return {
                        'acquirer_ref': response.get('datakey'),
                        'name': 'XXXXXXXXXXXX%s - %s' % (values['cc_number'][-4:], values['cc_holder_name'])
                    }
                else:
                    raise Exception(response.get('message'))
            except Exception as e:
                raise ValidationError(_("Moneris Error : %s !" % e))
        return {}

    def unlink(self):
        for rec in self:
            if rec.acquirer_id.provider == 'moneris':
                try:
                    request = moneris_vault.MonerisDeleteVault(rec.acquirer_id.store_id, rec.acquirer_id.api_token,
                                                               rec.acquirer_ref, acquirer_id=rec.acquirer_id)
                    response = request.send()
                    if response.get('code') == '001':
                        return super(PaymentToken, self).unlink()
                    return False
                except Exception as e:
                    raise ValidationError(_("Moneris Error : %s !" % e))
            else:
                return super(PaymentToken, self).unlink()
