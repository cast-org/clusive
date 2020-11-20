/* exported themeCSS */

function themeControls() {
    'use strict';

    var html = '<div id="themeTest" style="position: fixed; bottom: .25rem; left: 50%; z-index: 2000; transform: translateX(-50%); background: #ddd; color: #000; padding: 0 .5rem; border: 2px solid #666; text-align: center; font-size: .875rem;">';
    html += 'Theme: ';
    html += '<a href="#" style="color: #009 !important;" onclick="return themeCSS();">Default</a> |';
    html += '<a href="#" style="color: #009 !important;" onclick="return themeCSS(\'sepia\');">Sepia</a> |';
    html += '<a href="#" style="color: #009 !important;" onclick="return themeCSS(\'night\');">Night</a> ';
    html += '</br>';
    html += 'Line height: ';
    html += '<a href="#" style="color: #009 !important;" onclick="return themeLH(1.2);">Short</a> |';
    html += '<a href="#" style="color: #009 !important;" onclick="return themeLH(1.6);">Default</a> |';
    html += '<a href="#" style="color: #009 !important;" onclick="return themeLH(2);">Tall</a>';
    html += '</div>';
    $(document.body).append(html);
    $(document.body).trigger('themeControls');
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

function themeLH(dim) {
    'use strict';

    if (typeof dim === 'undefined') {
        dim = 1.6;
    }
    document.body.style.lineHeight = dim;
    document.body.style.setProperty('--CT_lineHeight', dim);

    return false;
}

$(window).ready(function() {
    'use strict';

    themeControls();
    themeLH();
});
