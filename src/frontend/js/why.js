

$(window).ready(function() {
    'use strict';

    $('#switchButton').CFW_Modal({
        target: '#switchModal',
        animate: true
    });

    $('#switchModal')
        .on('beforeShow.cfw.modal', function() {
            $.get('/library/switch/' + window.pub_id + '/' + window.pub_version)
                .done(function(data) {
                    $('#switchModal .modal-dialog').html(data);
                })
                .fail(function(err) {
                    console.error(err);
                });
        });
});
