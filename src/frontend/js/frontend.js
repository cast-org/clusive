function imgCheckPortrait($img) {
    'use strict';

    var imgWidth = $img[0].naturalWidth;
    var imgHeight = $img[0].naturalHeight;
    var isPortrait = false;

    if (imgWidth / imgHeight < 1) { isPortrait = true; }

    if (isPortrait) {
        $img.addClass('is-portrait');
    }
}

// Temporary replacement for $.CFW_imageLoaded() until next
// Figuration release.
// Currently using: 4.0.0-beta.1
function isImageLoaded($img, instance, callback) {
    'use strict';

    var img = $img[0];
    var proxyImg = new Image();
    var $proxyImg = $(proxyImg);

    if (typeof instance === 'undefined') {
        instance = '';
    } else {
        instance = '.' + instance;
    }

    var _doCallback = function() {
        $proxyImg
            .off('load.cfw.imageLoaded' + instance)
            .remove();
        callback();
    };

    var _isImageComplete = function() {
        return img.complete && typeof img.naturalWidth !== 'undefined';
    };

    if (_isImageComplete() && img.naturalWidth !== 0) {
        _doCallback();
        return;
    }

    $proxyImg
        .off('load.cfw.imageLoaded' + instance)
        .one('load.cfw.imageLoaded' + instance, _doCallback);
    proxyImg.src = img.src;
}

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
            twiddle +
            '<a href="' +
            element.href +
            '" onclick="' + click + '" class="' + li_class + '">' +
            element.title +
            '</a>' +
            submenu +
            '</li>';
    });
    out += '</ul>';

    return out;
}

// eslint-disable-next-line no-undef,no-unused-vars
function build_table_of_contents() {
    'use strict';

    // eslint-disable-next-line no-undef
    if (typeof D2Reader === 'object') {
        // eslint-disable-next-line no-undef
        D2Reader.tableOfContents().then(function(x) {
            var out = table_of_contents_level(x, 0, 'toc');
            $('#contents_list').html(out).CFW_Init();
        });
    }
}

// eslint-disable-next-line no-unused-vars
function highlight_current_toc_item() {
    'use strict';

    // eslint-disable-next-line no-undef
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
    // FIXME - for some reason this is not working
    elt[0].scrollIntoView();
}

$(window).ready(function() {
    'use strict';

    var $imgs = $('.card-img img');
    for (var i = 0; i < $imgs.length; i++) {
        var $img = $($imgs[i]);

        /* eslint-disable no-loop-func */
        var callback = function() {
            imgCheckPortrait($img);
        };
        /* eslint-enable no-loop-func */

        isImageLoaded($img, i, callback);
    }
});
