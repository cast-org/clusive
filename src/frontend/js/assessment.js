/* Code for comprehension and affect assessments */
/* global clusiveContext, PAGE_EVENT_ID, DJANGO_CSRF_TOKEN, fluid, D2Reader */
/* exported clusiveAssessment */

var clusiveAssessment = {
    tooEarly: true, // auto-show of popover is blocked for a few seconds after page load
    affectCheckDone: false,
    compCheckDone: false
};

clusiveAssessment.showCompCheck = function() {
    'use strict';

    if (!clusiveAssessment.compCheckDone && !clusiveAssessment.tooEarly) {
        // Set timer. Don't show comp check if user immediately moves away from the bottom.
        window.setTimeout(function() {
            D2Reader.atEnd().then(function(edge) {
                if (edge) {
                    $('#compPop').CFW_Popover('show');
                } else {
                    console.debug('Was no longer at end of resource after time delay');
                }
            });
        }, 2000);
    }
};

clusiveAssessment.setUpCompCheck = function() {
    'use strict';

    var autosaveQueue = clusive.djangoMessageQueue({
        config: {                        
            localStorageKey: "clusive.messageQueue.autosave",
            lastQueueFlushInfoKey: "clusive.messageQueue.autosave.log.lastQueueFlushInfo"
        }
    });

    var bookId = clusiveContext.reader.info.publication.id;

    // Block auto-show for at least 10 seconds after page load, to prevent it erroneously getting shown.
    clusiveAssessment.tooEarly = true;
    window.setTimeout(function() { clusiveAssessment.tooEarly = false; }, 10000);

    // Retrieve existing affect check values and set them
    $.get('/assessment/affect_check/' + bookId, function(data) {
        Object.keys(data).forEach(function (affectOptionName) {
            var shouldCheck = data[affectOptionName];
            var affectInput = $('input[name="' + affectOptionName + '"]');
            affectInput.prop("checked", shouldCheck);
            var idx = affectInput.attr("data-react-index");
            var wedge = document.querySelector('.react-wedge-' + idx);

            if(shouldCheck) {
                reactDimAnimate(wedge, 100);
            } else {
                reactDimAnimate(wedge, 0);
            }
            console.log("affectInput", affectInput, shouldCheck);
        })
    }).fail(function(error) {
        if (error.status === 404) {
            console.debug('No pre-existing affect check response');
        } else {
            console.warn('failed to get affect check, status code: ', error.status);
        }
    });

    // Retrieve existing comprehension check values and set them
    $.get('/assessment/comprehension_check/' + bookId, function(data) {
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

            // Create basic affect response structure
            var affectResponse = {
                bookVersionId: clusiveContext.reader.info.publication.version_id,
                bookId: clusiveContext.reader.info.publication.id,
                eventId: PAGE_EVENT_ID
            };

            // Get all affect inputs
            var checkedAffectInputs = $('input[name^="affect-option"]');
            // Add to data object
            checkedAffectInputs.each(function (i, elem) {
                affectResponse[elem.name] = elem.checked
            });


            autosaveQueue.add({"type": "AS", "url": "/assessment/affect_check", "data": JSON.stringify(affectResponse)});

            // $.ajax('/assessment/affect_check', {
            //     method: 'POST',
            //     headers: {
            //         'X-CSRFToken': DJANGO_CSRF_TOKEN
            //     },
            //     data: JSON.stringify(affectResponse)
            // })
            //     .done(function(data) {
            //         console.debug('Affect check save complete', data);
            //         clusiveAssessment.affectCheckDone = true;
            //     })
            //     .fail(function(err) {
            //         console.error('Affect check save failed!', err);
            //     });

            var scaleResponse = $('input[name="comprehension-scale"]:checked').val();
            var freeResponse = $('textarea[name="comprehension-free"]').val();
            var comprehensionResponse = {
                scaleQuestion: $('#compScaleQuestion').text(),
                scaleResponse: scaleResponse,
                freeQuestion: $('#compFreeQuestion').children(':visible').text(),
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
