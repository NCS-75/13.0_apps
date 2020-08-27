odoo.define('portal_vendor.sync_portal_vendor', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var PortalSidebar = require('portal.PortalSidebar');
var utils = require('web.utils');
var Dialog = require('web.Dialog');
var ajax = require('web.ajax');
var core = require('web.core');
var Qweb = core.qweb;
var _t = core._t;
ajax.loadXML('/sync_vendor_portal/static/src/xml/template.xml', Qweb);


publicWidget.registry.StockMoveLine = PortalSidebar.extend({
    selector: '.o_portal_shiping_sidebar',
    events: {
        'click #done_picking': '_onClickMove',
        'click #button_valid': '_onClickValidate',
        // 'change #qty_done': '_onChangeLot',
    },
     /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickValidate: function (ev) {
        var $model;
        var self = this;
        ajax.jsonRpc("/my/shiping/validate", 'call', {'order_id': $('#order_id').val()})
        .then(function(modal){
            $model = $(modal.html);
            $model.modal().show();
        });
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickMove: function (ev) {
        var $model;
        var self = this;
        ajax.jsonRpc("/detialed/operations", 'call', {'move_id': $(ev.currentTarget).data('id'), 'stock_id': $(ev.currentTarget).data('stock')})
        .then(function(modal){
            $model = $(modal.html);
            var $move = modal.move;
            var $package_ids = modal.package_ids;
            var $location_ids = modal.location_ids;
            var $is_serial_with_text = modal.is_serial_with_text;
            var $is_serial_with_selection = modal.is_serial_with_selection;
            var $is_uom = modal.is_uom;
            var $lot_ids = modal.lot_ids;
            var $uom_name = modal.uom_name;
            var $location_dest_name = modal.location_dest_name;
            $model.modal().show();
            $model.find("#add_move_line_ids").on('click', function(ev){
                var $StockMoveLine = $(Qweb.render("MoveLineRows", {
                    'rec': ($('.move_line_row').length + 1),
                    'move': $move,
                    'package_ids': $package_ids,
                    'location_ids': $location_ids,
                    'is_serial_with_text': $is_serial_with_text,
                    'is_serial_with_selection': $is_serial_with_selection,
                    'is_uom': $is_uom,
                    'uom_name': $uom_name,
                    'lot_ids': $lot_ids,
                    'location_dest_name': $location_dest_name,
                }));
                self._addMoveRow($StockMoveLine);
            });
            $model.find(".move_line_record_delete").on('click', function(ev){
                $(ev.currentTarget).parents('tr').remove();
                $('#move_limit_rec').val($('.move_line_row').length);
                $('table#move_line_info').find('tr.move_line_row').each(function (index, element) {
                    var $location_dest_id = $(element).find('.location_dest_id select');
                    var $result_package_id = $(element).find('.result_package_id select');
                    var $qty_done = $(element).find('.qty_done input');
                    $location_dest_id.attr('name', 'location_dest_id_' + (index + 1))
                    $result_package_id.attr('name', 'result_package_id_' + (index + 1))
                    $qty_done.attr('name', 'qty_done_' + (index + 1))
                });
            });
            $model.find("#lot_id").on('change', function(ev){
                var lot_id_list = []
                $('table#move_line_info').find('tr.move_line_row').each(function (index, element) {
                    lot_id_list.push($(element).find('#lot_id').val());
                    if (self.find_duplicate_in_array(lot_id_list).length > 0){
                        $(ev.currentTarget).val('');
                        self.do_notify(_t("This record already exists."), _t("You can not select same serial for multiple record."));
                    }
                });
            });
            $model.find("#lot_name").on('change', function(ev){
                var lot_id_list = []
                $('table#move_line_info').find('tr.move_line_row').each(function (index, element) {
                    lot_id_list.push($(element).find('#lot_name').val());
                    if (self.find_duplicate_in_array(lot_id_list).length > 0){
                        $(ev.currentTarget).val('');
                        self.do_notify(_t("This record already exists."), _t("You can not select same serial for multiple record."));
                    }
                });
            });
            $model.find("#qty_done").on('change', function(ev){
                if ($(ev.currentTarget).val() > 1 && $model.find("#lot_id").val() != undefined) {
                    self.do_notify(_t("Warning."), _t("You can not set done quantity greator to 1."));
                    $(ev.currentTarget).val('');
                }
                else if ($(ev.currentTarget).val() > 1 && $model.find("#lot_name").val() != undefined) {
                    self.do_notify(_t("Warning."), _t("You can not set done quantity greator to 1."));
                    $(ev.currentTarget).val('');
                }
            });
        });
    },
    /**
     * @private
     */
    _addMoveRow: function (StockMoveLine) {
        var $StockMoveLine = StockMoveLine;
        var self = this
        // var $FamilyRows = $(Qweb.render("FamilyRows", {'id': ($('.ipc_family_row').length + 1)}));
        $('.o_add_an_item_tr').before($StockMoveLine);
        $('#move_line_rec').val($('.move_line_row').length);
        $StockMoveLine.find('.move_line_record_delete span').on('click', function () {
            $(this).parents('tr').remove();
            $('#move_limit_rec').val($('.move_line_row').length);
            $('table#move_line_info').find('tr.move_line_row').each(function (index, element) {
                var $location_dest_id = $(element).find('.location_dest_id select');
                var $result_package_id = $(element).find('.result_package_id select');
                var $qty_done = $(element).find('.qty_done input');
                $location_dest_id.attr('name', 'location_dest_id_' + (index + 1))
                $result_package_id.attr('name', 'result_package_id_' + (index + 1))
                $qty_done.attr('name', 'qty_done_' + (index + 1))
            });
        });
        $StockMoveLine.find("#qty_done").on('change', function(ev) {
            if ($(ev.currentTarget).val() > 1 && $StockMoveLine.find("#lot_id").val() != undefined) {
                    self.do_notify(_t("Warning."), _t("You can not set done quantity greator to 1."));
                    $(ev.currentTarget).val('');
            }
            else if ($(ev.currentTarget).val() > 1 && $StockMoveLine.find("#lot_name").val() != undefined) {
                self.do_notify(_t("Warning."), _t("You can not set done quantity greator to 1."));
                $(ev.currentTarget).val('');
            }
        });
        $StockMoveLine.find("#lot_id").on('change', function(ev) {
            var lot_id_list = []
            $('table#move_line_info').find('tr.move_line_row').each(function (index, element) {
                lot_id_list.push($(element).find('#lot_id').val());
                if (self.find_duplicate_in_array(lot_id_list).length > 0){
                    $(ev.currentTarget).val('');
                    self.do_notify(_t("This record already exists."), _t("You can not select same serial for multiple record."));
                }
            });
        });
        $StockMoveLine.find("#lot_name").on('change', function(ev) {
            var lot_id_list = []
            $('table#move_line_info').find('tr.move_line_row').each(function (index, element) {
                lot_id_list.push($(element).find('#lot_name').val());
                if (self.find_duplicate_in_array(lot_id_list).length > 0){
                    $(ev.currentTarget).val('');
                    self.do_notify(_t("This record already exists."), _t("You can not select same serial for multiple record."));
                }
            });
        });
    },
    find_duplicate_in_array: function(arra1) {
        var object = {};
        var result = [];
        arra1.forEach(function (item) {
        if(!object[item])
                  object[item] = 0;
                object[item] += 1;
        })
        for (var prop in object) {
           if(object[prop] >= 2) {
               result.push(prop);
           }
        }
        return result;
    }
    });
});
