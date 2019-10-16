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

        $.CFW_imageLoaded($img, i, callback);
    }
});
