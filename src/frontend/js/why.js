

$(window).ready(function() {
    'use strict';

    $('#whyButton').CFW_Modal({
        target: '#switchModal',
        animate: true
    });

    $('#whyWhyLink').on('click', function(e) {
        // eslint-disable-next-line no-alert
        alert('Not yet implemented');
        e.preventDefault();
    });
});
