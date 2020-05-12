/* Code for dealing with images - in particular, showing detail modals. */
/* exported setUpImageDetails */

var previousFocus; // Remember where focus was before opening modal.

function showImageInfoModal(event, src, alt, description) {
    'use strict';

    // Remember focus
    previousFocus = event.target;
    event.preventDefault();

    // Clear any old content from modal
    var modalBody = $('#image-info-modal .modal-body');
    modalBody.empty();

    // Add image to modal
    var image = new Image();
    image.src = src;
    image.alt = alt;
    image.className = 'img-fluid imgdesc-img';
    modalBody.append(image);

    modalBody.append(description);

    // Show modal
    $('#image-info-trigger').CFW_Modal('show');
}

function showImageDetails(event) {
    'use strict';

    var image = $('img', event.target.closest('figure'));
    // Adjust image src since we're moving it out of its IFrame.
    var baseURI = event.target.baseURI;
    // FIXME is eslint correct that the next line incompatible with some browsers?
    // eslint-disable-next-line compat/compat
    var src = new URL(image.attr('src'), baseURI);

    var description = $(event.target).closest('details').children().not('summary').clone();

    showImageInfoModal(event, src, image.attr('alt'), description);
}

function restoreFocus() {
    'use strict';

    if (previousFocus) {
        previousFocus.focus();
        previousFocus = null;
    } else {
        console.log('Warning: no previous focus recorded');
    }
}

// This is called when opening a book or navigating to a new resource within it.
function setUpImageDetails(scope) {
    'use strict';

    // Click event to override normal behavior of the <details> and <summary> elements.
    var details = $(scope).find('details summary');
    details.on('click', showImageDetails);
}

$(function() {
    'use strict';

    // On closing modal, restore focus
    // Normally Figuration does this automatically, but it can't navigate into the IFrame.
    $('#image-info-modal').on('afterHide.cfw.modal', restoreFocus);

    // Listen for clicks on details elements in the glossary
    $('#glossaryPop').on('click', 'details summary', showImageDetails);
});
