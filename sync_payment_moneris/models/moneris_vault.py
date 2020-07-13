# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from . import moneris_payment


class MonerisVaultRequest(moneris_payment.MonerisRequst):
    def __init__(self, store_id, customer_id, api_token, phone, email, pan, expdate, acquirer_id):
        self.customer_id = customer_id
        self.phone = phone
        self.pan = pan
        self.email = email
        self.expdate = expdate
        self.acquirer_id = acquirer_id
        super(MonerisVaultRequest, self).__init__(store_id, api_token)

    def _get_data(self):
        """
        This Method is used to generate XML format required to send a save card request.
        """
        data = []
        data.append("""
            <?xml version="1.0"?>
                <request>
                    <store_id>%s</store_id>
                    <api_token>%s</api_token>
                    <res_add_cc>
                        <cust_id>%s</cust_id>
                        <phone>%s</phone>
                        <email>%s</email>
                        <pan>%s</pan>
                        <expdate>%s</expdate>
                        <crypt_type>7</crypt_type>
                    </res_add_cc>
                </request>""" % (
            self.store_id, self.api_token, self.customer_id, self.phone, self.email, self.pan, self.expdate))
        environment = 'prod' if self.acquirer_id.state == 'enabled' else 'test'
        url = self.acquirer_id._get_moneris_urls(environment)['moneris_request_url']
        data.append(url)
        return data

    def _parse_response_body(self, root):
        return MonerisVaultResponse(root).get_response()


class MonerisVaultResponse(object):
    def __init__(self, root):
        self.root = root
        self.datakey = root.findtext('receipt/DataKey')
        self.code = root.findtext('receipt/ResponseCode')
        self.message = root.findtext('receipt/Message')

    def get_response(self):
        return {'code': self.code, 'datakey': self.datakey, 'message': self.message}


class MonerisDeleteVault(moneris_payment.MonerisRequst):
    def __init__(self, store_id, api_token, datakey, acquirer_id):
        self.datakey = datakey
        self.acquirer_id = acquirer_id
        super(MonerisDeleteVault, self).__init__(store_id, api_token)

    def _get_data(self):
        """
        This Method is used to generate XML format required to send a delete card request.
        """
        data = []
        data.append("""
            <?xml version="1.0"?>
                <request>
                    <store_id>%s</store_id>
                    <api_token>%s</api_token>
                    <res_delete>
                        <data_key>%s</data_key>
                    </res_delete>
                </request>""" % (self.store_id, self.api_token, self.datakey))
        environment = 'prod' if self.acquirer_id.state == 'enabled' else 'test'
        url = self.acquirer_id._get_moneris_urls(environment)['moneris_request_url']
        data.append(url)
        return data

    def _parse_response_body(self, root):
        return MonerisVaultDeleteResponse(root).get_response()


class MonerisVaultDeleteResponse(object):
    def __init__(self, root):
        self.root = root
        self.code = root.findtext('receipt/ResponseCode')
        self.message = root.findtext('receipt/Message')

    def get_response(self):
        return {'code': self.code, 'message': self.message}


class MonerisTokenizeCard(moneris_payment.MonerisRequst):
    def __init__(self, store_id, api_token, order_id, txn_number, customer_id, email, phone, acquirer_id):
        self.order_id = order_id
        self.txn_number = txn_number
        self.customer_id = customer_id
        self.email = email
        self.phone = phone
        self.acquirer_id = acquirer_id
        super(MonerisTokenizeCard, self).__init__(store_id, api_token)

    def _get_data(self):
        """
        This Method is used to generate XML format required to send Tokenized card request.
        """
        data = []
        data.append("""
            <?xml version="1.0"?>
                <request>
                    <store_id>%s</store_id>
                    <api_token>%s</api_token>
                    <res_tokenize_cc>
                        <order_id>%s</order_id>
                        <txn_number>%s</txn_number>
                        <cust_id>%s</cust_id>
                        <email>%s</email>
                        <phone>%s</phone>
                    </res_tokenize_cc>
                </request>""" % (self.store_id, self.api_token, self.order_id, self.txn_number, self.customer_id,
                                 self.email, self.phone))
        environment = 'prod' if self.acquirer_id.state == 'enabled' else 'test'
        url = self.acquirer_id._get_moneris_urls(environment)['moneris_request_url']
        data.append(url)
        return data

    def _parse_response_body(self, root):
        return MonerisVaultResponse(root).get_response()
