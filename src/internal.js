import MarkLoader from 'script-loader!mark.js'

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
        $(node).on('click touchstart', function(e) {
            e.preventDefault();
            e.stopPropagation();
            let word = $(this).text();
            window.parent.load_definition(1, word);
            window.parent.$('#glossaryButton').CFW_Popover('show');
        });
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

function markCuedWords(words) {
    // "words" is a map from main form to a list of all forms.
    var altmap = {};
    for (var i in words) {
        for (var alt in words[i]) {
            altmap[words[i][alt]] = i;
        }
        primaryMarkOptions['synonyms'] = altmap;
        $('body').mark(i, primaryMarkOptions);
    }
}


$(function() {
    $.get('/glossary/cuelist/'+window.parent.pub_id)
        .done(function(data, status) {
            console.log("Received cuelist: ", data);
            markCuedWords(data.words)
        })
        .fail(function(err) {
            console.log(err);
        });
    // This doesn't work on mobile since Readium intercepts the touch events and this never fires.
    // $('body').on('click touchstart', 'a.gloss', function(e) {
    //     e.preventDefault();
    //     e.stopPropagation();
    //     let word = $(this).text();
    //     console.log('clicked ', word);
    //     window.parent.load_definition(1, word);
    //     window.parent.$('#glossaryButton').CFW_Popover('show');
    // })
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
