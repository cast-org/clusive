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

function imgCheckPortrait($img, useAlt) {
    'use strict';

    if (typeof useAlt === 'undefined') { useAlt = false; }
    var imgWidth = $img[0].naturalWidth;
    var imgHeight = $img[0].naturalHeight;
    var isPortrait = false;

    if (useAlt) {
        $img.removeClass('is-portrait');
        imgWidth = $img[0].width;
        imgHeight = $img[0].height;
    }

    if (imgWidth / imgHeight < 1) { isPortrait = true; }

    if (isPortrait) {
        $img.addClass('is-portrait');
    }
}

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
            .off('load.imageLoaded' + instance)
            .remove();
        callback();
    };

    var _isImageComplete = function() {
        return img.complete && typeof img.naturalWidth !== 'undefined';
    };

    // Firefox reports img.naturalWidth=0 for SVG
    // if (_isImageComplete() && img.naturalWidth !== 0) {
    if (_isImageComplete()) {
        _doCallback();
        return;
    }

    $proxyImg
        .off('load.imageLoaded' + instance)
        .one('load.imageLoaded' + instance, _doCallback);
    proxyImg.src = img.src;
}

function doPortraitCheck($img, i) {
    'use strict';

    isImageLoaded($img, i, function() {
        // Firefox reports img.naturalWidth=0 for SVG
        // Also currently borked in most browsers: https://github.com/whatwg/html/issues/3510
        if ($img[0].naturalWidth !== 0) {
            imgCheckPortrait($img, false);
        } else {
            imgCheckPortrait($img, true);
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

    var $imgs = $('.card-img img');
    for (var i = 0; i < $imgs.length; i++) {
        doPortraitCheck($($imgs[i]), i);
    }
});
