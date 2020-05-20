import MarkLoader from 'script-loader!mark.js'

// Reference from within the iframe to the clusivePrefs global in the parent window
var clusivePrefs = window.parent.window.clusivePrefs;

window.cuedWordMap = null;

if (!window.debug) {
    console.log = function () {};
}

// Filter function that, when applied as part of Mark options, only marks up the first occurrence
function onlyFirstMatch(node, term, totalCount, count) {
    "use strict";
    return count === 0;
}

// Filter function that avoids marking a word that is already marked
function notAlreadyMarked(node) {
    "use strict";
    return ($(node).closest("a.gloss").length === 0);
}

// Options hash for marking the primary occurrence of words
var primaryMarkOptions = {
    accuracy : { value: "exactly", limiters: [ ".", ",", ";", ":", ")"] },
    separateWordSearch: false,
    acrossElements: true,
    exclude: [ "h1", "h2", "h3", "h4", "h5", "h6", "figure" ],
    filter: onlyFirstMatch,
    element: "a",
    className: "gloss",
    each: function (node) {
        $(node).attr("href", "#");
    },
};

// Options hash for marking additional occurrences of a word
var secondaryMarkOptions = {
    accuracy : { value: "exactly", limiters: [ ".", ",", ";", ":", ")"] },
    separateWordSearch: false,
    acrossElements: true,
    // synonyms: alternatesMap,
    filter: notAlreadyMarked,
    element: "span",
    className: "glossOther"
};

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
        var altmap = {};        
        for (var i in window.cuedWordMap) {
            for (var alt in window.cuedWordMap[i]) {
                altmap[window.cuedWordMap[i][alt]] = i;
            }
            primaryMarkOptions['synonyms'] = altmap;
            $('body').mark(i, primaryMarkOptions);
        }
    }
};

// Explicitly attached to "window" so that uglify won't change it and it can be called from elsewhere.
window.unmarkCuedWords = function() {
    return $('body').unmark();
};


$(function() {
    var $body = $('body');
    $body.on('click touchstart', 'a.gloss', function(e) {
        e.preventDefault();
        e.stopPropagation();
        let word = $(this).text();
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