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

    var autosave = {
        queue: clusive.djangoMessageQueue({
                config: {                        
                    localStorageKey: "clusive.messageQueue.autosave",
                    lastQueueFlushInfoKey: "clusive.messageQueue.autosave.log.lastQueueFlushInfo"
                }
            }),
        set: function(url, data) {
            autosave.queue.add({"type": "AS", "url": url, "data": data});
        },
        retrieve: 
            function(url, callback) {
                var hasLocal = false;
                console.log("autosave queue", autosave.queue.getMessages());
                var autosaveMessages = [].concat(autosave.queue.getMessages()).filter(function (item) {                    
                        if(item.content.type === "AS" && item.content.url === url) {
                            return true;
                        }                    
                });
                
                if(autosaveMessages.length > 0) {                    
                    var latestLocalData = JSON.parse(autosaveMessages.pop().content.data);
                    console.log("local data for url: " + url + " found");
                    callback(latestLocalData);
                } else {                   
                    console.log("No local data for url: " + url + ", trying to get from server");
                    $.get(url, function(data) {
                        console.log("Found data on server for url: " + url);
                        callback(data);                    
                    }).fail(function(error) {
                        if (error.status === 404) {
                            console.debug('No matching data on server for url: ' + url);
                        } else {
                            console.warn('failed to get data: ', error.status);
                        }
                    });
                }                 
            }                
    };


    var bookId = clusiveContext.reader.info.publication.id;

    // Block auto-show for at least 10 seconds after page load, to prevent it erroneously getting shown.
    clusiveAssessment.tooEarly = true;
    window.setTimeout(function() { clusiveAssessment.tooEarly = false; }, 10000);

    // Retrieve existing affect check values and set them

    var set_affect_check = function(data) {
        console.log("calling set_affect_check", data)
        Object.keys(data).forEach(function (key) {
            if(key.includes("affect-option")) {
                var affectOptionName = key                
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
                }
        })
    };

    autosave.retrieve('/assessment/affect_check/' + bookId, set_affect_check);

    var set_comprehension_check = function(data) {
        console.log("calling set_comprehension_check", data);
        clusiveAssessment.compCheckDone = true;
        var scaleResponse = data.scaleResponse;
        var freeResponse = data.freeResponse;
        $('textarea[name="comprehension-free"]').val(freeResponse);
        $('input[name="comprehension-scale"]').val([scaleResponse]);
        $('input[name="comprehension-scale"]').change();
    };

    autosave.retrieve('/assessment/comprehension_check/' + bookId, set_comprehension_check);

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
            
            autosave.set("/assessment/affect_check/" + bookId, JSON.stringify(affectResponse));

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

            autosave.set("/assessment/comprehension_check/" + bookId, JSON.stringify(comprehensionResponse));

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
