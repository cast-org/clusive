// Basic object for speech synthesis

var clusiveTTS = {
    synth: window.speechSynthesis,
    elementsToRead: [],    
    readAloudButtonId: "#readAloudButton"
};

// Bind controls

$(document).ready(function () {
    $(clusiveTTS.readAloudButtonId).click(function (e) {
        console.log("read aloud button clicked");
        if(! clusiveTTS.synth.speaking) {
            clusiveTTS.readAll(); 
        } else if (clusiveTTS.synth.speaking) {
            clusiveTTS.stopReading();
        }
    });
});

// Stop an in-process reading

clusiveTTS.stopReading = function () {
    clusiveTTS.elementsToRead = [];
    clusiveTTS.synth.cancel();    
}

clusiveTTS.readQueuedElements = function () {
    if(clusiveTTS.elementsToRead.length > 0) {
        var toRead = clusiveTTS.elementsToRead.shift();
        clusiveTTS.readElement(toRead);            
    } else {
        console.log("Done reading elements");
    }
}

clusiveTTS.readElement = function (textElement) {
    var synth = clusiveTTS.synth;    
    var element = $(textElement);
    var contentText = element.text();
    
    // Preserve and hide the original element so we can handle the highlighting in an
    // element without markup (needs better implementation longer term)
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

    element[0].scrollIntoView();
    synth.speak(utterance);
}

clusiveTTS.readAll = function() {    
    // Cancel any active reading
    clusiveTTS.stopReading();
    clusiveTTS.readerIframe = $("#D2Reader-Container").find("iframe");
    clusiveTTS.readerBody = clusiveTTS.readerIframe.contents().find("body");

    var textElements = clusiveTTS.readerBody.find("h1,h2,h3,h4,h5,h6,p");

    $.each(textElements, function (i, e) {
        clusiveTTS.elementsToRead.push(e);
    });

    clusiveTTS.readQueuedElements();

};



