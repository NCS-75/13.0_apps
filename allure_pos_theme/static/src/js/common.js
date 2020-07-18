$(document).ready(function () {
    var $body = $('body'),
        $width = $(document).width();
    //Mobile view detect
    if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || $width <= 991) {
        $body.addClass('ad_mobile oe_full_view');
    }
});