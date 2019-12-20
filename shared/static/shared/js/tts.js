
// 1. Get reader text content
// 2. Build parallel text to elements structure

var clusiveTTS = {};

clusiveTTS.readElements = function (elems) {
    if(elems.length > 0) {
        var current = elems.shift();
        clusiveTTS.readElement(current, elems);            
    } else {
        console.log("Done processing");
    }
}

clusiveTTS.readElement = function (textElement, remainingElements) {
    var synth = window.speechSynthesis;        
    var element = $(textElement);
    var contentText = element.text();
    
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
        copiedElement.remove();
        element.show();                  
        process(remainingElements);
    }

    synth.speak(utterance);
}

clusiveTTS.start = function() {
    console.log("tts loaded");
    
    clusiveTTS.readerIframe = $("#D2Reader-Container").find("iframe");
    clusiveTTS.readerBody = clusiveTTS.readerIframe.contents().find("body");

    clusiveTTS.textElements = clusiveTTS.readerBody.find("h1,h2,h3,h4,h5,h6,p");

    textElements = [];

    $.each(clusiveTTS.textElements, function (i, e) {
        textElements.push(e);
    });

    clusiveTTS.readElements(textElements);

};



