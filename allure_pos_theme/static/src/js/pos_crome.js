odoo.define('allure_pos_theme.chrome', function (require) {
"use strict";

var SynchNotificationWidget = require('point_of_sale.chrome').SynchNotificationWidget

SynchNotificationWidget.include({
    start: function(){
        this._super();
        this.$el.parents('.pos-topheader').find('.panel_toggal').click(function() {
            $('body').toggleClass('oe_full_view');
        });
    },
});

});