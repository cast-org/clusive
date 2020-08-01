import MarkLoader from 'script-loader!mark.js'

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
            // Build up a CSS selector that will match any of the forms of the word.
            //  TODO exclude: [ "h1", "h2", "h3", "h4", "h5", "h6", "figure" ]
            var selector = '';
            for (var j in alts) {
                selector += ',span.word[data-word="' + alts[j] + '"]';
            }
            // Find and mark first occurrence of any form.  Substr removes leading comma.
            var occurrence = document.querySelector(selector.substr(1));
            if (occurrence) {
                // data-gloss attribute indicates that this is a glossary cue, and what the main form is.
                occurrence.setAttribute('data-gloss', main);
                // tabindex makes it accessible to keyboard navigation
                occurrence.setAttribute('tabindex', '0');
                // TODO is this helpful?
                occurrence.setAttribute('role', 'button');
            } else {
                console.warn('No occurrence of glossary word found, selector=', selector.substr(1));
            }
        }
    }
};

// Explicitly attached to "window" so that uglify won't change it and it can be called from elsewhere.
window.unmarkCuedWords = function() {
    return $('body').unmark();
};


$(function() {
    var $body = $('body');
    // FIXME how do we handle keyboard activation of these links as well?
    $body.on('click touchstart', 'span[data-gloss]', function(e) {
        e.preventDefault();
        e.stopPropagation();
        let word = $(this).data('gloss');
        window.parent.load_definition(1, word);
        window.parent.$('#glossaryButton').CFW_Popover('show');
        window.parent.glossaryPop_focus($(this));
    })
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