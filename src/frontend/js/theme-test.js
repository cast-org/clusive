/* exported themeCSS */

function themeControls() {
    'use strict';

    var html = '<div style="position: fixed; bottom: .25rem; left: 50%; z-index: 2000; transform: translateX(-50%); background: #ddd; padding: 0 .5rem; border: 2px solid #666;">';
    html += '<a href="#" style="color: #009 !important;" onclick="return themeCSS();">Default</a> |';
    html += '<a href="#" style="color: #009 !important;" onclick="return themeCSS(\'sepia\');">Sepia</a> |';
    html += '<a href="#" style="color: #009 !important;" onclick="return themeCSS(\'night\');">Night</a> ';
    html += '</div>';
    $(document.body).append(html);
}

function themeCSS(name) {
    'use strict';

    var $body = $(document.body);
    if (typeof $body.attr('class') !== 'undefined') {
        $body.attr('class', function(i, c) {
            return c.replace(/(^|\s)clusive-theme-\S+/g, '');
        });
    }
    $('#themeCSS').remove();
    if (typeof name !== 'undefined') {
        $body.addClass('clusive-theme-' + name);
    }
    return false;
}

$(window).ready(function() {
    'use strict';

    themeControls();
});
