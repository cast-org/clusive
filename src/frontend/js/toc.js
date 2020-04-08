/* global D2Reader */
/* exported build_table_of_contents, highlight_current_toc_item, scroll_to_current_toc_item */

/*
 * Functions dealing with the Table of Contents modal.
 */

function table_of_contents_level(list, level, id) {
    'use strict';

    var out = '<ul class="nav nav-vertical">';
    list.forEach(function(element, index) {
        var toc_depth = 'toc-depth-' + level;
        var li_class = 'nav-link ' + toc_depth;
        // eslint-disable-next-line no-script-url
        var click = 'javascript:D2Reader.goTo({\'href\':\'' + element.href + '\'}); return false;';
        var twiddle = '';
        var submenu = '';
        var submenu_id = id + '_' + index;
        if (element.children) {
            twiddle = '<a href="#' +
                submenu_id +
                '" class="has-children ' +
                toc_depth +
                '" data-cfw="collapse" data-cfw-collapse-animate="false">' +
                '<span class="icon-angle-right" aria-hidden="true"></span>\n' +
                '<span class="sr-only">Toggle menu for item ' +
                element.title +
                '</span></a>';

            submenu = '<div id="' +
                submenu_id +
                '" class="collapse">' +
                table_of_contents_level(element.children, level + 1, submenu_id) +
                '</div>';
        }
        out += '<li class="nav-item">' +
            '<a href="' +
            element.href +
            '" onclick="' + click + '" class="' + li_class + '">' +
            element.title +
            '</a>' +
            twiddle +
            submenu +
            '</li>';
    });
    out += '</ul>';

    return out;
}

function build_table_of_contents() {
    'use strict';

    if (typeof D2Reader === 'object') {
        D2Reader.tableOfContents().then(function(x) {
            var out = table_of_contents_level(x, 0, 'toc');
            $('#contents_list').html(out).CFW_Init();
        });
    }
}

// This is called from reader.html
function highlight_current_toc_item() {
    'use strict';

    var current = D2Reader.mostRecentNavigatedTocItem();
    if (current.startsWith('/')) {
        current = current.substr(1);
    }
    var top = $('#contents_list');
    var elt = top.find('a[href$=\'' + current + '\']');
    // Add active class to just the selected element.
    top.find('a.active').removeClass('active');
    elt.addClass('active');
    // Open collapsers to show the current section
    elt.parents('li').children('a[data-cfw="collapse"]').CFW_Collapse('show');
}

// This is called from reader.html
function scroll_to_current_toc_item() {
    'use strict';

    var elt =  $('#contents_list').find('a.active');
    console.log('Scrolling to ', elt);
    if (elt.length > 0) {
        elt[0].scrollIntoView();
    }
}
