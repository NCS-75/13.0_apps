# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import os
from odoo import _, api, fields, models
from odoo.exceptions import UserError

static_dict_theme = {
    '$brand-primary': '#072635;',
    '$brand-secondary': '#1983a4;',
    '$button-box': '#0b3a49;',
    '$heading': '#1983a4;',
    '$Label': '#0b3a49;',
    '$Label-value': '#0b3a49;',
    '$link': '#1983a4;',
    '$notbook': '#0b3a49;',
    '$tooltip': '#072630;',
    '$border': '#e6e9ea;',
    '$menu-main-title': '#0b3a49;'
}

tag_dict_theme = {
    '$brand-tag-info': '#00b3e5;',
    '$brand-tag-danger': '#ca0c05;',
    '$brand-tag-success': '#00aa00;',
    '$brand-tag-warning': '#e47e01;',
    '$brand-tag-primary': '#005ba9;',
    '$brand-tag-muted': '#717171;'
}


class IrWebTheme(models.Model):
    _name = "ir.web.theme"
    _description = "Theme Configuration"

    leftbar_color = fields.Char(string='Custom Color', required=True, default="#875a7b")
    menu_color = fields.Char(string='Menu', required=True, default="#666666")
    border_color = fields.Char(string='Border', required=True, default="#cccccc")
    buttons_color = fields.Char(string='Buttons Color', required=True, default="#00a09d")
    button_box = fields.Char(string='Button Box', required=True, default="#666666")
    heading_color = fields.Char(string='Heading Color', required=True, default="#2f3136")
    label_color = fields.Char(string='Label', required=True, default="#666666")
    label_value_color = fields.Char(string='Label Value Color', required=True, default="#666666")
    link_color = fields.Char(string='Link Color', required=True, default="#00a09d")
    panel_title_color = fields.Char(string='Panel Title Color', required=True, default="#2f3136")
    tooltip_color = fields.Char(string='Tooltip Color', required=True, default="#875a7b")

    def replace_file(self, file_path, static_dict):
        try:
            with open(file_path, 'w+') as new_file:
                for key, value in static_dict.items():
                    line = ''.join([key, ': ', value, ';\n'])
                    new_file.write(line)
            new_file.close()
        except Exception as e:
            raise UserError(_("Please follow the readme file. Contact to Administrator."
                              "\n %s") % e)

    @api.model
    def get_current_theme(self):
        return self.env['ir.config_parameter'].sudo().get_param("allure_pos_theme.selected_theme")

    @api.model
    def set_customize_theme(self, theme_id, form_values):
        self.env['ir.config_parameter'].sudo().set_param("allure_pos_theme.selected_theme", theme_id)
        is_backend_module_install = self.env['ir.config_parameter'].sudo().get_param("is_login_install")
        is_tag_module_install = self.env['ir.config_parameter'].sudo().get_param("is_tag_install")
        try:
            path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            theme_path = path + "/allure_pos_theme/static/src/scss/variables.scss"
            backend_login = path + "/backend_login/static/src/scss/variable.scss"
        except Exception as e:
            raise UserError(_("Please Contact to Administrator. \n %s") % e)

        # Backend Theme Changes
        if form_values.get('leftbar_color', False):
            static_dict_theme.update({'$brand-primary': form_values['leftbar_color']})

        if form_values.get('buttons_color', False):
            static_dict_theme.update({'$brand-secondary': form_values['buttons_color']})

        if form_values.get('button_box', False):
            static_dict_theme.update({'$button-box': form_values['button_box']})

        if form_values.get('heading_color', False):
            static_dict_theme.update({'$heading': form_values['heading_color']})

        if form_values.get('label_color', False):
            static_dict_theme.update({'$Label': form_values['label_color']})

        if form_values.get('label_value_color', False):
            static_dict_theme.update({'$Label-value': form_values['label_value_color']})

        if form_values.get('link_color', False):
            static_dict_theme.update({'$link': form_values['link_color']})

        if form_values.get('panel_title_color', False):
            static_dict_theme.update({'$notbook': form_values['panel_title_color']})

        if form_values.get('tooltip_color', False):
            static_dict_theme.update({'$tooltip': form_values['tooltip_color']})

        if form_values.get('menu_color', False):
            static_dict_theme.update({'$menu-main-title': form_values['menu_color']})

        if form_values.get('border_color', False):
            static_dict_theme.update({'$border': form_values['border_color']})

        self.replace_file(theme_path, static_dict_theme)

        # Backend Login Changes
        if is_backend_module_install and form_values.get('leftbar_color', False):
            self.replace_file(backend_login, {'$brand-primary': form_values.get['leftbar_color']})

        # Web Status Tag Changes
        return True