/* Code for comprehension and affect assessments */
/* global clusiveContext, PAGE_EVENT_ID, DJANGO_CSRF_TOKEN */

function setUpCompCheck() {
    'use strict';

    // When a radio button is selected, show the appropriate free-response prompt.
    $('input[name="comprehension-scale"]').change(
        function() {
            if ($(this).val() === '0') {
                $('#compTextPromptYes').hide();
                $('#compTextPromptNo').show();
            } else {
                $('#compTextPromptYes').show();
                $('#compTextPromptNo').hide();
            }
            $('#comprehensionFreeResponseArea').show();
        }
    );

    // When submit button is clicked, build JSON and send to server, close popover.
    $('#comprehensionCheckSubmit').click(
        function(e) {
            e.preventDefault();
            var scaleResponse = $('input[name="comprehension-scale"]:checked').val();
            var freeResponse = $('textarea[name="comprehension-free"]').val();
            var comprehensionResponse = {
                scaleResponse: scaleResponse,
                freeResponse: freeResponse,
                bookVersionId: clusiveContext.reader.info.publication.version_id,
                bookId: clusiveContext.reader.info.publication.id,
                eventId: PAGE_EVENT_ID
            };

            $.ajax('/assessment/comprehension_check', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': DJANGO_CSRF_TOKEN
                },
                data: JSON.stringify(comprehensionResponse)
            })
                .done(function(data) {
                    console.debug('Comp check save complete', data);
                })
                .fail(function(err) {
                    console.error('Comp check save failed!', err);
                });
            $(this).closest('.popover').CFW_Popover('hide');
        });
}

$(function() {
    'use strict';

    setUpCompCheck();
});
