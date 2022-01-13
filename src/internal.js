// This is the Javascript file that is injected into all R2D2BC frames.

// Reference from within the iframe to the clusivePrefs global in the parent window
var clusivePrefs = window.parent.window.clusivePrefs;

// Reference from within the iframe to the clusiveEvents global in the parent window
var clusiveEvents = window.parent.window.clusiveEvents;

// Reference from within the iframe to the clusiveAssessment global

var clusiveAssessment = window.parent.window.clusiveAssessment;

if (!window.debug) {
    console.log = function () {};
}

$(function() {
    var $body = $('body');
    // $body.on('click touchstart keydown', 'span[data-gloss]', function(e) {
    //     if (e.type === 'keydown') {
    //         // Respond to Enter and Space keys, ignore anything else.
    //         if (e.which !== 13 && e.which !== 32) {
    //             return;
    //         }
    //     }
    //     e.preventDefault();
    //     e.stopPropagation();
    //     openGlossaryForCue($(this));
    // });
    window.parent.setUpImageDetails($body);
});


// // Additional actions when popover opens
// scope.on("beforeShow.cfw.popover", "a.gloss",
//     function () {
//         var word = $(this).data("word");
//         console.log("clicked: ", word);
//         // Hide other popovers
//         scope.find("a.gloss").CFW_Popover("hide");
//         // Show other matches
//         scope.mark(word, secondaryMarkOptions);
//     });
//
// // Additional actions when popover closes
// scope.on("afterHide.cfw.popover", "a.gloss",
//     function () {
//         console.log("Closed: ", $(this).data("word"));
//         scope.unmark({ element: "span" });
//     });

// TODO: make preferences editor properly aware of page changes
if(clusivePrefs && clusivePrefs.prefsEditorLoader && clusivePrefs.prefsEditorLoader.prefsEditor) {
    console.info('getting settings')
    var prefsPromise = clusivePrefs.prefsEditorLoader.getSettings();
    prefsPromise.then(function (prefs) {
        console.debug('prefs received', prefs)
        if(prefs.preferences["cisl_prefs_glossary"]) {
            window.markCuedWords();
        }
    }, function (e) {
        console.error('error fetching prefs', e)
    })
}
