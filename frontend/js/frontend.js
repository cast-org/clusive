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

// Lazy image load integration for height constraint
/*
function imgHeightConstrain() {
    'use strict';

    $('.card-img').on('afterShow.cfw.lazy', 'img', function(e) {
        var $img = $(e.currentTarget);
        imgCheckPortrait($img);
    });
}
*/

$(window).ready(function() {
    'use strict';

    /*
    imgHeightConstrain();
    */

    $('.card-img img').each(function() {
        imgCheckPortrait($(this));
    });
});
