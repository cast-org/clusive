'use strict'

/*
Variables and functions for information about the current context
*/


$(document).ready(function () { 

    window.clusiveContext = {
        reader: {
            get window() {
                var readerIframe = $('#D2Reader-Container').find('iframe');
                var readerWindow;
                if (readerIframe.length > 0) {
                    readerWindow = readerIframe[0].contentWindow;            
                }
                return readerWindow;
            },
            get info() {
                return getReaderInfo();
            },
            get instance() {
                var readerDefined = typeof D2Reader;

                if (readerDefined !== 'undefined') {
                    return D2Reader;
                } return null;
            }
        }    
    }

    var getReaderInfo = function () {
        var readerInfo = {};
        if(clusiveContext.reader.window) {        
            // Include info from the HTML document
            readerInfo.document = {};
            readerInfo.document.title = clusiveContext.reader.window.document.title;
            readerInfo.document.baseURI = clusiveContext.reader.window.document.baseURI;
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
            if(window.sessionStorage.getItem(LOC_LOC_KEY)) {
                readerInfo.location = {}
                var locationInfoRaw = window.sessionStorage.getItem(LOC_LOC_KEY);
                var locationInfo = JSON.parse(locationInfoRaw);
                readerInfo.location.href = locationInfo.href;
                readerInfo.location.progression = locationInfo.locations.progression;
            }
        }
        return readerInfo;    
    }
});