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
    },
    get readerInstance() {
        var readerDefined = typeof D2Reader;

        if (readerDefined !== 'undefined') {
            return D2Reader;
        } return null;
    }        
}

var readerInfo = function () {
    var readerInfo = {};
    if(clusiveContext.readerWindow) {        
        // Include info from the HTML document
        readerInfo.document = {};
        readerInfo.document.title = clusiveContext.readerWindow.document.title;
        readerInfo.document.baseURI = clusiveContext.readerWindow.document.baseURI;
        // Include info from variables in reader.html
        readerInfo.publication = {};
        if(pub_id) {
            readerInfo.publication.id = pub_id;
        }
        if(pub_version) {
            readerInfo.publication.version = pub_version;
        }
        if(manifest_path) {
            readerInfo.publication.manifestPath = manifest_path;
        }
    }
    return readerInfo;    
}