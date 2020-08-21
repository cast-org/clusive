// Reference from within the iframe to the clusivePrefs global in the parent window
var clusivePrefs = window.parent.window.clusivePrefs;

window.cuedWordMap = null;

if (!window.debug) {
    console.log = function () {};
}

// Explicitly attached to "window" so that uglify won't change it and it can be called from elsewhere.
window.markCuedWords = function() {
    if (window.cuedWordMap === null) {
        $.get('/glossary/cuelist/'+window.parent.pub_id+'/'+window.parent.pub_version)
            .done(function(data, status) {
                console.debug("Received cuelist: ", data);
                window.cuedWordMap = data.words;
                markCuedWords();
            })
            .fail(function(err) {
                console.error(err);
            });
    } else {
        // "cuedWordMap" is a map from main form to a list of all forms.
        for (var main in window.cuedWordMap) {
            var alts = window.cuedWordMap[main];
            // Build up a selector that will match any of the forms of the word.
            // Something like: span[data-word='dog'],span[data-word='dogs']
            var selector = "span[data-word='"
                + alts.join("'],span[data-word='")
                + "']";
            var occurrence = $(selector).filter(':not(:header *):not(figure *)').first();
            if (occurrence) {
                // data-gloss attribute indicates that this is a glossary cue, and what the main form is.
                occurrence.attr('data-gloss', main);
                // tabindex makes it accessible to keyboard navigation
                occurrence.attr('tabindex', '0');
            } else {
                console.warn('No occurrence of glossary word found, selector=', selector);
            }
        }
    }
};

// Explicitly attached to "window" so that uglify won't change it and it can be called from elsewhere.
window.unmarkCuedWords = function() {
    document.body.querySelectorAll('[data-gloss]')
        .forEach(element => {
            element.removeAttribute('tabindex');
            element.removeAttribute('data-gloss');
        });
};

function openGlossaryForCue(elt) {
    'use strict';

    let word = $(elt).data('gloss');
    window.parent.load_definition(1, word);
    window.parent.$('#lookupIcon').CFW_Popover('show');
    console.debug('Focus reminder: ', $(elt));
    window.parent.glossaryPop_focus($(elt));
}


$(function() {
    var $body = $('body');
    $body.on('click touchstart keydown', 'span[data-gloss]', function(e) {
        if (e.type === 'keydown') {
            // Respond to Enter and Space keys, ignore anything else.
            if (e.which !== 13 && e.which !== 32) {
                return;
            }
        }
        e.preventDefault();
        e.stopPropagation();
        openGlossaryForCue($(this));
    });
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