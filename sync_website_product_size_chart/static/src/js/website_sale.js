odoo.define('sync_website_product_size_chart.website_sale', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var WebsiteSale =  require('website_sale.website_sale');
var PdfViewer = require('sync_website_product_size_chart.PdfViewer');
var Dialog = require('web.Dialog');

var core = require('web.core');
var _t = core._t;

    var AllureWebsiteSale = _.extend({}, {

        events: _.extend({}, publicWidget.registry.WebsiteSale.prototype.events || {}, {
            'click .o_product_dimensions': '_onClickProductDimensions',
        }),

        _onClickProductDimensions: function (ev) {
            ev.preventDefault();
            var self = this;
            var productDimensionId = parseInt($(ev.currentTarget).data('product_dimension_id'), 10);
            return this._rpc({
                route: '/shop/get_product_dimension',
                params: {
                    'product_dimension_id': productDimensionId,
                },
            }).then(res => {
                if (res.mode == "pdf") {
                    self.PdfViewer = new PdfViewer(self, {
                        isWebsite: true,
                        fullscreen: true,
                        size: 'extra-large',
                    }, {
                        model: 'product.dimensions',
                        field: 'pdf_file',
                        id: productDimensionId,
                    });
                    self.PdfViewer.open();
                } else if (res.mode == "html") {
                    self.sizeChartDialog = new Dialog(self, {
                        title: _t('Size Chart'),
                        size: 'large',
                        fullscreen: true,
                        dialogClass: 'o_product_dimensions_html',
                        $content: $(res.html_content),
                        technical: false,
                        renderFooter: false,
                    });
                    self.sizeChartDialog.opened().then(function() {
                        self.sizeChartDialog.$modal.addClass('o_dimensions_modal');
                    });
                    self.sizeChartDialog.open();
                };
            });
        },
    });
    publicWidget.registry.WebsiteSale.include(AllureWebsiteSale);

});