/* global d2reader, Promise, DJANGO_CSRF_TOKEN, PAGE_EVENT_ID, clusiveAutosave */
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

var TOC_focusSelector = null;

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
        var click = 'javascript:d2reader.goTo({\'href\':\'' + element.href + '\'}); return false;';
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
            '<a href="' + element.href + '" ' +
            'data-cle-handler="click" ' +
            'data-cle-control="reader-navigation-toc" ' +
            'data-cle-value="toc-nav-link:' + element.href + '" ' +
            'onclick="' + click + '" ' +
            'class="' + li_class + '">' +
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

    var current = d2reader.mostRecentNavigatedTocItem;
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

    if (typeof d2reader === 'object') {
        var items = d2reader.tableOfContents;
        var has_structure = items.length > 0;
        if (!has_structure) {
            // Use title and locator to create a single entry
            items = [{
                title: document.querySelector('#tocPubTitle').innerHTML,
                href: d2reader.currentLocator.href
            }];
        }

        var out = buildTocLevel(items, 0, 'toc');
        $(TOC_EMPTY).hide();
        $(TOC_CONTAINER).html(out).CFW_Init();

        var navLinks = $(TOC_CONTAINER).find('.nav-link');
        // Add click event to update menu when new page selected
        navLinks.on('click', function(event) {
            // Accessibility addition to close TOC and move focus to selected item within the reader frame.
            // Uses click event because screen readers since they use simulated click events,
            // even if keyboard navigation is used.
            if (event) {
                var selector = event.target.getAttribute('href') || '';
                if (selector.length !== 0) {
                    TOC_focusSelector = selector;
                    $(TOC_MODAL).CFW_Modal('hide');
                }
            }

            // Use timeout delay until we can get a callback from reader
            setTimeout(function() {
                resetCurrentTocItem(false);
                markTocItemActive();
            }, 100);
        });
    } else {
        console.warn('d2reader not initialized');
    }
}

//
// Location tracking functions
//
// Readium generates frequent callbacks - on every scroll or page.
// We hold onto these in session storage, sending them to the server only once per minute.
// If user navigates to a new page, any pending final location should also be sent to the server.
//

var LOC_UPDATE_INTERVAL = 20 * 1000; // Time between server calls - once per minute, in ms.
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
            store.setItem(LOC_DATE_KEY, Date.now());
            return sendLocationToServer(book, version, locString);
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
            highlight: JSON.stringify(annotation),
            eventId: PAGE_EVENT_ID
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
    d2reader.deleteAnnotation({
        id: id
    });
    $container.html('<div class="highlight-undelete">Deleted' +
        '<a href="#" class="link-undelete link-undelete-annotation">Undo</a></div>');
    $.ajax('/library/annotation/' + id + '?eventId=' + PAGE_EVENT_ID, {
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
    d2reader.addAnnotation(annotation);
    $.ajax('/library/annotation', {
        method: 'POST',
        headers: {
            'X-CSRFToken': DJANGO_CSRF_TOKEN
        },
        data: {
            undelete: annotation.id,
            eventId: PAGE_EVENT_ID
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
    var encoded = $(this).closest('.annotation-container').data('annotation');
    // Decode base-64 encoded JSON attribute value
    var json = JSON.parse(atob(encoded));
    markAnnotationActive(json);
    d2reader.goTo(json);

    // Trigger hide modal and focus on highlight
    TOC_focusSelector = '#' + json.highlight.id;
    $(TOC_MODAL).CFW_Modal('hide');
}

// For any changes to the 'note' of an annotation, keep display text updated and invoke auto-save.
function handleNoteTextChange($container) {
    'use strict';

    var text = $container.find('textarea').val();
    $container.find('.note-content').text(text);
    var id = $container.data('annotation-id');
    // console.debug('note ', id, ' CHANGED text=', text);
    clusiveAutosave.save('/library/annotationnote/' + id, {
        note: text
    });
}

// Initialize actions for all the notes-related functionality
function setUpNotes() {
    'use strict';

    var $area = $(NOTES_CONTAINER);

    // Show edit area
    $area.on('click', 'a.note-edit-button', function(e) {
        e.preventDefault();
        console.debug('note EDIT');
        var $container = $(this).closest('.annotation-container');
        $container.find('.note-display').hide();
        $container.find('.note-edit').show();
        $container.find('.note-add-button').attr('hidden', 'true');
    });

    // Hide edit area and show static display
    $area.on('click', '.note button[type=submit]', function(e) {
        e.preventDefault();
        console.debug('note DONE');
        var $container = $(this).closest('.annotation-container');
        $container.find('.note-display').show();
        $container.find('.note-edit').hide();

        var text = $container.find('textarea').val();
        if (text === '') {
            $container.find('.note-title').hide();
            $container.find('.note-add-button').removeAttr('hidden');
            $container.find('.note-display').hide();
        }
    });

    // Delete note by setting it to empty, but stash previous value for use by undo.
    $area.on('click', '.note a.note-delete-button', function(e) {
        e.preventDefault();
        console.debug('note DELETE');
        var $container = $(this).closest('.annotation-container');
        var $textarea = $container.find('textarea');
        $container.data('deleted-note', $textarea.val());
        $textarea.val('');
        handleNoteTextChange($container);
        $container.find('.note-display').hide();
        $container.find('.note-edit').hide();
        $container.find('.note-deleted-placeholder').show();
    });

    // Undelete note by restoring old value
    $area.on('click', '.note a.link-undelete-note', function(e) {
        e.preventDefault();
        console.debug('note UNDELETE');
        var $container = $(this).closest('.annotation-container');
        var $textarea = $container.find('textarea');
        $textarea.val($container.data('deleted-note'));
        handleNoteTextChange($container);
        $container.find('.note-display').show();
        $container.find('.note-deleted-placeholder').hide();
    });

    // Watch for user changes to note text.
    $area.on('change', '.note textarea', function(e) {
        handleNoteTextChange($(e.target).closest('.annotation-container'));
    });
}

function getReaderBody() {
    'use strict';

    var readerIframe = document.querySelector('#D2Reader-Container iframe');
    var readerDocument = readerIframe.contentDocument || readerIframe.contentWindow.document;
    return readerDocument.body;
}

$(document).on('updateCurrentLocation.d2reader', function() {
    'use strict';

    if (TOC_focusSelector === null) { return; }

    var _getValidSelector = function(selector, rootElement) {
        // Split at #
        if (selector.indexOf('#') > -1) {
            selector = selector.substring(selector.indexOf('#'));
        }

        if (typeof rootElement === 'undefined') { rootElement = document; }
        try {
            return rootElement.querySelector(selector) ? selector : null;
        } catch (error) {
            return null;
        }
    };
    var readerBody = getReaderBody();
    var selector = _getValidSelector(TOC_focusSelector, readerBody);

    var updateTabindex = function(element) {
        var tabindex = null;
        if (!element.hasAttribute('tabindex')) {
            element.setAttribute('tabindex', -1);
        }
    };

    setTimeout(function() {
        // Clean hotkey-js _downKeys[]
        var eventFocus = new Event('focus');
        window.dispatchEvent(eventFocus);

        if (selector === null) {
            // No specific element - focus on body
            setTimeout(function() {
                updateTabindex(readerBody);
                setTimeout(function() {
                    readerBody.focus();
                });
            });
        } else if (selector.startsWith('#R2_HIGHLIGHT_')) {
            // Focus on highlight item
            var highlightItem = readerBody.querySelector(selector + ' .R2_CLASS_HIGHLIGHT_AREA');
            setTimeout(function() {
                highlightItem.focus();
            });
        } else {
            // Focus on content element
            var readerItem = readerBody.querySelector(selector);
            setTimeout(function() {
                updateTabindex(readerItem);
                setTimeout(function() {
                    readerItem.focus();
                });
            });
        }
    });

    TOC_focusSelector = null;
});

//  Initial setup
$(document).ready(function() {
    'use strict';

    savePendingLocationUpdate();
    setUpNotes();

    $(NOTES_CONTAINER)
        .on('click touchstart', '.delete-highlight', deleteAnnotation)
        .on('click touchstart', '.goto-highlight', goToAnnotation)
        .on('click touchstart', '.link-undelete-annotation', undeleteAnnotation);

    $(TOC_MODAL_BUTTON)
        .on('click', function() {
            TOC_focusSelector = null;
            $(TOC_MODAL_BUTTON).CFW_Modal('show');
        });

    $(TOC_MODAL)
        .on('beforeShow.cfw.modal', function() {
            resetCurrentTocItem(true);
            markTocItemActive();
        })
        .on('afterShow.cfw.modal', function() {
            scrollToCurrentTocItem();
        })
        .on('beforeHide.cfw.modal', function() {
            if (TOC_focusSelector === null) {
                $(TOC_MODAL_BUTTON).trigger('focus');
            }
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
