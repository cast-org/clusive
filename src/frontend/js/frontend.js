/* global Masonry */
/* exported libraryMasonryEnable, libraryMasonryDisable, libraryListExpand, libraryListCollapse */

var libraryMasonryApi = null;

// Returns a function, that, as long as it continues to be invoked, will not
// be triggered. The function will be called after it stops being called for
// N milliseconds. If `immediate` is passed, trigger the function on the
// leading edge, instead of the trailing.
// By David Walsh (https://davidwalsh.name/javascript-debounce-function)
function clusiveDebounce(func, wait, immediate) {
	var timeout;
	return function() {
		var context = this, args = arguments;
		var later = function() {
			timeout = null;
			if (!immediate) func.apply(context, args);
		};
		var callNow = immediate && !timeout;
		clearTimeout(timeout);
		timeout = setTimeout(later, wait);
		if (callNow) func.apply(context, args);
	};
};

var libraryMasonryLayout = clusiveDebounce(function() {
    'use strict';

    if (libraryMasonryApi !== null) {
        libraryMasonryApi.layout();
    }
}, 150);

function libraryMasonryEnable() {
    'use strict';

    var elem = document.querySelector('.library-grid');
    libraryMasonryApi = new Masonry(elem, {
        itemSelector: '.card-library',
        columnWidth: '.card-library',
        percentPosition: true,
        transitionDuration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? '0' : '0.4s'
    });

    document.addEventListener('update.cisl.prefs', libraryMasonryLayout, { passive: true });

    var imgs = elem.querySelectorAll('img');
    imgs.forEach(function(img) {
        $.CFW_imageLoaded($(img), null, function() {
            libraryMasonryLayout();
        });
    });

    document.querySelector('.library-masonry-on').setAttribute('disabled', '');
    document.querySelector('.library-masonry-off').removeAttribute('disabled');
}

function libraryMasonryDisable() {
    'use strict';

    document.removeEventListener('update.cisl.prefs', libraryMasonryLayout);

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

function confirmationSharing() {
    'use strict';

    $(document.body).on('click', '[data-clusive="confirmSharing"]', function(e) {
        var $trigger = $(e.currentTarget);
        var $modal = $('#modalConfirm');
        var book = $trigger.data('clusive-book-id');

        if ($trigger.data('cfw') !== 'modal') {
            e.preventDefault();
            $modal.CFW_Modal('unlink');

            $.get('/library/share/' + book)
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
    confirmationSharing();
});
