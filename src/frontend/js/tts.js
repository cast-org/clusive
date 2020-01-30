var clusiveTTS = {
    synth: window.speechSynthesis,
    elementsToRead: [],    
    readAloudButtonId: "#readAloudButton",
    readAloudButtonPlayAriaLabel: "Read aloud",
    readAloudButtonStopAriaLabel: "Stop reading aloud",
    readAloudIconId: "#readAloudIcon"    
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
    $(clusiveTTS.readAloudButtonId).attr("aria-label", clusiveTTS.readAloudButtonPlayAriaLabel)
    $(clusiveTTS.readAloudIconId).toggleClass("icon-play", true);
    $(clusiveTTS.readAloudIconId).toggleClass("icon-stop", false);
};

clusiveTTS.toggleButtonToStop = function () {
    $(clusiveTTS.readAloudButtonId).attr("aria-label", clusiveTTS.readAloudButtonStopAriaLabel)
    $(clusiveTTS.readAloudIconId).toggleClass("icon-play", false);
    $(clusiveTTS.readAloudIconId).toggleClass("icon-stop", true);
};


// Stop an in-process reading

clusiveTTS.stopReading = function () {
    clusiveTTS.elementsToRead = [];
    clusiveTTS.synth.cancel();        
};

clusiveTTS.readQueuedElements = function () {
    if(clusiveTTS.elementsToRead.length > 0) {
        var toRead = clusiveTTS.elementsToRead.shift();
        clusiveTTS.readElement(toRead);            
    } else {
        console.log("Done reading elements");
        clusiveTTS.toggleButtonToPlay();
    }
};

clusiveTTS.readElement = function (textElement) {
    var synth = clusiveTTS.synth;    
    var element = $(textElement);
    var contentText = element.text();
    
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

            var preceding = contentText.substring(0, e.charIndex);
            var middle = contentText.substring(e.charIndex, e.charIndex+e.charLength);
            var following = contentText.substring(e.charIndex+e.charLength)
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
    return selection.type === "None" ? false : true;
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
    clusiveTTS.readElements(elements);

};

clusiveTTS.readSelection = function(elements, selection) {    
    var filteredElements = clusiveTTS.filterReaderTextElementsBySelection(elements, selection);
    clusiveTTS.readElements(filteredElements);
};


