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
