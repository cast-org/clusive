/* Code for comprehension and affect assessments */
/* global clusiveContext, PAGE_EVENT_ID, DJANGO_CSRF_TOKEN, fluid */
/* exported clusiveAssessment */

var clusiveAssessment = {
    compCheckDone: false
};

clusiveAssessment.showCompCheck = function() {
    'use strict';

    clusiveAssessment.enableButton();
    if (!clusiveAssessment.compCheckDone) {
        $('#compPop').CFW_Popover('show');
    }
};

clusiveAssessment.enableButton = function() {
    'use strict';

    $('#noCompButton').hide();
    $('#compButton').show();
};

clusiveAssessment.setUpCompCheck = function() {
    'use strict';

    var bookId = clusiveContext.reader.info.publication.id;

    // Retrieve existing comprehension check values and set them
    $.get('/assessment/comprehension_check/' + bookId, function(data) {
        clusiveAssessment.enableButton();
        clusiveAssessment.compCheckDone = true;
        var scaleResponse = data.scale_response;
        var freeResponse = data.free_response;
        $('textarea[name="comprehension-free"]').val(freeResponse);
        $('input[name="comprehension-scale"]').val([scaleResponse]);
        $('input[name="comprehension-scale"]').change();
    }).fail(function(error) {
        if (error.status === 404) {
            console.debug('No pre-existing comp check response');
        } else {
            console.warn('failed to get comprehension check, status code: ', error.status);
        }
    });

    // When a radio button is selected, show the appropriate free-response prompt.
    $('input[name="comprehension-scale"]').change(
        function() {
            if ($(this).is(':checked')) {
                if ($(this).val() === '0') {
                    $('#compTextPromptYes').hide();
                    $('#compTextPromptNo').show();
                } else {
                    $('#compTextPromptYes').show();
                    $('#compTextPromptNo').hide();
                }
                $('#comprehensionFreeResponseArea').show();
            }
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
                    clusiveAssessment.compCheckDone = true;
                })
                .fail(function(err) {
                    console.error('Comp check save failed!', err);
                });
            $(this).closest('.popover').CFW_Popover('hide');
        });
};

$(function() {
    'use strict';

    $(document).ready(function() {
        // Don't set up a comp check unless on a book page
        if (fluid.get(clusiveContext, 'reader.info.publication.id')) {
            clusiveAssessment.setUpCompCheck();
        }
    });
});
