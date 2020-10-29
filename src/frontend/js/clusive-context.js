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
    }
}