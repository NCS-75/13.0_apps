odoo.define('allure_pos_theme.screens', function (require) {
"use strict";


var ActionpadWidget = require('point_of_sale.screens').ActionpadWidget;
var ProductCategoriesWidget = require('point_of_sale.screens').ProductCategoriesWidget;
var ScreenWidget = require('point_of_sale.screens').ScreenWidget;
var OrderWidget = require('point_of_sale.screens').OrderWidget;
var PaymentScreenWidget = require('point_of_sale.screens').PaymentScreenWidget;
var ClientListScreenWidget = require('point_of_sale.screens').ClientListScreenWidget;
var ProductScreenWidget = require('point_of_sale.screens').ProductScreenWidget;
var ProductListWidget = require('point_of_sale.screens').ProductListWidget;
var gui = require('point_of_sale.gui');

    ActionpadWidget.include({
        renderElement: function() {
            var self = this;
            this._super();
            this.$('.panel').click(function(){
                self.$el.parents('.window').toggleClass('other_panel');
            });
        },
    });


    ProductScreenWidget.include({
        start: function(){
            var self = this;
            this._super();
            var defaultView = this.pos.config.default_view;
            self.renderView(defaultView,false);
            this.click_view_action = function(view,currentview){
                self.renderView(view,currentview);
            };
            this.action_update_order = function(){
                self.update_order_list();
            };
            if(this.pos.isMobile) {
                this.MobileSectionPanel = new MobileSectionPanel(this,{

                });
                this.MobileSectionPanel.replace(this.$('.panel-MobileSectionPanel'));
            }
        },
        renderView: function(view,currentview) {
            var self = this;
            if(view === 'oe_barcode' && currentview !== 'oe_barcode') {
                self.order_widget.replace(self.$('.product-list-container'));
                self.$('.subwindow-container-fix:not(.pads)').append('<div class="renderButtons"/>');
                this.renderButtons(view);
            }
            else if(currentview === 'oe_barcode' && view !== 'oe_barcode') {
                var self = this;
                self.product_list_widget.replace(self.$('.order-container'));
                self.$('.subwindow-container-fix').append('<div class="order_view"/>')
                self.order_widget.replace(self.$('.order_view'));
                self.$('.renderButtons').remove();
                this.renderButtons(view);
            }
            this.renderWidget(view);
        },
        renderWidget: function(view){
            this.$el.removeClass('oe_kanban oe_barcode oe_list').addClass(view);
            this.$el.find('.leftpane').removeClass('oe_kanban oe_barcode oe_list').addClass(view);
            this.$el.find('.rightpane .layout-table').removeClass('oe_kanban oe_barcode oe_list').addClass(view);
            $('.oe_view_btn[data-view="' + view + '"]').addClass('active');
            var view_btn =  $('.oe_view_btn[data-view="' + view + '"]').find('.fa').attr('class');
            this.$el.find('.dropdownMenuButton').attr("data-view",view);
            this.$el.find('.dropdownMenuButton i').removeAttr('class').addClass(view_btn);
            // gui change screen to set view
            this.pos.config.default_fa = view_btn;
            this.pos.config.default_view = view;
            var other_buttons = Object.keys(this.action_buttons);
            this.pos.config.other_buttons_menu = other_buttons.length;
        },
        renderButtons: function(view) {
            var other_buttons = Object.keys(this.action_buttons);
            if(other_buttons.length != 0) {
                for (var i = 0; i < other_buttons.length; i++) {
                    var classe = other_buttons[i];
                    if(view ==  'oe_barcode' && !this.pos.isMobile) {
                        this.action_buttons[classe].appendTo(self.$('.renderButtons'))
                    }
                    else {
                        this.action_buttons[classe].appendTo(self.$('.control-buttons'));
                    }
                }
            }
        },
    });

    ProductCategoriesWidget.include({
        init: function(parent, options){
            this._super.apply(this, arguments);
            self = this;
            this.breadcrumbInner = [];
            this.click_view_handler = function(view,currentview){
                parent.click_view_action(view,currentview);
            };
            this.pos.bind('change:selectedClient', function() {
                self.renderElement();
            });
        },
        UserScreen: function() {
            this.gui.show_screen('clientlist');
        },
        renderElement: function() {
            var self = this;
            this._super();

            // select view button
            var buttons = this.el.querySelectorAll('.oe_view_btn');
            for(var i = 0; i < buttons.length; i++){
                buttons[i].addEventListener('click',function(event) {
                    self.ActiveView(event)
                });
            }

            // Set category button
            var list_container = this.el.querySelector('.category-list');
            if (!list_container) {
                if(!this.pos.isMobile){
                    this.el.querySelector('.oe-category').classList.add('oe_hidden');
                }
            }
            else {
                this.el.querySelector('.oe-category').classList.remove('oe_hidden');
            }
            var breadcrumb_more = this.el.querySelector('.oe_more_btn');
            if (breadcrumb_more) {
                this.el.querySelector('.oe_more_btn').addEventListener('click',this.BreadcrumbClick);
            }
            // Menage drop-down
            this.el.querySelector('.dropdownMenuButton').addEventListener('click',this.DropDown);
            this.el.querySelector('.oe-search').addEventListener('click',this.OpenSearch);
            this.el.querySelector('.oe-category').addEventListener('click',this.CategoryView);
            if(this.el.querySelector('.oe-filter')) {
                this.el.querySelector('.oe-filter').addEventListener('click',this.FilterBtn);
            }
            this.el.querySelector('.oe-user').addEventListener('click', function(){
                self.UserScreen();
            });

            this.el.querySelector('.oe-back-btn').addEventListener('click',function(){
                self.MobileBack();
            });
        },
        ActiveView: function(event) {
            var target = $(event.currentTarget)
            var currebtn = target.parents('.dropdown-custom').find('.dropdownMenuButton');
            var currentview = currebtn.attr('data-view');
            var view = target.data('view');
            target.closest('.dropdown-custom').removeClass('show');
            target.addClass('active');
            target.nextAll().removeClass('active');
            target.prevAll().removeClass('active');
            this.click_view_handler(view,currentview);
        },
        MobileBack: function() {
            this.gui.current_screen.$el.removeClass('oe_leftbar').removeClass('oe_other_btn');
        },
        BreadcrumbClick : function(event) {
            var panel = $(this).closest('.header-cell');
            panel.find('.breadcrumb_dropdown').toggleClass('show');
            //other drop down hide
            panel.find('.dropdown-custom , .control-buttons, .categories').removeClass('show');
        },
        CategoryView: function(event) {
            var panel = $(this).closest('.header-cell');
            panel.find('.categories').toggleClass('show');
            //other drop down hide
            panel.find('.dropdown-custom, .control-buttons, .breadcrumb_dropdown').removeClass('show');
        },
        DropDown: function(event) {
            var panel = $(this).closest('.header-cell');
            panel.find('.dropdown-custom').toggleClass('show');
            //other drop down hide
            panel.find('.categories, .control-buttons, .breadcrumb_dropdown').removeClass('show');
        },
        FilterBtn: function(event) {
            var panel = $(this).closest('.header-cell');
            panel.find('.control-buttons').toggleClass('show');
            //other drop down hide
            panel.find('.categories, .dropdown-custom, .breadcrumb_dropdown').removeClass('show');
        },
        OpenSearch: function(event) {
            var panel = $(this).closest('.header-cell');
            panel.find('.searchbox').addClass('show');
        },
        set_category : function(category){
            this._super.apply(this, arguments);
            if(!this.pos.isMobile){
                if (this.breadcrumb.length > 3) {
                    this.breadcrumbInner = this.breadcrumb.slice(3)
                    this.breadcrumb = this.breadcrumb.slice(0,3)
                }
                else {
                    this.breadcrumbInner = [];
                }
            }
        },
        clear_search: function(){
            this._super();
            var searchbox = this.el.querySelector('.searchbox');
            searchbox.classList.remove('show');
        },
    });

    ScreenWidget.include({
        start: function(){
            this._super();
            var self = this;
            var $width = $(document).width();
            this.pos.isMobile = false;
            if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || $width <= 991) {
                this.pos.isMobile = true;
            }
        },
        update_order_list: function() {
            var self = this;
            var order = this.pos.get_order();
            if (!order) {
                return;
            }
            var total     = order ? order.get_total_with_tax() : 0;
            var taxes     = order ? total - order.get_total_without_tax() : 0;
            this.$('.summary .total > .value').text(this.format_currency(total));
            this.$('.oe-payment-details').click(function() {
                self.orderBtnClick();
            });
            this.$('.oe-filter').click(function() {
                self.filterBtnClick();
            });
        },
        filterBtnClick: function() {
            this.gui.current_screen.$el.addClass('oe_other_btn');
        },
        orderBtnClick: function() {
            this.gui.current_screen.$el.addClass('oe_leftbar');
        },
    });

    OrderWidget.include({
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);
            this.update_order = function(){
                var prom = parent.action_update_order;
                Promise.resolve(prom).then(function() {
                    parent.action_update_order();
                });
            };
        },
        orderline_change: function(line){
            var def = this._super.apply(this, arguments);
            var products_data = $('.product-screen').find('.product-list');
            products_data.children().removeClass('selected');
            products_data.children().find('.product-qty').text('');
            if(this.pos.get_order()) {
                var data = this.pos.get_order().get_orderlines()
                var item = parseInt(line.get_quantity_str())
                if(!(data.length == 1 && item == 0)) {
                    _.each(data, function (line) {
                        var selected_product = products_data.find('[data-product-id='+line.product.id+']');
                        selected_product.addClass('selected');
                        selected_product.find('.product-qty').text(line.quantity);
                    });
                }
            }
            return def;
        },
        update_summary: function(){
            this._super();
            this.update_order();
        },
    });

    ProductListWidget.include({
        init: function() {
            this._super.apply(this, arguments);
            this.products_ids = [];
        },
        render_product: function(product){
            var def = this._super.apply(this, arguments);
            var order_lines = [];
            var current_pricelist = this._get_active_pricelist();
            var cache_key = this.calculate_cache_key(product, current_pricelist);
            var cached = this.product_cache.get_node(cache_key);
            // remove selected product
            if(cached && this.pos.get_order()){
                var data = this.pos.get_order().get_orderlines()
                _.each(data, function (line) {
                    if(cached.getAttribute("data-product-id") === product_id) {
                    }
                    order_lines.push(_.object(['id','value'],[line.product.id,line.quantity]));
                });
                var product_id = parseInt(cached.getAttribute("data-product-id"));
                if(_.contains(_.pluck(order_lines, 'id'), product_id)) {
                    var index = _.indexOf(_.pluck(order_lines, 'id'),product_id);
                    cached.classList.add('selected')
                    cached.querySelector('.product-qty').innerHTML = order_lines[index]['value'];
                }else {
                    cached.classList.remove('selected')
                    cached.querySelector('.product-qty').innerHTML = ""
                }
            }
            return def;
        },
        renderElement: function() {
            var self = this;
            this._super();
            if(this.gui.current_screen && this.pos.isMobile) {
                this.gui.current_screen.$el.removeClass('oe_leftbar');
            }
        },
    });

    PaymentScreenWidget.include({
        renderElement: function() {
            var self = this;
            this._super();
            this.$('.oe_filter').click(function() {
                self.$('.other-buttons').toggleClass('oe_hidden');
            });
            this.$('.other-buttons .button').click(function() {
                self.$('.other-buttons').addClass('oe_hidden');
            });
        },
        customer_changed: function() {
            this._super();
            var client = this.pos.get_client();
            if(client) {
                this.$('.js_customer_name').append("<i class='fa fa-user-times'>");
            }else {
                this.$('.js_customer_name').append("<i class='fa fa-user'>");
            }
        },
    });

    ClientListScreenWidget.include({
        show: function(){
            var self = this;
            this._super();
            this.$('.new-customer').click(function(){
                self.$('.screen-content').addClass('selected_client');
            });
        },
        display_client_details: function(visibility,partner,clickpos){
            this._super.apply(this, arguments);
            if (visibility === 'show') {
                this.$('.screen-content').addClass("selected_client");
            }
            else if (visibility === 'hide') {
                this.$('.screen-content').removeClass("selected_client");
            }
        },
    });

    var MobileSectionPanel = ScreenWidget.extend({
        template:'MobileSectionPanel',
        init: function(parent, options) {
            var self = this;
            this._super(parent,options);
        },
        renderElement: function() {
            this._super();
            this.update_order_list();
        },
    });

    return {
        MobileSectionPanel: MobileSectionPanel,
    };
});