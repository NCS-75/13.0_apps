odoo.define('allure_pos_theme.crome', function (require) {
"use strict";

var PosBaseWidget = require('point_of_sale.BaseWidget');
var chrome = require('point_of_sale.chrome');

var SystrayMenuWidget = PosBaseWidget.extend({
    template: 'SystrayMenuWidget',
    init: function(parent, options) {
        this._super(parent, options);
    },
    get_user: function(){
        var user = this.pos.get_cashier();
        var default_user = 0;
        if(user){
            if(!_.isUndefined(user.user_id[0])) {
                return user.user_id[0];
            }
            else {
                return default_user;
            }
        }else{
            return default_user;
        }
    },
    renderElement: function(){
        var self = this;
        this._super();
        this.$el.click(function(){
            self.$el.closest('.pos-systray').find('.systray-item').toggleClass('oe_hidden');
            self.$el.closest('.pos-topheader').find('.order-selector').addClass('oe_hidden');
        });
    },
});

var ProfileIcon = PosBaseWidget.extend({
    template: 'ProfileIcon',
    init: function(parent, options) {
        this._super(parent, options);
    },
    get_user: function(){
        var user = this.pos.get_cashier();
        var default_user = 0;
        if(user){
            if(!_.isUndefined(user.user_id[0])) {
                return user.user_id[0];
            }
            else {
                return default_user;
            }
        }else{
            return default_user;
        }
    },
});

chrome.UsernameWidget.include({
    renderElement: function(){
        var self = this;
        this._super();
        self.chrome.widget.systray_menu.renderElement();
        self.chrome.widget.profile_icon.renderElement();
    },
});

chrome.OrderSelectorWidget.include({
    renderElement: function(){
        var self = this;
        this._super();
        this.$el.closest('#session_toggle').click(function(e){
            if(!_.has(this.$el,'.oe_invisible')) {
                self.$el.closest('.order-selector').toggleClass('oe_hidden');
                self.$el.closest('.pos-topheader').find('.systray-item').addClass('oe_hidden');
            }
        });
    },
    getCompany: function() {
        var company_logo = '';
        if(!_.isUndefined(this.pos.company_logo_base64)) {
            company_logo = this.pos.company_logo_base64;
        }
        return company_logo;
    },
});

chrome.Chrome.include({
    load_widgets: function(widgets) {
        widgets.push({
            'name':   'systray_menu',
            'widget': SystrayMenuWidget,
            'prepend':  '.pos-systray',
        },{
            'name':   'profile_icon',
            'widget': ProfileIcon,
            'replace':  '.profile-imagewidget',
        });
        _.each(widgets, function(widget) {
            if (_.isEqual(widget.name, "close_button") || _.isEqual(widget.name, "lock_button")) {
                widget.append = '.systray-item'
            }
        });
        return this._super.apply(this, arguments)
    },
});

return {
    SystrayMenuWidget: SystrayMenuWidget,
    ProfileIcon: ProfileIcon,
};

});