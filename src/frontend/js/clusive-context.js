/* global clusiveContext, d2reader, pub_id, pub_version, pub_version_id, manifest_path, LOC_LOC_KEY */

/*
Variables and functions for information about the current context
*/


$(document).ready(function() {
    'use strict';

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
            get pdf() {
                var readerPDF = $('#D2Reader-Container').find('#pdf-container');
                if (readerPDF.length > 0) {
                    return readerPDF;
                }
                return;
            },
            get info() {
                return getReaderInfo();
            },
            get instance() {
                if (typeof d2reader !== 'undefined') {
                    return d2reader;
                }
                return null;
            }
        }
    };

    var getReaderInfo = function() {
        var readerInfo = {};
        // Include info from the HTML document
        if (clusiveContext.reader.window) {
            readerInfo.document = {};
            readerInfo.document.title = clusiveContext.reader.window.document.title;
            readerInfo.document.baseURI = clusiveContext.reader.window.document.baseURI;
        }

        // PDF publication needs to construct the document info from various sources
        if (clusiveContext.reader.pdf && typeof d2reader !== 'undefined' && d2reader !== null) {
            readerInfo.document = {};
            var fname = d2reader.navigator.publication.Metadata.Title;
            var href = d2reader.navigator.publication.manifestUrl.href;
            readerInfo.document.title = document.querySelector('#tocPubTitle').innerHTML;
            readerInfo.document.baseURI = href.replace('manifest.json', fname);
        }

        // Include info from variables in reader.html
        if (clusiveContext.reader.window || clusiveContext.reader.pdf) {
            readerInfo.publication = {};
            if (pub_id) {
                readerInfo.publication.id = pub_id;
            }
            if (pub_version) {
                readerInfo.publication.version = pub_version;
            }
            if (pub_version_id) {
                readerInfo.publication.version_id = pub_version_id;
            }
            if (manifest_path) {
                readerInfo.publication.manifestPath = manifest_path;
            }
            if(window.sessionStorage.getItem(LOC_LOC_KEY)) {
                readerInfo.location = {};
                var locationInfoRaw = window.sessionStorage.getItem(LOC_LOC_KEY);
                var locationInfo = JSON.parse(locationInfoRaw);
                readerInfo.location.href = locationInfo.href;
                readerInfo.location.progression = locationInfo.locations.progression;
            }
        }
        return readerInfo;
    };
});
