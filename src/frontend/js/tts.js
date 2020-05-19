var clusiveTTS = {
    synth: window.speechSynthesis,
    elementsToRead: [],
    readAloudButtonId: "#readAloudButton",
    readAloudButtonPlayAriaLabel: "Read aloud",
    readAloudButtonStopAriaLabel: "Stop reading aloud",
    readAloudIconId: "#readAloudIcon",
    readAloudSrTextId: "#readAloudSrText",
};

// Bind controls

$(document).ready(function () {
    $(clusiveTTS.readAloudButtonId).click(function (e) {
        console.log("read aloud button clicked");
        if(! clusiveTTS.synth.speaking) {
            clusiveTTS.toggleButtonToStop();
            clusiveTTS.read();
            // clusiveTTS.readAll();
        } else if (clusiveTTS.synth.speaking) {
            clusiveTTS.toggleButtonToPlay();
            clusiveTTS.stopReading();
        }
    });
});

clusiveTTS.toggleButtonToPlay = function () {
    $(clusiveTTS.readAloudButtonId).attr({
        "aria-label": clusiveTTS.readAloudButtonPlayAriaLabel,
        "title": clusiveTTS.readAloudButtonPlayAriaLabel
    });
    $(clusiveTTS.readAloudIconId).toggleClass("icon-play", true);
    $(clusiveTTS.readAloudIconId).toggleClass("icon-stop", false);
    $(clusiveTTS.readAloudSrTextId).text(readAloudButtonPlayAriaLabel);
};

clusiveTTS.toggleButtonToStop = function () {
    $(clusiveTTS.readAloudButtonId).attr({
        "aria-label": clusiveTTS.readAloudButtonStopAriaLabel,
        "title": clusiveTTS.readAloudButtonStopAriaLabel
    });
    $(clusiveTTS.readAloudIconId).toggleClass("icon-play", false);
    $(clusiveTTS.readAloudIconId).toggleClass("icon-stop", true);
    $(clusiveTTS.readAloudSrTextId).text(readAloudButtonStopAriaLabel);
};


// Stop an in-process reading

clusiveTTS.stopReading = function () {
    clusiveTTS.elementsToRead = [];
    clusiveTTS.synth.cancel();
};

clusiveTTS.readQueuedElements = function () {
    if(clusiveTTS.elementsToRead.length > 0) {
        var toRead = clusiveTTS.elementsToRead.shift();
        var end = toRead.end ? toRead.end : null;
        clusiveTTS.readElement(toRead.element, toRead.offset, end);
    } else {
        console.log("Done reading elements");
        clusiveTTS.toggleButtonToPlay();
    }
};

clusiveTTS.readElement = function (textElement, offset, end) {
    var synth = clusiveTTS.synth;
    var element = $(textElement);
    var elementText = element.text();
    var contentText = end ? element.text().slice(offset, end) : element.text().slice(offset);

    // Preserve and hide the original element so we can handle the highlighting in an
    // element without markup
    // TODO: this needs improved implementation longer term
    var copiedElement = element.clone(false);
    element.after(copiedElement);
    element.hide();
    var utterance = new SpeechSynthesisUtterance(contentText);

    utterance.onboundary = function (e) {
        if(e.name === "sentence") {
            console.log("sentence boundary", e.charIndex, e.charLength, contentText.slice(e.charIndex, e.charIndex + e.charLength));
        }
        if(e.name === "word") {
            console.log("word boundary", e.charIndex, e.charLength, contentText.slice(e.charIndex, e.charIndex + e.charLength));

            var preceding = elementText.substring(0, offset+e.charIndex);
            var middle = elementText.substring(offset+e.charIndex, offset+e.charIndex+e.charLength);
            var following = elementText.substring(offset+e.charIndex+e.charLength)
            var newText = preceding + "<span class='tts-currentWord'>" + middle + "</span>" + following;

            copiedElement.html(newText);
        }
    }

    utterance.onend = function (e) {
        console.log("utterance ended");
        copiedElement.remove();
        element.show();
        clusiveTTS.readQueuedElements();
    }

    synth.speak(utterance);
};

clusiveTTS.readElements = function(textElements) {
    // Cancel any active reading
    clusiveTTS.stopReading();

    $.each(textElements, function (i, e) {
        clusiveTTS.elementsToRead.push(e);
    });

    clusiveTTS.readQueuedElements();
};

clusiveTTS.getAllTextElements = function(documentBody) {
    var textElements = documentBody.find("h1,h2,h3,h4,h5,h6,p");
    return textElements;
};

clusiveTTS.getReaderIFrameBody = function() {
    var readerIframe = $("#D2Reader-Container").find("iframe");
    return readerIframe.contents().find("body");
};

clusiveTTS.getReaderIframeSelection = function() {
    return $("#D2Reader-Container").find("iframe")[0].contentWindow.getSelection();
}

clusiveTTS.filterReaderTextElementsBySelection = function (textElements, userSelection) {
    var filteredElements = textElements.filter(function (i, elem) {
        return userSelection.containsNode(elem, true);
    });
    return filteredElements;
};

clusiveTTS.isSelection = function (selection) {
    return selection.type === "None" || selection.type === "Caret" ? false : true;
};

clusiveTTS.read = function() {
    var isReader = $("#D2Reader-Container").length > 0;
    var elementsToRead;
    var selection, isSelection;

    if(isReader) {
        elementsToRead = clusiveTTS.getAllTextElements(clusiveTTS.getReaderIFrameBody());
        selection = clusiveTTS.getReaderIframeSelection();
    } else {
        elementsToRead = clusiveTTS.getAllTextElements($("body"));
        selection = window.getSelection();
    }

    isSelection = clusiveTTS.isSelection(selection);

    if(isSelection) {
        clusiveTTS.readSelection(elementsToRead, selection);
    } else {
        clusiveTTS.readAll(elementsToRead);
    }

};

clusiveTTS.readAll = function(elements) {

    var toRead = [];
    $.each(elements, function(i, elem) {
        var elementToRead = {
            element: elem,
            offset: 0
        };
        toRead.push(elementToRead);
    });

    clusiveTTS.readElements(toRead);

};

// TODO: this needs refactoring to (among other things) extract the Selection-related functions
// for general usage
clusiveTTS.readSelection = function(elements, selection) {
    var filteredElements = clusiveTTS.filterReaderTextElementsBySelection(elements, selection);

    var selectionDirection = clusiveSelection.getSelectionDirection(selection, selectionTexts);

    var firstNodeOffSet;

    if(selectionDirection === clusiveSelection.directions.FORWARD) {
        firstNodeOffSet = selection.anchorOffset;
    } else if(selectionDirection === clusiveSelection.directions.BACKWARD) {
        firstNodeOffSet = selection.focusOffset;
    };

    var selectionTexts = clusiveSelection.getSelectionTextAsArray(selection);

    // Check the selectionTexts against the filteredElements text, eliminate
    // selectionTexts that don't appear in the element text (ALT text, hidden text elements, etc)

    selectionTexts = selectionTexts.filter(function (selectionText, i) {
        var trimmed = selectionText.trim();
        var found = false;
        $.each(filteredElements, function (i, elem) {
            var elemText = $(elem).text();
            if(elemText.includes(trimmed)) {
                found = true;
            };
        });
        return found;
    });

    var toRead = [];
    $.each(filteredElements, function(i, elem) {
        var fromIndex = (i===0) ? firstNodeOffSet : 0;
        var selText = selectionTexts[i].trim();

        var textOffset = $(elem).text().indexOf(selText, fromIndex);

        var textEnd = selText.length;

        console.log("textOffset/textEnd", textOffset, textEnd);

        var elementToRead = {
            element: elem,
            offset: textOffset,
            end: textOffset+textEnd
        };
        toRead.push(elementToRead);

    });
    // TODO: how to preserve ranges, while not selecting the substituted ones?
    selection.removeAllRanges();
    clusiveTTS.readElements(toRead);
};



var clusiveSelection = {
    directions: {
        FORWARD: "Forward",
        BACKWARD: "Backward",
        UNCERTAIN: "Uncertain"
    }
};

clusiveSelection.getSelectionDirection = function (selection) {

    var selectionDirection;
    var selectionTexts = clusiveSelection.getSelectionTextAsArray(selection);

    var anchorNode = selection.anchorNode;
    var selectedAnchorText = selection.anchorNode.textContent.slice(selection.anchorOffset);

    var focusNode = selection.focusNode;
    var selectedFocusText = selection.focusNode.textContent.slice(selection.focusOffset);

    // Selection within a single element, direction can be determined by comparing anchor and focus offset
    if(anchorNode.textContent === focusNode.textContent) {
        selectionDirection = selection.anchorOffset < selection.focusOffset ? clusiveSelection.directions.FORWARD : clusiveSelection.directions.BACKWARD;
    // The first block of selection text is matched in the anchor element; forward selection
    } else if(selectedAnchorText === selectionTexts[0].trim()) {
        selectionDirection = clusiveSelection.directions.FORWARD;
    // The first block of selection text is matched in the focus element; backward selection
    } else if(selectedFocusText === selectionTexts[0].trim()) {
        selectionDirection = clusiveSelection.directions.BACKWARD;
    // This should eventually be eliminated as other scenarios get covered
    // TODO: check for anchorText / focusText within larger elements - might be divided by inline tags, etc
    } else selectionDirection = clusiveSelection.directions.UNCERTAIN;

    return selectionDirection;
};

// Get the selection text as an array, splitting by the newline character
clusiveSelection.getSelectionTextAsArray = function (selection) {
    return selection.toString().split("\n").filter(function (text) {
        return text.length > 1;
    });
};