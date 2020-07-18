odoo.define('allure_pos_restaurant.floors', function (require) {
"use strict";

var FloorScreenWidget = require('pos_restaurant.floors').FloorScreenWidget;

FloorScreenWidget.include({
    renderElement: function(){
        self = this;
        this._super();
        this.$el.find('.floor-buttons').click(function(){
            self.$el.find('.floor-selector').toggleClass('show');
        });
    },
});

});