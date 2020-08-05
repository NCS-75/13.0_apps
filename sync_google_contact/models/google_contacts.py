# -*- coding: utf-8 -*-
# Part of Synconics. See LICENSE file for full copyright and licensing details.

import werkzeug
import json
import urllib
import requests
import math
from odoo.http import request
from datetime import datetime, timedelta
from odoo.addons.google_account import TIMEOUT
from odoo.exceptions import UserError, ValidationError, RedirectWarning
import tempfile
import base64
import os

import gdata.contacts.client

import atom.data
import gdata.data
import gdata.contacts.data
import gdata.contacts

from odoo import api, fields, models, _

import logging
_logger = logging.getLogger(__name__)

class GoogleContacts(models.Model):
    _name = "google.contacts"
    _description = "Google Contacts"

    def get_token(self):
        current_user = self.env.user
        if not current_user.google_contacts_token_validity or \
                fields.Datetime.from_string(str(current_user.google_contacts_token_validity).split('.')[0]) < (datetime.now() + timedelta(minutes=1)):
            try:
                self.do_refresh_token()
            except Exception as e:
                raise e
            current_user.refresh()
        return current_user.google_contacts_rtoken

    def do_refresh_token(self):
        current_user = self.env.user
        gs_pool = self.env['google.service']

        if not current_user.google_contacts_rtoken:
            return False

        all_token = gs_pool._refresh_google_token_json(current_user.google_contacts_rtoken, 'contacts')

        vals = {}
        vals['google_contacts_token_validity'] = datetime.now() + timedelta(seconds=all_token.get('expires_in'))
        vals['google_contacts_token'] = all_token.get('access_token')

        self.env.user.sudo().write(vals)

    def need_authorize(self):
        rtoken = self.get_token()
        return rtoken or False

    def authorize_google_uri(self, from_url='http://www.openerp.com'):
        url = self.env['google.service']._get_authorize_uri(from_url, 'contacts', scope=self.get_google_scope())
        return url

    @api.model
    def set_all_tokens(self, authorization_code):
        _logger.error("token set")
        gs_pool = self.env['google.service']
        all_token = gs_pool._get_google_token_json(authorization_code, 'contacts')

        vals = {}
        vals['google_contacts_rtoken'] = all_token.get('refresh_token')
        vals['google_contacts_token_validity'] = datetime.now() + timedelta(seconds=all_token.get('expires_in'))
        vals['google_contacts_token'] = all_token.get('access_token')
        self.env.user.write(vals)

    def g_contact_download(self):
        self.ensure_one()
        ir_config = self.env['ir.config_parameter'].sudo()
        google_contacts_client_id = ir_config.get_param('google_contacts_client_id')
        google_contacts_client_secret = ir_config.get_param('google_contacts_client_secret')
        if google_contacts_client_id and google_contacts_client_secret:
            if self.need_authorize():
                my_from_url = request.httprequest.host_url + "google/contacts/auth/download"
                return {'type': 'ir.actions.act_url', 'url': my_from_url, 'target': 'self'}
            else:
                my_from_url = request.httprequest.host_url + "google/contacts/auth/download"
                url = self.authorize_google_uri(from_url=my_from_url)
                return {'type': 'ir.actions.act_url', 'url': url, 'target': 'self'}

    def g_contact_upload(self):
        self.ensure_one()
        ir_config = self.env['ir.config_parameter'].sudo()
        google_contacts_client_id = ir_config.get_param('google_contacts_client_id')
        google_contacts_client_secret = ir_config.get_param('google_contacts_client_secret')
        if google_contacts_client_id and google_contacts_client_secret:
            if self.need_authorize():
                my_from_url = request.httprequest.host_url + "google/contacts/auth/upload"
                return {'type': 'ir.actions.act_url', 'url': my_from_url, 'target': 'self'}
            else:
                my_from_url = request.httprequest.host_url + "google/contacts/auth/upload"
                url = self.authorize_google_uri(from_url=my_from_url)
                return {'type': 'ir.actions.act_url', 'url': url, 'target': 'self'}

    @api.model
    def export_contacts(self):
        gs_pool = self.env['google.service']
        ir_config = self.env['ir.config_parameter'].sudo()

        google_contacts_client_id = ir_config.get_param('google_contacts_client_id')
        google_contacts_client_secret = ir_config.get_param('google_contacts_client_secret')

        access_token = self.env.user.google_contacts_token
        refresh_token = self.env.user.google_contacts_rtoken

        SCOPES = ['https://www.google.com/m8/feeds/','https://www.googleapis.com/auth/userinfo.email']

        if access_token:
            auth_token = gdata.gauth.OAuth2Token(
                client_id=google_contacts_client_id,
                client_secret=google_contacts_client_secret,
                scope=SCOPES,
                user_agent='MyUserAgent/1.0',
                access_token=access_token,
                refresh_token=refresh_token)

            client = gdata.contacts.client.ContactsClient(source='synconics', auth_token=auth_token)

            for contact in self.env['res.partner'].search([('email', '!=', False)]):
                google_contacts_id = contact_entry = False
                for contact_id in contact.google_contact_ids:
                    if contact_id.user_id == self.env.user:
                        google_contacts_id = contact_id.google_contacts_id

                if google_contacts_id:
                    try:
                        # First retrieve the contact to modify from the API.
                        contact_entry = client.GetContact(google_contacts_id)
                        if contact_entry:
                            self.update_contacts(contact=contact, client=client, contact_entry=contact_entry)
                    except gdata.client.RequestError as e:
                        if e.status == 412:
                            # Etags mismatch: handle the exception.
                            raise ValidationError(_('This contact (%s) is not available in your google account.') % contact.name)
                    finally:
                        if not contact_entry and contact.google_contact_ids:
                            google_contacts_ids = contact.google_contact_ids.search([('google_contacts_id', '=', google_contacts_id),
                                                         ('user_id', '=', self.env.uid)])
                            google_contacts_ids.unlink()
                            self.create_contacts(contact=contact, client=client)
                else:
                    flag = True
                    flag1 = False

                    if contact.google_contact:
                        flag = False
                    else:
                        flag = True

                    for user in contact.user_ids:
                        if self.env.user == user:
                            flag = True

                    if flag:
                        for google_contact in contact.google_contact_ids:
                            if self.env.user == google_contact.user_id:
                                flag1 = True

                    if flag and not flag1:
                        try:
                            self.create_contacts(contact=contact, client=client)
                        except Exception as e:
                            raise e

    def create_contacts(self, contact, client):
        new_contact = gdata.contacts.data.ContactEntry()
        # Set the contact's name.
        new_contact.name = gdata.data.Name(
          given_name=gdata.data.GivenName(text=contact.name or ''),
          family_name=gdata.data.FamilyName(text=contact.last_name or ''),
          additional_name=gdata.data.AdditionalName(text=contact.middle_name or ''))

        new_contact.organization = gdata.data.Organization(
            job_description=gdata.data.OrgTitle(text=contact.function or ''),
            title=gdata.data.OrgName(text=contact.parent_id and contact.parent_id.name or ''))

        new_contact.content = atom.data.Content(text=contact.comment)

        # Set the contact's email addresses.
        new_contact.email.append(gdata.data.Email(address=contact.email,
          rel=gdata.data.WORK_REL, display_name=contact.name))
        new_contact.email.append(gdata.data.Email(address=contact.email,
          rel=gdata.data.HOME_REL))
        # Set the contact's phone numbers.
        new_contact.phone_number.append(gdata.data.PhoneNumber(text=contact.phone or '+00',
          rel=gdata.data.WORK_REL))
        if contact.home_phone:
            new_contact.phone_number.append(gdata.data.PhoneNumber(text=contact.home_phone,
              rel=gdata.data.HOME_REL))

        if contact.mobile:
            new_contact.phone_number.append(gdata.data.PhoneNumber(text=contact.mobile,
              rel=gdata.data.MOBILE_REL))

        if contact.fax:
            new_contact.phone_number.append(gdata.data.PhoneNumber(text=contact.fax,
              rel=gdata.data.WORK_FAX_REL))

        if contact.home_fax:
            new_contact.phone_number.append(gdata.data.PhoneNumber(text=contact.home_fax,
              rel=gdata.data.HOME_FAX_REL))

        new_contact.structured_postal_address.append(
          gdata.data.StructuredPostalAddress(
            rel=gdata.data.WORK_REL, primary='true',
            street=gdata.data.Street(text=contact.street or ''),
            neighborhood=gdata.data.Neighborhood(text=contact.street2 or ''),
            city=gdata.data.City(text=contact.city or ''),
            region=gdata.data.Region(text=contact.state_id and contact.state_id.name or ''),
            postcode=gdata.data.Postcode(text=contact.zip),
            country=gdata.data.Country(text=contact.country_id and contact.country_id.name or '')))

        contact_entry = client.CreateContact(new_contact)

        # Add Photo
        result_fd, excel_file_name = tempfile.mkstemp()
        if contact.image_1920:
           os.write(result_fd, base64.decodestring(contact.image_1920))
           client.ChangePhoto(excel_file_name, contact_entry, content_type='image/*')
           _logger.info("\n\n Create Syncing Google Contact Photo is Updated")

        contact.google_contact_ids = [(0, 0, {'user_id': self.env.user.id,
            'google_contacts_id': contact_entry.id.text})]
        _logger.info('Contact is created : (%s)', (contact_entry.id.text,))

    def update_contacts(self, contact, client, contact_entry):

        # # Add Photo
        # result_fd, excel_file_name = tempfile.mkstemp()
        # if contact.image_1920:
        #     os.write(result_fd, base64.decodestring(contact.image_1920))
        #     client.ChangePhoto(excel_file_name, contact_entry, content_type='image/*')
        #     _logger.info("\n\n Update Contact Syncing Google Contact Photo is Updated")

        # Update Name
        contact_entry.name = gdata.data.Name(
          given_name=gdata.data.GivenName(text=contact.name or ''),
          family_name=gdata.data.FamilyName(text=contact.last_name or ''),
          additional_name=gdata.data.AdditionalName(text=contact.middle_name  or ''))

        contact_entry.organization = gdata.data.Organization(
            job_description=gdata.data.OrgTitle(text=contact.function or ''),
            title=gdata.data.OrgName(text=contact.parent_id and contact.parent_id.name or ''))

        contact_entry.content = atom.data.Content(text=contact.comment)

        # Update Email
        email_list = []
        if contact.email:
            email_list.append(gdata.data.Email(address=contact.email,
                                  rel=gdata.data.WORK_REL, display_name=contact.name))
            email_list.append(gdata.data.Email(address=contact.email,
              rel=gdata.data.HOME_REL))
            contact_entry.email = email_list

        # Update Phone
        phone_list = []

        if contact.phone:
            phone_list.append(gdata.data.PhoneNumber(text=contact.phone or '+00',
              rel=gdata.data.WORK_REL))

        if contact.home_phone:
            phone_list.append(gdata.data.PhoneNumber(text=contact.home_phone,
              rel=gdata.data.HOME_REL))

        if contact.mobile:
            phone_list.append(gdata.data.PhoneNumber(text=contact.mobile,
              rel=gdata.data.MOBILE_REL))

        if contact.fax:
            phone_list.append(gdata.data.PhoneNumber(text=contact.fax,
              rel=gdata.data.WORK_FAX_REL))

        if contact.home_fax:
            phone_list.append(gdata.data.PhoneNumber(text=contact.home_fax,
              rel=gdata.data.HOME_FAX_REL))

        contact_entry.phone_number = phone_list

        # Update Postal Address
        contact_entry.structured_postal_address = []
        contact_entry.structured_postal_address.append(
              gdata.data.StructuredPostalAddress(
              rel=gdata.data.WORK_REL, primary='true',
              street=gdata.data.Street(text=contact.street or ''),
              neighborhood=gdata.data.Neighborhood(text=contact.street2 or ''),
              city=gdata.data.City(text=contact.city or ''),
              region=gdata.data.Region(text=contact.state_id and contact.state_id.name or ''),
              postcode=gdata.data.Postcode(text=contact.zip),
              country=gdata.data.Country(text=contact.country_id and contact.country_id.name or '')))

        try:
            updated_contact = client.Update(contact_entry)
            _logger.info('Contact is updated : (%s)', (updated_contact.updated.text))
        except Exception as e:
            raise UserError(_('Sync Error (%s).') % e)

    @api.model
    def export_contacts_cron(self):
        try:
            users = self.env['res.users'].search([('google_contacts_token', '!=', False), ('google_contacts_rtoken', '!=', False)])
            for user in users:
                if self.sudo().with_user(user.id).need_authorize():
                    self.sudo().with_user(user.id).export_contacts()
                else:
                    _logger.info('%s user needs to authenticate.', user.partner_id.name)
        except Exception as e:
            _logger.info(e)

    @api.model
    def import_contacts_cron(self):
        try:
            users = self.env['res.users'].search([('google_contacts_token', '!=', False), ('google_contacts_rtoken', '!=', False)])
            for user in users:
                if self.sudo().with_user(user.id).need_authorize():
                    self.sudo().with_user(user.id).import_contacts()
                else:
                    _logger.info('%s user needs to authenticate.', user.partner_id.name)
        except Exception as e:
            _logger.info(e)

    @api.model
    def import_contacts(self):
        """
            Import Contacts from Google Contact
        """
        gs_pool = self.env['google.service']
        ir_config = self.env['ir.config_parameter'].sudo()

        google_contacts_client_id = ir_config.get_param('google_contacts_client_id')
        google_contacts_client_secret = ir_config.get_param('google_contacts_client_secret')

        access_token = self.env.user.google_contacts_token
        refresh_token = self.env.user.google_contacts_rtoken

        SCOPES = ['https://www.google.com/m8/feeds/','https://www.googleapis.com/auth/userinfo.email']
        try:
            if access_token:
                auth_token = gdata.gauth.OAuth2Token(
                    client_id=google_contacts_client_id,
                    client_secret=google_contacts_client_secret,
                    scope=SCOPES,
                    user_agent='MyUserAgent/1.0',
                    access_token=access_token,
                    refresh_token=refresh_token)

                client = gdata.contacts.client.ContactsClient(source='synconics', auth_token=auth_token)

                for contact in self.env['res.partner'].search([('email', '!=', False)]):
                    google_contacts_id = False
                    for contact_id in contact.google_contact_ids:
                        if contact_id.user_id == self.env.user:
                            google_contacts_id = contact_id.google_contacts_id

                headers = {'Authorization': 'Bearer ' + access_token, 'GData-Version': '3.0'}
                #Get the 'My Contacts' Group
                response_string = requests.get("https://www.google.com/m8/feeds/groups/default/full/?v=3.0&alt=json", headers=headers)
                google_contacts_group_json = json.loads(response_string.text)
                if google_contacts_group_json.get('feed') and google_contacts_group_json.get('feed').get('entry'):
                    my_contacts_group = google_contacts_group_json['feed']['entry'][0]['id']['$t']
                #Fetch the first 25 and get the total results in the process
                start_index = 1
                response_string = requests.get("https://www.google.com/m8/feeds/contacts/default/full?v=3.0&alt=json&start-index=" + str(start_index), headers=headers)
                google_contacts_json = json.loads(response_string.text)
                total_results = google_contacts_json['feed']['openSearch$totalResults']['$t']
                num_pages = math.ceil(int(int(total_results) / 25))
                no_1 = int(total_results) / 25
                no_2 = str(no_1).split('.')
                no_3 = float(no_2[1])
                if no_3 > 0.0:
                    num_pages = num_pages + 1.0

                for page in range(1, int(num_pages) + 1):
                    account_email = google_contacts_json['feed']['id']['$t']
                    for contact in google_contacts_json['feed']['entry']:

                        if 'gd$name' not in contact:
                            continue

                        contact_id = contact['id']['$t']
                        parent_id = False
                        g_contact_dict = {}

                        if contact.get('gd$name') and contact['gd$name'].get('gd$givenName'):
                            g_contact_dict['name'] = contact['gd$name']['gd$givenName']['$t']
                        if contact.get('gd$name') and contact['gd$name'].get('gd$additionalName'):
                            g_contact_dict['middle_name'] = contact['gd$name']['gd$additionalName']['$t']
                        if contact.get('gd$name') and contact['gd$name'].get('gd$familyName'):
                            g_contact_dict['last_name'] = contact['gd$name']['gd$familyName']['$t']

                        if contact.get('gd$organization') and contact['gd$organization'][0].get('gd$orgTitle'):
                            g_contact_dict['function'] = contact['gd$organization'][0]['gd$orgTitle']['$t']

                        if contact.get('gd$organization') and contact['gd$organization'][0].get('gd$orgName'):
                            parent_id = contact['gd$organization'][0]['gd$orgName']['$t']
                        if contact.get('gContact$website') and contact['gContact$website'][0]:
                            g_contact_dict['website'] = contact['gContact$website'][0].get('href')
                        if contact.get('content'):
                            g_contact_dict['comment'] = contact.get('content').get('$t')

                        if 'gd$email' in contact:
                            g_contact_dict['email'] = contact['gd$email'][0]['address']

                        if 'gd$phoneNumber' in contact:
                            for phone_data in contact['gd$phoneNumber']:
                                if 'rel' in phone_data.keys():
                                    rel = phone_data['rel'].split('#')
                                    if rel[-1] == 'mobile':
                                        g_contact_dict['mobile'] = phone_data['$t']
                                    if rel[-1] == 'work':
                                        g_contact_dict['phone'] = phone_data['$t']
                                    if rel[-1] == 'home':
                                        g_contact_dict['home_phone'] = phone_data['$t']
                                    if rel[-1] == 'work_fax':
                                        g_contact_dict['fax'] = phone_data['$t']
                                    if rel[-1] == 'home_fax':
                                        g_contact_dict['home_fax'] = phone_data['$t']
                                if 'label' in phone_data.keys():
                                    if phone_data.get('label') == 'Home Fax':
                                        g_contact_dict['home_fax'] = phone_data['$t']
                                    if phone_data.get('label') == 'Work Fax':
                                        g_contact_dict['fax'] = phone_data['$t']

                        if 'gd$structuredPostalAddress' in contact:
                            if 'gd$neighborhood' in contact['gd$structuredPostalAddress'][0]:
                                g_contact_dict['street2'] = contact['gd$structuredPostalAddress'][0]['gd$neighborhood']['$t']

                            if 'gd$street' in contact['gd$structuredPostalAddress'][0]:
                                g_contact_dict['street'] = contact['gd$structuredPostalAddress'][0]['gd$street']['$t']

                            if 'gd$city' in contact['gd$structuredPostalAddress'][0]:
                                g_contact_dict['city'] = contact['gd$structuredPostalAddress'][0]['gd$city']['$t']

                            if 'gd$region' in contact['gd$structuredPostalAddress'][0]:
                                state = contact['gd$structuredPostalAddress'][0]['gd$region']['$t']
                                #Find the corresponding state in out database
                                state_search = self.env['res.country.state'].search([('name','=', state)], limit=1)
                                g_contact_dict['state_id'] = state_search and state_search.id

                            if 'gd$country' in contact['gd$structuredPostalAddress'][0]:
                                country_search = False
                                #Find the corresponding country in out database
                                if contact['gd$structuredPostalAddress'][0]['gd$country'].get('$t', False):
                                    country = contact['gd$structuredPostalAddress'][0]['gd$country'].get('$t')
                                    country_search = self.env['res.country'].search([('name','=', country)], limit=1)
                                if not country_search and contact['gd$structuredPostalAddress'][0]['gd$country'].get('code', False):
                                    country = contact['gd$structuredPostalAddress'][0]['gd$country'].get('code')
                                    country_search = self.env['res.country'].search([('code','=', country)], limit=1)

                                g_contact_dict['country_id'] = country_search and country_search.id

                            if 'gd$postcode' in contact['gd$structuredPostalAddress'][0]:
                                    zip = contact['gd$structuredPostalAddress'][0]['gd$postcode']['$t']
                                    g_contact_dict['zip'] = zip or ''

                        # try:
                        #     hosted_image_binary = client.GetPhoto(contact)
                        #     if hosted_image_binary:
                        #         g_contact_dict.update({
                        #             'image_1920': base64.encodestring(hosted_image_binary)
                        #         })
                        # except Exception as e:
                        #     pass

                        existing_contacts = self.env['google.details'].search([('google_contacts_id', '=', contact_id)])

                        if len(existing_contacts) > 0:
                            for g_contact in existing_contacts:
                                #Update existing partner
                                if parent_id and g_contact.partner_id.company_type == 'company' and not g_contact.partner_id.parent_id:
                                    existing_partner_id = self.env['res.partner'].search([('name', '=', parent_id)], limit=1)
                                    if existing_partner_id and existing_partner_id.name == parent_id:
                                        g_contact_dict.update({'parent_id': existing_partner_id.id})
                                    else:
                                        vals = {'name': parent_id, 'company_type': 'company'}
                                        cust_parent_id = self.import_partner_create(vals=vals, contact_id=contact_id)
                                        g_contact_dict.update({'parent_id': cust_parent_id.id})
                                elif g_contact.partner_id.company_type != 'company':
                                    existing_partner_id = self.env['res.partner'].search([('name', '=', parent_id)], limit=1)
                                    if not parent_id and not existing_partner_id:
                                        g_contact_dict.update({'parent_id': False})
                                    else:
                                        if existing_partner_id and existing_partner_id.name == parent_id:
                                            g_contact_dict.update({'parent_id': existing_partner_id.id})
                                        else:
                                            vals = {'name': parent_id, 'company_type': 'company'}
                                            cust_parent_id = self.import_partner_create(vals=vals, contact_id=contact_id)
                                            g_contact_dict.update({'parent_id': cust_parent_id.id})
                                    g_contact.partner_id.write(g_contact_dict)
                        else:
                            if parent_id:
                                existing_partner_id = self.env['res.partner'].search([('name', '=', parent_id)], limit=1)
                                if existing_partner_id and existing_partner_id.name == parent_id:
                                    g_contact_dict.update({'parent_id': existing_partner_id.id})
                                if not existing_partner_id:
                                    vals = {'name': parent_id, 'company_type': 'company'}
                                    cust_parent_id = self.import_partner_create(vals=vals, contact_id=contact_id)
                                    g_contact_dict.update({'parent_id': cust_parent_id.id})
                            else:
                                g_contact_dict.update({'parent_id': False})
                            partner = self.import_partner_create(vals=g_contact_dict, contact_id=contact_id)

                    #Fetch the content for the next page
                    start_index += 25
                    response_string = requests.get("https://www.google.com/m8/feeds/contacts/default/full?v=3.0&alt=json&start-index=" + str(start_index), headers=headers)
                    google_contacts_json = json.loads(response_string.text)
        except Exception as e:
            _logger.info(e)

    def import_partner_create(self, vals, contact_id):
        """ Create new partner """
        vals = dict(vals)
        vals.update({
            'user_ids': [(6, 0, [self.env.uid])],
            'google_contact': True,
            'google_contact_ids': [(0, 0, {'user_id': self.env.uid,
            'google_contacts_id': contact_id})]
            })
        partner = self.env['res.partner'].create(vals)
        return partner

    def get_google_scope(self):
        return 'https://www.google.com/m8/feeds/'

    def get_access_token(self, scope=None):
        ir_config = self.env['ir.config_parameter']
        google_contacts_refresh_token = ir_config.get_param('google_contacts_refresh_token')
        if not google_contacts_refresh_token:
            if self.env.user._is_admin():
                model, action_id = self.env['ir.model.data'].get_object_reference('base_setup', 'action_general_configuration')
                msg = _("You haven't configured 'Authorization Code' generated from google, Please generate and configure it .")
                raise RedirectWarning(msg, action_id, _('Go to the configuration panel'))
            else:
                raise UserError(_("Google Contacts is not yet configured. Please contact your administrator."))
        google_contacts_client_id = ir_config.get_param('google_contacts_client_id')
        google_contacts_client_secret = ir_config.get_param('google_contacts_client_secret')
        #For Getting New Access Token With help of old Refresh Token

        data = werkzeug.url_encode(dict(client_id=google_contacts_client_id,
                                     refresh_token=google_contacts_refresh_token,
                                     client_secret=google_contacts_client_secret,
                                     grant_type="refresh_token",
                                     scope=scope or 'https://www.google.com/m8/feeds/'))
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        try:
            req = urllib.Request('https://accounts.google.com/o/oauth2/token', data, headers)
            content = urllib.urlopen(req, timeout=TIMEOUT).read()
        except urllib.HTTPError:
            if self.env.user._is_admin():
                model, action_id = self.env['ir.model.data'].get_object_reference('base_setup', 'action_general_configuration')
                msg = _("Something went wrong during the token generation. Please request again an authorization code .")
                raise RedirectWarning(msg, action_id, _('Go to the configuration panel'))
            else:
                raise UserError(_("Google Drive is not yet configured. Please contact your administrator."))
        content = json.loads(content)
        return content.get('access_token')
