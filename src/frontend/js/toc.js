/* global D2Reader, Promise */
/* exported build_table_of_contents, reset_current_toc_item, highlight_current_toc_item, scroll_to_current_toc_item,
    trackReadingLocation */

/*
 * Functions dealing with location tracking and the Table of Contents modal.
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
                '" role="button" data-cfw="collapse" data-cfw-collapse-animate="false">' +
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

function reset_current_toc_item(collapse) {
    'use strict';

    var top = $('#contents_list');
    if (typeof collapse === 'undefined') {
        collapse = false;
    }

    // Remove active and current indicators from all menu items
    top.find('.nav-toc .active').removeClass('active');
    top.find('.nav-toc [aria-current]').removeAttr('aria-current');

    // Collapse any open sub-menus
    if (collapse) {
        top.find('a[data-cfw="collapse"]').CFW_Collapse('hide');
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

    // Add active class to current element and any related 'parent' sections
    elt.addClass('active').attr('aria-current', true);
    elt.parents('li').children('.nav-link').addClass('active');

    // Open collapsers to show the current section
    elt.parents('li').children('a[data-cfw="collapse"]').attr('aria-current', true).CFW_Collapse('show');
}

// This is called from reader.html
function scroll_to_current_toc_item() {
    'use strict';

    var elt =  $('#contents_list').find('a.active');
    console.log('Scrolling to ', elt);
    if (elt.length > 0) {
        elt[elt.length - 1].scrollIntoView();
    }
}

function build_table_of_contents() {
    'use strict';

    if (typeof D2Reader === 'object') {
        D2Reader.tableOfContents().then(function(x) {
            var out = table_of_contents_level(x, 0, 'toc');
            $('#contents_list').html(out).CFW_Init();

            // Add click event to update menu when new page selected
            $('#contents_list').find('.nav-link').on('click', function() {
                // Use timeout delay until we can get a callback from reader
                setTimeout(function() {
                    reset_current_toc_item(false);
                    highlight_current_toc_item();
                }, 100);
            });
        });
    }
}

//
// Location tracking functions
//
// Readium generates frequent callbacks - on every scroll or page.
// We hold onto these in session storage, sending them to the server only once per minute.
// If user navigates to a new page, any pending final location should also be sent to the server.
//

var LOC_UPDATE_INTERVAL = 60 * 1000; // Time between server calls - once per minute, in ms.
var LOC_LOC_KEY = 'trackReadingLocationLoc'; // Stores recorded location that has not yet been transmitted, if any.
var LOC_BOOK_KEY = 'trackReadingLocationBook'; // Publication that LOC_LOC_KEY refers to.
var LOC_DATE_KEY = 'trackReadingLocationDate'; // Last time location was sent to server.

// Push data to server.  Asynchronous - returns a Promise.
function sendLocationToServer(book, locString) {
    'use strict';

    return $.post('/library/setlocation', {
        book: book,
        locator: locString
    })
        .fail(function(err) {
            console.log('Set location API failure!', err);
        });
}

function trackReadingLocation(book, locator) {
    'use strict';

    var store = window.sessionStorage;
    if (store) {
        // Put this location into session storage for eventual transmittal to server
        var locString = JSON.stringify(locator);
        store.setItem(LOC_BOOK_KEY, book);
        store.setItem(LOC_LOC_KEY, locString);

        var storedDate = store.getItem(LOC_DATE_KEY);
        // Send to server if we haven't already sent one for this book, or last did so more than a minute ago
        if (!storedDate || storedDate < Date.now() - LOC_UPDATE_INTERVAL) {
            return sendLocationToServer(book, locString)
                .done(function() {
                    store.setItem(LOC_DATE_KEY, Date.now());
                });
        }
    }
    // eslint-disable-next-line compat/compat
    return Promise.resolve();
}

// If there is a location update waiting in sessionStorage, send it to server.
// Called at page load to capture final location if you left the reading page.
function savePendingLocationUpdate() {
    'use strict';

    var store = window.sessionStorage;
    if (store) {
        var storedLoc = store.getItem(LOC_LOC_KEY);
        var storedBook = store.getItem(LOC_BOOK_KEY);
        if (storedLoc && storedBook) {
            return sendLocationToServer(storedBook, storedLoc)
                .done(function() {
                    store.removeItem(LOC_LOC_KEY);
                    store.removeItem(LOC_BOOK_KEY);
                    store.removeItem(LOC_DATE_KEY);
                });
        }
    }
    return false;
}

$(document).ready(function() {
    'use strict';

    savePendingLocationUpdate();
});
