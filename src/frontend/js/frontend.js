/* global Masonry */
/* exported libraryMasonryEnable, libraryMasonryDisable, libraryListExpand, libraryListCollapse */

var libraryMasonryApi = null;

function libraryMasonryEnable() {
    'use strict';

    var elem = document.querySelector('.library-grid');
    libraryMasonryApi = new Masonry(elem, {
        itemSelector: '.card-library',
        // use element for option
        columnWidth: '.card-library',
        percentPosition: true
    });

    var imgs = elem.querySelectorAll('img');
    imgs.forEach(function(img) {
        $.CFW_imageLoaded($(img), null, function() {
            libraryMasonryApi.layout();
        });
    });
    document.querySelector('.library-masonry-on').setAttribute('disabled', '');
    document.querySelector('.library-masonry-off').removeAttribute('disabled');
}

function libraryMasonryDisable() {
    'use strict';

    if (libraryMasonryApi !== null) {
        libraryMasonryApi.destroy();
        libraryMasonryApi = null;
    }
    document.querySelector('.library-masonry-on').removeAttribute('disabled');
    document.querySelector('.library-masonry-off').setAttribute('disabled', '');
}

function libraryListExpand() {
    'use strict';

    $('.card-toggle-btn').CFW_Collapse('show');
}

function libraryListCollapse() {
    'use strict';

    $('.card-toggle-btn').CFW_Collapse('hide');
}

function confirmationPublicationDelete() {
    'use strict';

    $(document.body).on('click', '[data-clusive="confirmPubDel"]', function(e) {
        var $trigger = $(e.currentTarget);
        var $modal = $('#modalConfirm');
        var article = $trigger.data('clusive-book-id');

        if ($trigger.data('cfw') !== 'modal') {
            e.preventDefault();
            $modal.CFW_Modal('unlink');

            $.get('/library/remove/confirm/' + article)
                // eslint-disable-next-line no-unused-vars
                .done(function(data, status) {
                    $modal.find('.modal-content').html(data);
                });

            $trigger.CFW_Modal({
                target: '#modalConfirm',
                unlink: true
            });
            $trigger.CFW_Modal('show');
        }
    });
}

function formFileText() {
    'use strict';

    var formFileInputUpdate = function(node) {
        var input = node;
        var $input = $(node);

        var name = (typeof input === 'object')
            && (typeof input.files === 'object')
            && (typeof input.files[0] === 'object')
            && (typeof input.files.name === 'object')
            ? input.files[0].name : $input.val();

        name = name.split('\\').pop().split('/').pop();
        if (name === null) { name = ''; }
        if (name !== '') {
            $input.closest('.form-file').find('.form-file-text').first().text(name);
        }
    };

    $(document).on('change', '.form-file-input', function() {
        formFileInputUpdate(this);
    });
    $('.form-file-input').each(function() {
        formFileInputUpdate(this);
    });
}

$(window).ready(function() {
    'use strict';

    formFileText();
    confirmationPublicationDelete();
});
