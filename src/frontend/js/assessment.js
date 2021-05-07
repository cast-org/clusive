/* Code for comprehension and affect assessments */
/* global clusive, clusiveContext, PAGE_EVENT_ID, DJANGO_CSRF_TOKEN, fluid, D2Reader */
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

clusiveAssessment.setAffectCheck = function(data) {    
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
            }
    })
}

clusiveAssessment.setComprehensionCheck = function(data) {    
    clusiveAssessment.compCheckDone = true;
    var scaleResponse = data.scaleResponse;
    var freeResponse = data.freeResponse;
    $('textarea[name="comprehension-free"]').val(freeResponse);
    $('input[name="comprehension-scale"]').val([scaleResponse]);
    if(freeResponse.length > 0) {
        $('#comprehensionFreeResponseArea').show();
    }    
}

clusiveAssessment.saveAffectCheck = function () {    
    var bookId = clusiveContext.reader.info.publication.id;
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

    clusiveAutosave.save("/assessment/affect_check/" + bookId, affectResponse);        
}

clusiveAssessment.saveComprehensionCheck = function () {        
    var bookId = clusiveContext.reader.info.publication.id;
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
    clusiveAutosave.save("/assessment/comprehension_check/" + bookId, comprehensionResponse);
}

clusiveAssessment.setupAssessments = function() {
    'use strict';
    var bookId = clusiveContext.reader.info.publication.id;

    // Block auto-show for at least 10 seconds after page load, to prevent it erroneously getting shown.
    clusiveAssessment.tooEarly = true;
    window.setTimeout(function() { clusiveAssessment.tooEarly = false; }, 10000);

    // Retrieve existing affect check values and set them
    clusiveAutosave.retrieve('/assessment/affect_check/' + bookId, clusiveAssessment.setAffectCheck);

    clusiveAutosave.retrieve('/assessment/comprehension_check/' + bookId, clusiveAssessment.setComprehensionCheck);

    // TODO: this should be an onchange on the elements
    window.setInterval(function() {
        console.log("adding current state of assessments to autosave queue")
        clusiveAssessment.saveAffectCheck();
        clusiveAssessment.saveComprehensionCheck();        
    }, 1000)

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
};

$(function() {
    'use strict';

    $(document).ready(function() {
        // Don't set up a comp check unless on a book page
        if (fluid.get(clusiveContext, 'reader.info.publication.id')) {
            clusiveAssessment.setupAssessments();
        }
    });
});
