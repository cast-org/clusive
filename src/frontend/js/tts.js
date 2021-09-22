// There are TWO TTS systems used - Readium's built-in read-aloud functionality for the reader page,
// and the more basic clusiveTTS defined here for other pages.
//
/* eslint-disable no-use-before-define */
/* global D2Reader */

var clusiveTTS = {
    synth: window.speechSynthesis,
    elementsToRead: [],
    region: {},
    currentVoice: null,
    voiceRate: 1,
    textElement: null,
    copiedElement: null,
    autoScroll: true,
    userScrolled: false,
    readerReady: false,
    isPaused: false,
    utterance: null
};

// Bind controls
$(document).ready(function() {
    'use strict';

    // Allow play button to have toggle behavior
    $('.tts-play').on('click', function(e) {
        clusiveTTS.setRegion(e.currentTarget);

        if (clusiveTTS.region.mode === 'Readium') {
            console.debug('Readium read aloud play button clicked');
            if (!clusiveTTS.synth.speaking) {
                D2Reader.startReadAloud();
                clusiveTTS.updateUI('play');
            } else {
                D2Reader.stopReadAloud();
                clusiveTTS.updateUI('stop');
            }
        } else {
            console.debug('read aloud play button clicked');
            if (!clusiveTTS.synth.speaking) {
                clusiveTTS.resetState();
                clusiveTTS.read();
                clusiveTTS.updateUI('play');
            } else {
                clusiveTTS.stopReading();
                clusiveTTS.updateUI('stop');
            }
        }
    });

    $('.tts-stop').on('click', function(e) {
        clusiveTTS.setRegion(e.currentTarget);

        if (clusiveTTS.region.mode === 'Readium') {
            console.debug('Readium read aloud stop button clicked');
            D2Reader.stopReadAloud();
        } else {
            console.debug('read aloud stop button clicked');
            clusiveTTS.stopReading();
            // Call resetElements since some browsers do not always get the `utterance.onend` event
            clusiveTTS.resetElements();
        }
        clusiveTTS.updateUI('stop');
    });

    $('.tts-pause').on('click', function(e) {
        clusiveTTS.setRegion(e.currentTarget);

        if (clusiveTTS.region.mode === 'Readium') {
            console.debug('Readium read aloud pause button clicked');
            D2Reader.pauseReadAloud();
        } else {
            console.debug('read aloud pause button clicked');
            // Don't reset `userScrolled` here, otherwise page might jump due to async reading
            clusiveTTS.isPaused = true;
            clusiveTTS.synth.pause();
        }
        clusiveTTS.updateUI('pause');
    });

    $('.tts-resume').on('click', function(e) {
        clusiveTTS.setRegion(e.currentTarget);

        if (clusiveTTS.region.mode === 'Readium') {
            console.debug('Readium read aloud resume button clicked');
            D2Reader.resumeReadAloud();
        } else {
            console.debug('read aloud resume button clicked');
            clusiveTTS.userScrolled = false;

            // Resume by speaking utterance if one is queued
            if (clusiveTTS.utterance) {
                clusiveTTS.synth.speak(clusiveTTS.utterance);
                clusiveTTS.utterance = null;
            }
            clusiveTTS.synth.resume();
            clusiveTTS.isPaused = false;
        }
        clusiveTTS.updateUI('resume');
    });
});

window.addEventListener('unload', function() {
    'use strict';

    if (clusiveTTS.region.mode === 'Readium') {
        D2Reader.stopReadAloud();
    } else {
        clusiveTTS.stopReading();
    }
});

clusiveTTS.setRegion = function(ctl) {
    'use strict';

    var newRegion = {};
    newRegion.elm = ctl.closest('.tts-region');
    newRegion.mode = Object.prototype.hasOwnProperty.call(newRegion.elm.dataset, 'mode') ? newRegion.elm.dataset.mode : null;

    // Stop any previous region from reading
    if (Object.keys(clusiveTTS.region).length && (clusiveTTS.region.elm !== newRegion.elm)) {
        if (clusiveTTS.region.mode === 'Readium') {
            console.debug('Readium read aloud stop on region change');
            D2Reader.stopReadAloud();
        } else {
            console.debug('read aloud stop on region change');
            clusiveTTS.stopReading();
        }
        clusiveTTS.updateUI('stop');
    }

    if (clusiveTTS.region.elm !== newRegion.elm) {
        clusiveTTS.region = newRegion;
    }
};

clusiveTTS.updateUI = function(mode) {
    'use strict';

    if (!Object.keys(clusiveTTS.region).length) { return; }

    var region = clusiveTTS.region.elm;

    switch (mode) {
        case 'resume':
        case 'play': {
            region.classList.remove('paused');
            region.classList.add('active');
            break;
        }
        case 'pause': {
            region.classList.add('paused');
            region.classList.add('active');
            break;
        }
        default: {
            region.classList.remove('paused');
            region.classList.remove('active');
        }
    }
};

// Stop an in-process reading
clusiveTTS.stopReading = function(reset) {
    'use strict';

    if (typeof reset === 'undefined') { reset = true; }
    clusiveTTS.elementsToRead = [];
    if (reset) {
        clusiveTTS.scrollWatchStop();
    }
    clusiveTTS.synth.cancel();
    clusiveTTS.resetState();
    clusiveTTS.updateUI();
};

clusiveTTS.scrollWatch = function(event) {
    'use strict';

    if (event instanceof KeyboardEvent) {
        switch (event.key) {
            case 'ArrowUp':
            case 'ArrowDown': {
                clusiveTTS.userScrolled = true;
                break;
            }
            default:
                break;
        }
    } else {
        clusiveTTS.userScrolled = true;
    }
};

clusiveTTS.scrollWatchStart = function() {
    'use strict';

    clusiveTTS.userScrolled = false;
    $(document).on('wheel keydown touchmove', clusiveTTS.scrollWatch);
};

clusiveTTS.scrollWatchStop = function() {
    'use strict';

    clusiveTTS.userScrolled = false;
    $(document).off('wheel keydown touchmove', clusiveTTS.scrollWatch);
};

clusiveTTS.outerWidthMargin = function(el) {
    'use strict';

    var width = el.offsetWidth;
    var style = getComputedStyle(el);

    width += parseInt(style.marginLeft, 10) + parseInt(style.marginRight, 10);
    return width;
};

clusiveTTS.outerHeightMargin = function(el) {
    'use strict';

    var height = el.offsetHeight;
    var style = getComputedStyle(el);

    height += parseInt(style.marginTop, 10) + parseInt(style.marginBottom, 10);
    return height;
};

clusiveTTS.isVisuallyVisible = function(elem) {
    'use strict';

    return Boolean(clusiveTTS.outerWidthMargin(elem) > 0 && clusiveTTS.outerHeightMargin(elem) > 0 && elem.getClientRects().length && $(elem).outerHeight(true) > 0 && window.getComputedStyle(elem).visibility !== 'hidden');
};

clusiveTTS.isReadable = function(node) {
    'use strict';

    // if (!clusiveTTS.isVisuallyVisible(node.parentElement)) { return false; }
    if (!node.data.trim().length > 0) { return false; }
    if (/script|style|button|input|optgroup|option|select|textarea/i.test(node.parentElement.tagName)) { return false; }

    return true;
};

clusiveTTS.readQueuedElements = function() {
    'use strict';

    var toRead = null;

    while (clusiveTTS.elementsToRead.length && toRead === null) {
        toRead = clusiveTTS.elementsToRead.shift();
        if (!clusiveTTS.isVisuallyVisible(toRead.element.parentElement)) {
            toRead = null;
        }
    }

    if (typeof toRead !== 'undefined' && toRead !== null) {
        var end = toRead.end ? toRead.end : null;
        clusiveTTS.readElement(toRead.element, toRead.offset, end);
    } else {
        console.debug('Done reading elements');
        clusiveTTS.updateUI('stop');
    }
};

clusiveTTS.wrap = function(toWrap, wrapper) {
    'use strict';

    wrapper = wrapper || document.createElement('div');
    toWrap.after(wrapper);
    wrapper.appendChild(toWrap);
};

clusiveTTS.createActive = function(textElement) {
    'use strict';

    var wrapperActive = document.createElement('cttsActive');
    clusiveTTS.wrap(textElement, wrapperActive);
    clusiveTTS.copiedElement = wrapperActive;
};

clusiveTTS.updateActive = function(preceding, middle, following) {
    'use strict';

    if (clusiveTTS.copiedElement === null) {
        return;
    }

    if (!preceding.length > 0 && !middle.length > 0 && !following.length > 0) {
        return;
    }

    // Short method for reference - Research indicates using documentFragment should be faster
    // var newText = preceding + '<span class="tts-currentWord">' + middle + '</span>' + following;
    // clusiveTTS.copiedElement.innerHTML = newText;

    var newText = document.createDocumentFragment();
    var newPrefix = document.createDocumentFragment();
    var newMiddle = document.createElement('span');
    var newFollowing = document.createDocumentFragment();

    newPrefix.textContent = preceding;
    newMiddle.classList.add('tts-currentWord');
    if (typeof middle === 'object') {
        newMiddle = middle;
    } else {
        newMiddle.textContent = middle;
    }
    newFollowing.textContent = following;
    newText.append(newPrefix);
    newText.append(newMiddle);
    newText.append(newFollowing);

    while (clusiveTTS.copiedElement.firstChild) {
        clusiveTTS.copiedElement.removeChild(clusiveTTS.copiedElement.firstChild);
    }
    clusiveTTS.copiedElement.append(newText);
};

clusiveTTS.readElement = function(textElement, offset, end) {
    'use strict';

    var synth = clusiveTTS.synth;
    var elementText = textElement.textContent;
    var contentText = end ? elementText.slice(offset, end) : elementText.slice(offset);

    // Store then wrap text node so content can be replaced
    clusiveTTS.textElement = textElement;
    clusiveTTS.createActive(textElement);

    var utterance = clusiveTTS.makeUtterance(contentText);

    utterance.onboundary = function(e) {
        var preceding = '';
        var middle = '';
        var following = '';

        if (e.name === 'sentence') {
            console.debug('sentence boundary', e.charIndex, e.charLength, contentText.slice(e.charIndex, e.charIndex + e.charLength));
        }
        if (e.name === 'word') {
            console.debug('word boundary', e.charIndex, e.charLength, contentText.slice(e.charIndex, e.charIndex + e.charLength));

            // iOS/Safari does not report charLength
            if (typeof e.charLength !== 'undefined') {
                preceding = elementText.substring(0, offset + e.charIndex);
                middle = elementText.substring(offset + e.charIndex, offset + e.charIndex + e.charLength);
                following = elementText.substring(offset + e.charIndex + e.charLength);
            } else {
                // Find first word boundary after index
                var subString = e.charIndex ? elementText.substring(offset + e.charIndex) : elementText;
                var boundaryMatch = subString.match(/\s\b\S?/);
                var boundaryIndex = boundaryMatch ? boundaryMatch.index : 0;
                var textLength = subString.length;

                boundaryIndex = textLength < boundaryIndex ? textLength : boundaryIndex;

                preceding = elementText.substring(0, offset + e.charIndex);
                // middle = elementText.substring(offset + e.charIndex, offset + e.charIndex + boundaryIndex);
                following = elementText.substring(offset + e.charIndex + boundaryIndex);

                if (!boundaryMatch) {
                    middle = elementText.substring(offset + e.charIndex);
                    following = '';
                } else {
                    middle = elementText.substring(offset + e.charIndex, offset + e.charIndex + boundaryIndex);
                }
            }
        }

        clusiveTTS.updateActive(preceding, middle, following);

        // Keep current word being read in view
        if (clusiveTTS.autoScroll && !clusiveTTS.userScrolled) {
            var wordCurr = document.querySelector('.tts-currentWord');
            if (wordCurr) {
                wordCurr.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        }
    };

    utterance.onend = function() {
        console.debug('utterance ended');
        clusiveTTS.resetElements();
    };

    if (!clusiveTTS.isPaused) {
        synth.speak(utterance);
    } else {
        clusiveTTS.utterance = utterance;
    }
};

clusiveTTS.resetState = function() {
    'use strict';

    clusiveTTS.utterance = null;
    clusiveTTS.isPaused = false;
};

clusiveTTS.resetElements = function() {
    'use strict';

    console.debug('read aloud reset elements');
    // Replace current active text with stored textnode, and reset store
    if (clusiveTTS.copiedElement && clusiveTTS.textElement) {
        clusiveTTS.copiedElement.replaceWith(clusiveTTS.textElement);
    }
    clusiveTTS.copiedElement = null;
    clusiveTTS.textElement = null;
    clusiveTTS.readQueuedElements();
};

clusiveTTS.makeUtterance = function(text) {
    'use strict';

    if (typeof SpeechSynthesisUtterance === 'function') {
        var utt = new SpeechSynthesisUtterance(text);
        if (clusiveTTS.currentVoice) {
            utt.voice = clusiveTTS.currentVoice;
        }
        if (clusiveTTS.voiceRate) {
            utt.rate = clusiveTTS.voiceRate;
        }
        return utt;
    }
    console.warn('Speech synthesis unsupported by this browser');
    return null;
};

clusiveTTS.readElements = function(textElements) {
    'use strict';

    // Cancel any active reading
    clusiveTTS.stopReading(false);

    textElements.forEach(function(e) {
        clusiveTTS.elementsToRead.push(e);
    });

    clusiveTTS.readQueuedElements();
};

clusiveTTS.getAllTextElements = function(documentBody) {
    'use strict';

    var textElements = documentBody.find('h1, h2, h3, h4, h5, h6, p');
    return textElements;
};

clusiveTTS.getReadableTextNodes = function(elem) {
    'use strict';

    return clusiveTTS.getTextNodes(elem, clusiveTTS.isReadable);
};

/**
 * Gets an array of the matching text nodes contained by the specified element.
 * @param  {!Element} elem - DOM element to be traversed.
 * @param  {function(!Node,!Element):boolean} [filter]
 *     Optional function that if a true-ish value is returned will cause the
 *     text node in question to be added to the array to be returned from
 *     getTextNodes().  The first argument passed will be the text node in
 *     question while the second will be the parent of the text node.
 * @return {!Array.<!Node>} - Text nodes contained by the specified element.
 *
 * References:
 *  - https://cwestblog.com/2014/03/14/javascript-getting-all-text-nodes/
 *      - Updated to return proper DOM order.
 *  - https://developer.mozilla.org/en-US/docs/Web/API/Node/nodeType
 */
clusiveTTS.getTextNodes = function(elem, filter) {
    'use strict';

    var textNodes = [];
    if (elem) {
        var nodes = elem.childNodes;
        for (var i = nodes.length; i--;) {
            var node = nodes[i];
            var nodeType = node.nodeType;

            if (nodeType === Node.TEXT_NODE) {
                if (!filter || filter(node, elem)) {
                    textNodes.push(node);
                }
            } else if (nodeType === Node.ELEMENT_NODE || nodeType === Node.DOCUMENT_NODE || nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
                textNodes = textNodes.concat(clusiveTTS.getTextNodes(node, filter).reverse());
            }
        }
    }
    return textNodes.reverse();
};

clusiveTTS.uniqueNodeList = function(list) {
    'use strict';

    var listLen = list.length;
    var unique = [];

    for (var i = 0; i < listLen; i++) {
        if (unique.indexOf(list[i]) === -1) {
            unique.push(list[i]);
        }
    }

    return unique;
};

clusiveTTS.getReaderIFrameBody = function() {
    'use strict';

    var readerIframe = $('#D2Reader-Container').find('iframe');
    return readerIframe.contents().find('body');
};

clusiveTTS.filterReaderTextElementsBySelection = function(textElements, userSelection) {
    'use strict';

    var filteredElements = textElements.filter(function(elem) {
        return userSelection.containsNode(elem, true);
    });
    return filteredElements;
};

clusiveTTS.isSelection = function(selection) {
    'use strict';

    return !(selection.type === 'None' || selection.type === 'Caret');
};

clusiveTTS.read = function() {
    'use strict';

    var nodesToRead = clusiveTTS.getReadableTextNodes(document.querySelector('main'));
    var selection = window.getSelection();
    var isSelection = clusiveTTS.isSelection(selection);

    clusiveTTS.scrollWatchStart();
    if (isSelection) {
        clusiveTTS.readSelection(nodesToRead, selection);
    } else {
        clusiveTTS.readAll(nodesToRead);
    }
};

clusiveTTS.readAll = function(elements) {
    'use strict';

    var toRead = [];
    elements.forEach(function(elem) {
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
    'use strict';

    var filteredElements = clusiveTTS.filterReaderTextElementsBySelection(elements, selection);
    var selectionDirection = clusiveSelection.getSelectionDirection(elements, selection);
    var firstNodeOffSet;

    if (selectionDirection === clusiveSelection.directions.FORWARD) {
        firstNodeOffSet = selection.anchorOffset;
    } else if (selectionDirection === clusiveSelection.directions.BACKWARD) {
        firstNodeOffSet = selection.focusOffset;
    }

    var selectionTexts = clusiveSelection.getSelectionTextAsArray(selection);

    // Check the selectionTexts against the filteredElements text, eliminate
    // selectionTexts that don't appear in the element text (ALT text, hidden text elements, etc)
    filteredElements = filteredElements.filter(function(elem) {
        return clusiveTTS.isVisuallyVisible(elem.parentElement);
    });

    selectionTexts = selectionTexts.filter(function(selectionText) {
        var trimmed = selectionText.trim();
        var found = false;
        filteredElements.forEach(function(elem) {
            var elemText = elem.textContent;
            if (elemText.includes(trimmed)) {
                found = true;
            }
        });
        return found;
    });

    var toRead = [];
    filteredElements.forEach(function(elem, i) {
        var fromIndex = i === 0 ? firstNodeOffSet : 0;
        var selText = selectionTexts[i].trim();

        var textOffset = elem.textContent.indexOf(selText, fromIndex);

        var textEnd = selText.length;

        console.debug('textOffset/textEnd', textOffset, textEnd);

        var elementToRead = {
            element: elem,
            offset: textOffset,
            end: textOffset + textEnd
        };
        if (textOffset !==  textEnd) {
            toRead.push(elementToRead);
        }
    });

    // TODO: how to preserve ranges, while not selecting the substituted ones?
    selection.removeAllRanges();
    clusiveTTS.readElements(toRead);
};

// Return all voices known to the system for the given language.
// Language argument can be of the form "en" or "en-GB".
// If system default voice is on this list, it will be listed first.
clusiveTTS.getVoicesForLanguage = function(language) {
    'use strict';

    var voices = [];
    window.speechSynthesis.getVoices().forEach(function(voice) {
        if (voice.lang.startsWith(language)) {
            if (voice.default) {
                voices.unshift(voice); // Put system default voice at the beginning of the list
            } else {
                voices.push(voice);
            }
        }
    });
    return voices;
};

clusiveTTS.setCurrentVoice = function(name) {
    'use strict';

    // Eventually we may be able to switch voices mid-utterance, but for now have to stop speech
    clusiveTTS.stopReading();
    if (name) {
        window.speechSynthesis.getVoices().forEach(function(voice) {
            if (voice.name === name) {
                clusiveTTS.currentVoice = voice;
                if (clusiveTTS.readerReady) {
                    var voiceSpecs = {
                        usePublication: true,
                        lang: voice.lang,
                        name: voice.name
                    };
                    console.debug('setting D2Reader voice to ', voiceSpecs);
                    D2Reader.applyTTSSettings({
                        voice: voiceSpecs
                    });
                }
            }
        });
    } else {
        clusiveTTS.currentVoice = null;
        if (clusiveTTS.readerReady) {
            console.debug('Unsetting D2Reader voice');
            D2Reader.applyTTSSettings({
                voice: null
            });
        }
    }
};

clusiveTTS.readAloudSample = function() {
    'use strict';

    var utt = clusiveTTS.makeUtterance('Testing, testing, 1 2 3');
    window.speechSynthesis.speak(utt);
};

var clusiveSelection = {
    directions: {
        FORWARD: 'Forward',
        BACKWARD: 'Backward'
    }
};

clusiveSelection.getSelectionDirection = function(elements, selection) {
    'use strict';

    var selectionDirection;
    var selectionTexts = clusiveSelection.getSelectionTextAsArray(selection);

    var anchorNode = selection.anchorNode;
    var selectedAnchorText = selection.anchorNode.textContent.slice(selection.anchorOffset);

    var focusNode = selection.focusNode;
    var selectedFocusText = selection.focusNode.textContent.slice(selection.focusOffset);

    // Selection within a single element, direction can be determined by comparing anchor and focus offset
    if (anchorNode === focusNode) {
        selectionDirection = selection.anchorOffset < selection.focusOffset ? clusiveSelection.directions.FORWARD : clusiveSelection.directions.BACKWARD;
    // The first block of selection text is matched in the anchor element; forward selection
    } else if (selectedAnchorText === selectionTexts[0].trim()) {
        selectionDirection = clusiveSelection.directions.FORWARD;
    // The first block of selection text is matched in the focus element; backward selection
    } else if (selectedFocusText === selectionTexts[0].trim()) {
        selectionDirection = clusiveSelection.directions.BACKWARD;
    // Check for anchorNode / focusNode within larger elements
    } else {
        selectionDirection = elements.indexOf(anchorNode) < elements.indexOf(focusNode) ? clusiveSelection.directions.FORWARD : clusiveSelection.directions.BACKWARD;
    }

    return selectionDirection;
};

// Get the selection text as an array, splitting by the newline character
clusiveSelection.getSelectionTextAsArray = function(selection) {
    'use strict';

    return selection.toString().split(/[\n\r\t]/).filter(function(text) {
        return text.length > 1;
    });
};
