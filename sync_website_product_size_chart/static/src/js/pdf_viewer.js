odoo.define('sync_website_product_size_chart.PdfViewer', function(require) {
"use strict";

var Dialog = require('web.Dialog');
var core = require('web.core');
var _t = core._t;
var qWeb = core.qweb;

var PdfViewer = Dialog.extend({

    xmlDependencies: (Dialog.prototype.xmlDependencies || []).concat(
        ['/sync_website_product_size_chart/static/src/xml/templates.xml']
    ),

    init: function (parent, options, resState) {
        var self = this;
        var options = _.extend({
            title: _t('Size Chart'),
            size: 'large',
            buttons: [],
            renderFooter: false,
            technical: !options.isWebsite,
        }, options || {});

        this._super(parent, options);

        this.cartQuickView = parent;
        this.dialogClass = 'oe_pdf_viewer';
        this.resState = resState;
    },

    _getPdfIframeContent() {
        return $(qWeb.render('sync_website_product_size_chart.PdfViewerIframe'));
    },

    willStart: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$modal.addClass('o_pdfviewer_modal');
            self.$content = self._getPdfIframeContent();
        });
    },

    start: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function(){
            self.$('.o_pdfviewer_iframe').attr('src', self._getURI());
        });
    },

    _getURI: function (fileURI) {
        var page = 1;
        if (!fileURI) {
            var queryString = $.param(this.resState);
            fileURI = '/web/content?' + queryString;
        }
        fileURI = encodeURIComponent(fileURI);
        var viewerURL = '/web/static/lib/pdfjs/web/viewer.html?file=';
        return viewerURL + fileURI + '#page=' + page;
    },

});

return PdfViewer;

});
