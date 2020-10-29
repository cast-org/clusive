'use strict'

/*
Variables and functions for information about the current context
*/

var clusiveContext = {
    get readerWindow() {
        var readerIframe = $('#D2Reader-Container').find('iframe');
        var readerWindow;
        if (readerIframe.length > 0) {
            readerWindow = readerIframe[0].contentWindow;            
        }
        return readerWindow;
    },
    get readerInfo() {
        return readerInfo();
    }    
}

var readerInfo = function () {
    var readerInfo = {};
    if(clusiveContext.readerWindow) {        
        readerInfo.document = {};
        readerInfo.document.title = clusiveContext.readerWindow.document.title;
        readerInfo.document.baseURI = clusiveContext.readerWindow.document.baseURI;
    }
    return readerInfo;    
}