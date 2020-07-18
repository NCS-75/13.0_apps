odoo.define('allure_pos_theme.DashboardCustomizeTheme', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var Dialog = require('web.Dialog');
    var ajax = require('web.ajax');
    var session = require('web.session');
    var SystrayMenu = require('web.SystrayMenu');
    var framework = require('web.framework');
    var _t = core._t;

    var fields = {
        'leftbar_color': 'LeftBar',
        'menu_color': 'Menu',
        'buttons_color': 'Button',
        'button_box': 'Button Box',
        'heading_color': 'Heading',
        'label_color': 'Label',
        'label_value_color': 'Label Value',
        'link_color': 'Link Color',
        'panel_title_color': 'Panel Title',
        'tooltip_color': 'Tooltip',
        'border_color': 'Border',
    };

    var CustomizeThemeDialog = Dialog.extend({
        dialog_title: _t('Customize Theme'),
        template: "CustomizeTheme",
        events: {
            'click .o_add_theme': '_onClickAddRecord',
            'click ul.oe_theme_colorpicker li .o_view': '_onClickSelectTheme',
            'click ul.oe_theme_colorpicker li .o_remove': '_onClickRemoveTheme',
        },
        init: function (parent, result, themeData) {
            var self = this;
            this.result = result;
            this.parent = parent;
            this.theme_id = parent.theme_id;
            this.themeData = themeData;
            this.group_system = parent.group_system;
            $('body').addClass('open_customize_theme');
            this._super(parent, {
                title: _t('Customize Theme'),
                buttons: [{
                    text: _t('Apply'),
                    classes: 'btn-primary',
                    click: function () {
                        self._onClickSaveTheme();
                    },
                }, {
                    text: _t('Cancel'),
                    close: true,
                }],
            });
        },
        start: function () {
            var self = this;
            this.form_values = {};
            this.invalidFields = [];
            this.$el.find('.o_colorpicker').each(function () {
                $(this).minicolors({
                    control: 'hue',
                    inline: false,
                    letterCase: 'lowercase',
                    opacity: false,
                    theme: 'bootstrap',
                });
            });
            if (!_.isEmpty(this.result)) {
                this.current_theme = _.findWhere(this.result, {'selected': true});
                if (!_.isUndefined(this.current_theme)) {
                    self._fetchThemeData(self.current_theme.id);
                }
            }
            return this._super.apply(this, arguments);
        },
        close: function () {
            this.parent.customizeDialog = false;
            $('body').removeClass('open_customize_theme');
            this._super.apply(this, arguments);
        },
        destroy: function (options) {
            this.parent.customizeDialog = false;
            $('body').removeClass('open_customize_theme');
            this._super.apply(this, arguments);
        },
        _onClickAddRecord: function () {
            this.$el.addClass('o_new_record');
            this.$('.o_control_form').find('input.minicolors-input').minicolors('value', '');
            this.$('.o_breadcrumb_form').find('input').minicolors('value', '');
        },
        _setSelectedTheme: function (result) {
            var self = this;
            this.$el.removeClass('o_new_record');
            _.each(result, function (value, field) {
                self.$('input[name=' + field + ']').minicolors('value', value);
            });
        },
        _fetchThemeData: function (theme_id) {
            var self = this;
            var form_fields = _.keys(fields);
            this._rpc({
                model: 'ir.web.theme',
                method: 'search_read',
                domain: [['id', '=', theme_id]],
                fields: form_fields,
            }).then(function (result) {
                self._setSelectedTheme(result[0]);
            });
        },
        _removeTheme: function ($li, res_id) {
            var self = this;
            self._rpc({
                model: 'ir.web.theme',
                method: 'unlink',
                args: [parseInt(res_id, 10)],
            }).then(function (value) {
                $li.remove();
                self.do_notify(_t("Sucsess"), _t("Theme removed successfully."));
            })
        },
        _onClickSelectTheme: function (e) {
            var self = this;
            this.$el.find('ul li').removeClass('selected');
            $(e.currentTarget).parents('li').addClass('selected');
            var res_id = $(e.currentTarget).parents('li').find('span').data('id');
            if (res_id !== 0) {
                self._fetchThemeData(res_id);
            }
        },
        _onClickRemoveTheme: function (e) {
            var self = this;
            var res = confirm(_t("Do you want to delete this record?"));
            if (res) {
                var res_id = $(e.currentTarget).parents('li').find('span').data('id');
                if (res_id !== 0) {
                    var $li = $(e.currentTarget).parents('li');
                    self._removeTheme($li, res_id);
                }
            }
        },
        _createRecord: function (form_values) {
            return this._rpc({
                model: 'ir.web.theme',
                method: 'create',
                args: [form_values],
                kwargs: {context: session.user_context},
            });
        },
        _updateRecord: function (theme_id, form_values) {
            var self = this, user_vals = {};
            return this._rpc({
                model: 'ir.web.theme',
                method: 'write',
                args: [[theme_id], form_values],
            }).then(function (value) {
                return self._rpc({
                    model: 'res.users',
                    method: 'write',
                    args: [[session.uid], user_vals],
                })
            });
        },
        _changeCurrentTheme: function (theme_id) {
            var self = this;
            return this._rpc({
                model: 'ir.web.theme',
                method: 'set_customize_theme',
                args: [theme_id, self.form_values],
            }).then(function () {
                location.reload();
            });
        },
        _notifyInvalidFields: function (invalidFields) {
            var warnings = invalidFields.map(function (fieldName) {
                var fieldStr = fields[fieldName];
                return _.str.sprintf('<li>%s</li>', _.escape(fieldStr));
            });
            warnings.unshift('<ul>');
            warnings.push('</ul>');
            this.do_warn(_t("The following fields are invalid:"), warnings.join(''));
        },
        _doChangeTheme: function (theme_id) {
            var self = this;
            self._changeCurrentTheme(theme_id).then(function () {
                self.do_notify(_t("Sucsess"), _t("Theme customized successfully."));
                self.close(true);
                return;
            });
        },
        _onClickSaveTheme: function () {
            var self = this, theme_id;
            var form_fields = this.$('.o_control_form').serializeArray();
            _.each(form_fields, function (input) {
                if (input.value !== '') {
                    self.form_values[input.name] = input.value;
                } else {
                    self.invalidFields.push(input.name);
                }
            });

            if (!_.isEmpty(self.invalidFields)) {
                self._notifyInvalidFields(self.invalidFields);
                self.invalidFields = [];
                return false;
            } else {
                if (self.$el.hasClass('o_new_record')) {
                    self._createRecord(self.form_values).then(function (theme_id) {
                        self._doChangeTheme(theme_id);
                    })
                } else {
                    theme_id = this.$el.find('ul li.selected span').data('id');
                    theme_id = theme_id || self.theme_id;
                    if (theme_id && !_.isUndefined(theme_id) && theme_id !== 0) {
                        self._updateRecord(parseInt(theme_id), self.form_values).then(function () {
                            self._doChangeTheme(parseInt(theme_id));
                        })
                    }
                }
            }
        },
    });
    var DashboardCustomizeTheme = Widget.extend({
        template: 'DashboardThemeColors',
        events: {
            'click .o_setup_theme': '_onClickSetupTheme',
        },
        init: function (parent) {
            this.parent = parent;
            this.group_system = false;
            this.customizeDialog = false;
            this.group_theme_config = false;
            this._super.apply(this, arguments);
        },
        willStart: function () {
            var self = this;
            self.getSession().user_has_group('base.group_system').then(function (has_group) {
                self.group_system = has_group;
            });
            return self.getSession().user_has_group('allure_pos_theme.group_theme_setting_user').then(function (is_theme_access) {
                self.group_theme_config = is_theme_access
            });
        },
        start: function () {
            this._super.apply(this, arguments);
        },
        _onClickSetupTheme: function (event) {
            event.stopPropagation();
            event.preventDefault();
            var self = this;
            if (!this.customizeDialog) {
                self.customizeDialog = true;
                var form_fields = _.keys(fields);
                self._rpc({
                    model: 'ir.web.theme',
                    method: 'search_read',
                    fields: form_fields,
                }).then(function (result) {
                    self._rpc({
                        model: 'ir.web.theme',
                        method: 'get_current_theme',
                        args: []
                    }).then(function (theme_id) {
                        self.theme_id = theme_id;
                        _.each(result, function (rec, i) {
                            result[i]['selected'] = (rec.id === parseInt(theme_id));
                        });
                        return new CustomizeThemeDialog(self, result).open();
                    });
                })
            } else {
                $('footer.modal-footer .btn-secondary').click();
            }
        },
    });

    SystrayMenu.Items.push(DashboardCustomizeTheme);
    return SystrayMenu;
});