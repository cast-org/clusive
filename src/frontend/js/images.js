// Code for dealing with images - in particular, showing detail modals.

var previousFocus; // Remember where focus was before opening modal.

function setUpImageDetails(scope) {
    // Click event to override normal behavior of the <details> and <summary> elements.
    var details = scope.find("details summary");
    details.on('click', showImageDetails);

    // On closing modal, restore focus
    // Normally Figuration does this automatically, but it can't navigate into the IFrame.
    $('#image-info-modal').on('afterHide.cfw.modal', restoreFocus);
}

function showImageDetails (event) {
    // Remember focus
    previousFocus = event.target;

    // Clear any old content from modal
    var modalBody = $('#image-info-modal .modal-body');
    modalBody.empty();

    // Clone image and adjust URI
    var image = $('img', event.target.closest('figure')).clone();
    var baseURI = event.target.baseURI;
    console.log("Base URI", baseURI);
    image.attr('src', new URL(image.attr('src'), baseURI));
    modalBody.append(image);

    // Add description
    var description = $(event.target).closest('details').children().not('summary').clone();
    modalBody.append(description);

    // Show modal
    $('#image-info-trigger').CFW_Modal('show');
    event.preventDefault();
}

function restoreFocus() {
    if (previousFocus) {
        previousFocus.focus();
        previousFocus = null;
    } else {
        console.log("Warning: no previous focus recorded");
    }
}
