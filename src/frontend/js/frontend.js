function modalAdjust() {
    'use strict';

    var scrollbarWidth = $.CFW_measureScrollbar();
    var $items = $('.site-header, .sidebars');

    var scrollbarCheck = function() {
        var rect = document.body.getBoundingClientRect();
        return Math.round(rect.left + rect.right) < window.innerWidth;
    };

    var scrollbarSet = function() {
        if (scrollbarCheck()) {
            $items.each(function() {
                var $this = $(this);
                var actualPadding = this.style['padding-right'];
                var calculatedPadding = parseFloat($this.css('padding-right'));
                $this
                    .data('cfw.padding-dim', actualPadding)
                    .css('padding-right', calculatedPadding + scrollbarWidth + 'px');
            });
        }
    };

    var scrollbarReset = function() {
        $items.each(function() {
            var $this = $(this);
            var padding = $this.data('cfw.padding-dim');
            if (typeof padding !== 'undefined') {
                $this.css('padding-right', padding);
                $this.removeData('cfw.padding-dim');
            }
        });
    };

    $(document).on('beforeShow.cfw.modal', function() {
        scrollbarSet();
    });
    $(document).on('afterHide.cfw.modal', function() {
        scrollbarReset();
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

    function formFileInputUpdate(node) {
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
    }

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
    modalAdjust();

    var $imgs = $('.card-img img');
    for (var i = 0; i < $imgs.length; i++) {
        doPortraitCheck($($imgs[i]), i);
    }
});
