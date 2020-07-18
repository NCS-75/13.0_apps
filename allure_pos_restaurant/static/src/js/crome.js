odoo.define('allure_pos_restaurant.crome', function (require) {
"use strict";

var chrome = require('point_of_sale.chrome');

var core = require('web.core');
var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

chrome.OrderSelectorWidget.include({
    renderElement: function(){
        var self = this;
        this._super();
        this.$el.closest('#floor_toggle').click(function(e){
            self.floor_button_click_handler();
        });
        if (this.pos.config.iface_floorplan) {
            if (this.pos.get_order()) {
                if (this.pos.table && this.pos.table.floor) {
                    self.$el.closest('.session-panel').append(QWeb.render('FloorDetails',{table: this.pos.table, floor:this.pos.table.floor}));
                }
            }
        }
    },
});

});