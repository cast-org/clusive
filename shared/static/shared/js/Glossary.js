// Glossary functionality

// List of glossary words
// TODO when we have user login, this would be persistent data for the user.
var userGlossary = [];

// Map of all word forms, pointing to the word in userGlossary
var alternatesMap = {};


function addToUserGlossary(listOfWords, basePath) {
    for (var i in listOfWords) {
        var item = listOfWords[i];
        if (!findGlossaryWord(item.word)) {
            console.log("New glossary word: ", item.word);
            // Item will have image paths that are relative to the basePath. Make them absolute.
            for (var f in item.images) {
                var image = item.images[f];
                image.src = makeAbsolutePath(basePath, image.src);
            }
            // Add to user's glossary
            userGlossary.push(item);
            var altForms = item.alternateForms;
            if (altForms) {
                for (var f in altForms) {
                    alternatesMap[altForms[f]] = item.word;
                }
            }
        }
    }
}

// Look up and return a word in the glossary list
function findGlossaryWord(word) {
    "use strict";
    for (var i in userGlossary) {
        if (userGlossary[i].word === word) {
            return userGlossary[i];
        }
    }
    return null;
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
    synonyms: alternatesMap,
    filter: onlyFirstMatch,
    element: "a",
    className: "gloss"
};

// Options hash for marking additional occurrences of a word
var secondaryMarkOptions = {
    accuracy : { value: "exactly", limiters: [ ".", ",", ";", ":", ")"] },
    separateWordSearch: false,
    acrossElements: true,
    synonyms: alternatesMap,
    filter: notAlreadyMarked,
    element: "span",
    className: "glossOther"
};

// Construct a callback function to be called when a match is found
function makeMarkCallbackFunction(word, iFrameContainerSelector) {
    "use strict";
    return function (node) {
        console.log("Setting up popover, word=", word);

        $(node)
            .data("word", word)
            .attr("href", "#");
        $(node).CFW_Popover({
            placement: function(tip, trigger) {
                return getPopoverPlacement(tip, trigger, iFrameContainerSelector);
            },
            container: "body",
            content: buildGlossaryPopover(word),
            html: true,
            title: word
        });
    };
}

// The offset() calculation of the trigger element is in
// relation its parent window (the iframe one)
//
// However, to properly place it we need to also account
// for the dimensions of the elements around the iframe,
// since our positional instructions are relative to the
// main document body
//
// This function is far from final, but shows some of what's
// involve (it also duplicates some things that auto placement
// does better)

function getPopoverPlacement(tip, trigger, iFrameContainerSelector) {
    var $trigger = $(trigger);
    var loc = {};
    var pos = $trigger.offset();
    var $iFrameContainer = $(iFrameContainerSelector);

    // Prevent squashing against right side
    var availableSpace = $iFrameContainer.width() - pos.left;

    // Determine current base font size
    var baseFontSize = parseInt($iFrameContainer.find("iframe").contents().find("body").css("font-size"), 10);

    // TODO: ideally CSS and code would share this information
    var popoverRemWidth = 18;

    var minWidth = baseFontSize * popoverRemWidth;
    var adjustment = 0;

    if(availableSpace < minWidth) {
        adjustment = minWidth - availableSpace;
    }

    // Account for potential shifting by the Readium
    // pagination behaviour (Readium uses CSS translates to "paginate")

    var translateValues = getTranslateValues($iFrameContainer.find("#layout-view-root"));

    loc.top = pos.top + $iFrameContainer.offset().top + $trigger.height() + translateValues.y;
    loc.left = pos.left + $iFrameContainer.offset().left - adjustment + translateValues.x;
    return loc;
}

// Function adapted from https://medium.com/building-blocks/how-to-read-out-translatex-translatey-from-an-element-with-translate3d-with-jquery-c15d2dcccc2c for getting x/y translate values from a jQuery element

function getTranslateValues (element) {
    var translateValues = {};
    var matrix = $(element).css('transform').replace(/[^0-9\-.,]/g, '').split(',');
    var x = matrix[12] || matrix[4];
    var y = matrix[13] || matrix[5];
    translateValues.x = parseInt(x);
    translateValues.y = parseInt(y);
    return translateValues;
}

function buildGlossaryPopover(word) {
    "use strict";
    var info = findGlossaryWord(word);
    var popoverHtml = "";
    var usage = info.usage ? "<p class=\"gloss-usage\">" + info.usage + "</p>" : "";
    if (info.images) {
        popoverHtml +=
            "     <div class=\"row\">" +
            "        <div class=\"col-md-6\">" +
            "           <p>" + info.definition + "</p>" + usage +
            "        </div>" +
            "        <div class=\"col-md-6\">";
        for (var i in info.images) {
            var img = info.images[i];
            popoverHtml +=
                "           <figure class=\"figure\">" +
                "              <img src=\"" + img.src + "\" class=\"figure-img img-fluid\" alt=\"" + img.alt + "\">\n" +
//                "              <figcaption class=\"figure-caption\">" + img.caption + "</figcaption>\n" +
                "           </figure>";
        }
        popoverHtml +=
            "        </div>" +
            "     </div>"; //row
    } else {
        popoverHtml +=
            "<p>" + info.definition + "</p>" + usage;
    }

    return popoverHtml;
}


// Add a popover to the first occurrence of each glossary word
// eslint-disable-next-line
function markGlossaryWords(scopeSelector, iFrameContainerSelector) {
    "use strict";
    var scope = $(scopeSelector) || $("article");

    console.log("markGlossaryWords", scope)

    for (var i in userGlossary) {
        var word = userGlossary[i].word;
        primaryMarkOptions.each = makeMarkCallbackFunction(word, iFrameContainerSelector);
        scope.mark(word, primaryMarkOptions);
    }

    // Additional actions when popover opens
    scope.on("beforeShow.cfw.popover", "a.gloss",
        function () {
            var word = $(this).data("word");
            console.log("clicked: ", word);
            // Hide other popovers
            scope.find("a.gloss").CFW_Popover("hide");
            // Show other matches
            scope.mark(word, secondaryMarkOptions);
        });

    // Additional actions when popover closes
    scope.on("afterHide.cfw.popover", "a.gloss",
        function () {
            console.log("Closed: ", $(this).data("word"));
            scope.unmark({ element: "span" });
        });
}

// eslint-disable-next-line
function unmarkGlossaryWords(scopeSelector) {
    "use strict";
    var scope = $(scopeSelector) || $("article");

    // Hide and remove any open popovers
    var popovers = scope.find("div.popover");
    popovers.hide().remove();

    for (var i in userGlossary) {
        var word = userGlossary[i].word;
        scope.unmark(word, primaryMarkOptions);
    }
}

function makeAbsolutePath(base, relative) {
    var stack = base.split("/"),
        parts = relative.split("/");
    stack.pop(); // remove current file name (or empty string)
                 // (omit if "base" is the current folder without trailing slash)
    for (var i=0; i<parts.length; i++) {
        if (parts[i] == ".")
            continue;
        if (parts[i] == "..")
            stack.pop();
        else
            stack.push(parts[i]);
    }
    return stack.join("/");
}
