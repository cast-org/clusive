/* global D2Reader, Promise, DJANGO_CSRF_TOKEN */
/* exported buildTableOfContents, trackReadingLocation,
   buildAnnotationList, addNewAnnotation, showExistingAnnotation */

// Some IDs are required to be used in the side modal:
var TOC_MODAL_BUTTON = '#tocButton';
var TOC_MODAL = '#modalToc';

var TOC_TAB   = '#tocTab';  // links to #tocPanel
var TOC_CONTAINER = '#tocList';
var TOC_EMPTY = '#tocEmpty';

var NOTES_TAB = '#notesTab';  // links to #notesPanel
var NOTES_CONTAINER = '#notesList';

// eslint-disable-next-line no-unused-vars
function showTocPanel() {
    'use strict';

    $(TOC_MODAL_BUTTON).CFW_Modal('show');
    $(TOC_TAB).CFW_Tab('show');
}

function showNotesPanel() {
    'use strict';

    $(TOC_MODAL_BUTTON).CFW_Modal('show');
    $(NOTES_TAB).CFW_Tab('show');
}

/*
 * Functions dealing with location tracking and the Table of Contents modal.
 */

// Create HTML for a single level of TOC structure
function buildTocLevel(list, level, id) {
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
                '" role="button" data-cfw="collapse" data-cfw-collapse-animate="false" title="Toggle sub-menu">' +
                '<span class="icon-angle-right" aria-hidden="true"></span>\n' +
                '<span class="sr-only">Toggle menu for item ' +
                element.title +
                '</span></a>';

            submenu = '<div id="' +
                submenu_id +
                '" class="collapse">' +
                buildTocLevel(element.children, level + 1, submenu_id) +
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

// Reset TOC to its base state with nothing active, and (optionally) everything collapsed
function resetCurrentTocItem(collapse) {
    'use strict';

    var top = $(TOC_CONTAINER);
    if (typeof collapse === 'undefined') {
        collapse = false;
    }

    // Remove active and current indicators from all menu items
    top.find('.active').removeClass('active');
    top.find('[aria-current]').removeAttr('aria-current');

    // Collapse any open sub-menus
    if (collapse) {
        top.find('a[data-cfw="collapse"]').CFW_Collapse('hide');
    }
}

// Called when TOC modal is opened - activates the current location
function markTocItemActive() {
    'use strict';

    var current = D2Reader.mostRecentNavigatedTocItem();
    if (current.startsWith('/')) {
        current = current.substr(1);
    }

    var top = $(TOC_CONTAINER);
    var elt = top.find('a[href$=\'' + current + '\']');

    // Add active class to current element and any related 'parent' sections
    elt.addClass('active').attr('aria-current', true);
    elt.parents('li').children('.nav-link').addClass('active');

    // Open collapsers to show the current section
    elt.parents('li').children('a[data-cfw="collapse"]').attr('aria-current', true).CFW_Collapse('show');
}

// Scroll the TOC display so that the active item can be seen.
function scrollToCurrentTocItem() {
    'use strict';

    var elt =  $(TOC_CONTAINER).find('a.active');
    console.debug('Scrolling to ', elt);
    if (elt.length > 0) {
        elt[elt.length - 1].scrollIntoView();
    }
}

// Creates TOC contents for the current book.
function buildTableOfContents() {
    'use strict';

    if (typeof D2Reader === 'object') {
        D2Reader.tableOfContents().then(function(items) {
            if (items.length > 1) {
                $(TOC_EMPTY).hide();
                var out = buildTocLevel(items, 0, 'toc');
                $(TOC_CONTAINER).html(out).CFW_Init();

                // Add click event to update menu when new page selected
                $(TOC_CONTAINER).find('.nav-link').on('click', function() {
                    // Use timeout delay until we can get a callback from reader
                    setTimeout(function() {
                        resetCurrentTocItem(false);
                        markTocItemActive();
                    }, 100);
                });
            } else {
                // Empty TOC
                $(TOC_CONTAINER).hide();
            }
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
var LOC_VERSION_KEY = 'trackReadingLocationVersion'; // Version of publication that LOC_LOC_KEY refers to.
var LOC_DATE_KEY = 'trackReadingLocationDate'; // Last time location was sent to server.

// Push data to server.  Asynchronous - returns a Promise.
function sendLocationToServer(book, version, locString) {
    'use strict';

    return $.post('/library/setlocation', {
        book: book,
        version: version,
        locator: locString
    })
        .fail(function(err) {
            console.error('Set location API failure!', err);
        });
}

function trackReadingLocation(book, version, locator) {
    'use strict';

    var store = window.sessionStorage;
    if (store) {
        // Put this location into session storage for eventual transmittal to server
        var locString = JSON.stringify(locator);
        store.setItem(LOC_BOOK_KEY, book);
        store.setItem(LOC_VERSION_KEY, version);
        store.setItem(LOC_LOC_KEY, locString);

        var storedDate = store.getItem(LOC_DATE_KEY);
        // Send to server if we haven't already sent one for this book, or last did so more than a minute ago
        if (!storedDate || storedDate < Date.now() - LOC_UPDATE_INTERVAL) {
            return sendLocationToServer(book, version, locString)
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
        var storedVersion = store.getItem(LOC_VERSION_KEY);
        if (storedLoc && storedBook) {
            return sendLocationToServer(storedBook, storedVersion, storedLoc)
                .done(function() {
                    store.removeItem(LOC_LOC_KEY);
                    store.removeItem(LOC_BOOK_KEY);
                    store.removeItem(LOC_VERSION_KEY);
                    store.removeItem(LOC_DATE_KEY);
                });
        }
    }
    return false;
}

//
// Functions dealing with the Highlights and Notes panel
//

// Indicates the given annotation as being active.
function markAnnotationActive(annotation) {
    'use strict';

    $(NOTES_CONTAINER + ' .active').removeClass('active');
    $('#annotation' + annotation.id).addClass('active');
}

// Build the HTML for the annotations display
function buildAnnotationList() {
    'use strict';

    var $annotationsContainer = $(NOTES_CONTAINER);
    $annotationsContainer.html('<p>Loading...</p>');
    return $.get('/library/annotationlist/' + window.pub_id + '/' + window.pub_version)
        .done(function(data) {
            $annotationsContainer.html(data);
        })
        .fail(function(err) {
            console.error(err);
        });
}

// Create an annotation and assign an ID for it; called by reader.html
function addNewAnnotation(annotation, pub_id, pub_version) {
    'use strict';

    return $.ajax('/library/annotation', {
        method: 'POST',
        headers: {
            'X-CSRFToken': DJANGO_CSRF_TOKEN
        },
        data: {
            book: pub_id,
            version: pub_version,
            highlight: JSON.stringify(annotation)
        }
    })
        .then(function(result) {
            annotation.id = result.id;
            console.debug('Successfully stored annotation ', result.id);

            buildAnnotationList()
                .then(function() { markAnnotationActive(annotation); });
            showNotesPanel();

            return annotation;
        })
        .fail(function(err) {
            console.error('Create annotation API failure!', err);
            return err;
        });
}

function deleteAnnotation(e) {
    'use strict';

    e.preventDefault();
    e.stopPropagation();
    var $container = $(this).closest('.annotation-container');
    var id = $container.data('annotation-id');
    console.debug('Deleting annotation: ', id);
    D2Reader.deleteAnnotation({
        id: id
    });
    $container.html('<div class="highlight-undelete">Deleted' +
        '<a href="#" class="link-undelete">Undo</a></div>');
    $.ajax('/library/annotation/' + id, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': DJANGO_CSRF_TOKEN
        }
    })
        .then(function() {
            console.debug('Server-side delete succeeded');
        })
        .fail(function(err) {
            console.error('Delete API failure: ', err);
            return err;
        });
}

function undeleteAnnotation(event) {
    'use strict';

    event.preventDefault();
    event.stopPropagation();
    var $container = $(this).closest('.annotation-container');
    var encoded = $container.data('annotation');
    var annotation = JSON.parse(atob(encoded));
    console.debug('Undeleting annotation id=', annotation.id);
    D2Reader.addAnnotation(annotation);
    $.ajax('/library/annotation', {
        method: 'POST',
        headers: {
            'X-CSRFToken': DJANGO_CSRF_TOKEN
        },
        data: {
            undelete: annotation.id
        }
    })
        .then(function() {
            console.debug('Server-side undelete succeeded');
            buildAnnotationList()
                .then(function() { markAnnotationActive(annotation); });
        })
        .fail(function(err) {
            console.error('Undelete API failure: ', err);
            return err;
        });
}

// Open sidebar showing the requested annotation. Called by reader.html
function showExistingAnnotation(annotation) {
    'use strict';

    markAnnotationActive(annotation);
    showNotesPanel();
}

// Move reading position to the selected annotation.
function goToAnnotation(event) {
    'use strict';

    event.preventDefault();
    event.stopPropagation();
    var encoded = $(this).closest('.annotation-container').data('annotation');
    // Decode base-64 encoded JSON attribute value
    var json = JSON.parse(atob(encoded));
    markAnnotationActive(json);
    D2Reader.goTo(json);

    // Check to see if we should close the TOC modal based on current browser breakpoint
    var bpVal = window.getBreakpointByName('xs');
    if (bpVal) {
        var mediaQuery = window.matchMedia('(max-width: ' + bpVal.max + ')');
        if (mediaQuery.matches) {
            $(TOC_MODAL).CFW_Modal('hide');
        }
    }
}

//  Initial setup

$(document).ready(function() {
    'use strict';

    savePendingLocationUpdate();

    $(NOTES_CONTAINER)
        .on('click touchstart', '.delete-highlight', deleteAnnotation)
        .on('click touchstart', '.goto-highlight', goToAnnotation)
        .on('click touchstart', '.link-undelete', undeleteAnnotation);

    $(TOC_MODAL)
        .on('beforeShow.cfw.modal', function() {
            resetCurrentTocItem(true);
            markTocItemActive();
        })
        .on('afterShow.cfw.modal', function() {
            scrollToCurrentTocItem();
        });

    $(TOC_TAB)
        .on('beforeShow.cfw.tab', function() {
            resetCurrentTocItem(true);
            markTocItemActive();
        })
        .on('afterShow.cfw.tab', function() {
            scrollToCurrentTocItem();
        });
});
