// There are TWO TTS systems used - Readium's built-in read-aloud functionality for the reader page,
// and the more basic clusiveTTS defined here for other pages.
//
/* eslint-disable no-use-before-define */
/* global clusiveDebounce, d2reader */

// Initialize voices to trigger async update, so when it is called later
// a list is returned (re: Chrome/Android)
if (typeof window.speechSynthesis === 'object') {
    window.speechSynthesis.getVoices();
}

var ATTRIBUTE_FORCE_READ = 'ra-read';

var clusiveTTS = {
    synth: window.speechSynthesis,
    elementsToRead: [],
    region: {},
    voiceCurrent: null,
    voiceLocal: null,
    voiceRate: 1,
    textElement: null,
    copiedElement: null,
    autoScroll: true,
    userScrolled: false,
    readerReady: false,
    isPaused: false,
    currentQueueItem: null,
    utterance: null,
    isReadingState: false,
    isPausedState: false
};

// Bind controls
$(document).ready(function() {
    'use strict';

    // Allow play button to have toggle behavior
    $(document).on('click', '.tts-play', function(e) {
        clusiveTTS.toggle(e);
    });

    $(document).on('click', '.tts-stop', function() {
        clusiveTTS.stop();
    });

    $(document).on('click', '.tts-pause', function() {
        clusiveTTS.pause();
    });

    $(document).on('click', '.tts-resume', function() {
        clusiveTTS.resume();
    });
});

window.addEventListener('unload', function() {
    'use strict';

    clusiveTTS.stopReadingDetermineApi();
});

// Stop reading if active region is in dialog being closed
$(document).on('beforeHide.cfw.modal beforeHide.cfw.popover', function(event) {
    'use strict';

    var dialogElem = null;

    if (event.isDefaultPrevented()) { return; }
    if (event.namespace === 'cfw.popover') {
        dialogElem = $(event.target).data('cfw.popover').$target[0];
    } else {
        dialogElem = event.target;
    }

    if (dialogElem && dialogElem.contains(clusiveTTS.region.elm)) {
        clusiveTTS.stopReadingDetermineApi();
    }
});

clusiveTTS.getSelectorFromElement = function(element) {
    'use strict';

    var selector = element.getAttribute('data-ctts-target');

    if (!selector || selector === '#') {
        var hrefAttr = element.getAttribute('href');

        // Valid selector could be ID or class
        if (!hrefAttr || (!hrefAttr.includes('#') && !hrefAttr.startsWith('.'))) {
            return null;
        }

        // Just in case of a full URL with the anchor appended
        if (hrefAttr.includes('#') && !hrefAttr.startsWith('#')) {
            hrefAttr = '#' + hrefAttr.split('#')[1];
        }

        selector = hrefAttr && hrefAttr !== '#' ? hrefAttr.trim() : null;
    }

    try {
        return document.querySelector(selector) ? selector : null;
    } catch (error) {
        return null;
    }
};

clusiveTTS.isElement = function(item) {
    'use strict';

    if (!item || typeof item !== 'object') {
        return false;
    }

    if (typeof item.jquery !== 'undefined') {
        item = item[0];
    }

    return typeof item.nodeType !== 'undefined';
};

clusiveTTS.getElement = function(item) {
    'use strict';

    // it's a jQuery object or a node element
    if (clusiveTTS.isElement(item)) {
        return item.jquery ? item[0] : item;
    }

    if (typeof item === 'string' && item.length > 0) {
        return document.querySelector(item);
    }

    return null;
};

clusiveTTS.setRegion = function(ctl) {
    'use strict';

    var newRegion = {};
    newRegion.elm = ctl.closest('[role="region"]');
    newRegion.mode = Object.prototype.hasOwnProperty.call(newRegion.elm.dataset, 'ttsMode') ? newRegion.elm.dataset.ttsMode : null;

    // Stop any previous region from reading
    if (Object.keys(clusiveTTS.region).length && (clusiveTTS.region.elm !== newRegion.elm)) {
        clusiveTTS.stopReadingDetermineApi();
        clusiveTTS.updateUI('stop');
    }

    if (clusiveTTS.region.elm !== newRegion.elm) {
        clusiveTTS.region = newRegion;
    }
};

clusiveTTS.updateUI = function(mode) {
    'use strict';

    // Update sidebar and dialog controls
    var controls = document.querySelectorAll('.sidebar-tts, .dialog-tts');
    controls.forEach(function(region) {
        clusiveTTS.updateUIRegion(mode, region);
    });
};

clusiveTTS.updateUIRegion = function(mode, region) {
    'use strict';

    switch (mode) {
        case 'resume':
        case 'play': {
            clusiveTTS.isReadingState = true;
            clusiveTTS.isPausedState = false;
            region.classList.remove('paused');
            region.classList.add('active');
            break;
        }
        case 'pause': {
            clusiveTTS.isReadingState = true;
            clusiveTTS.isPausedState = true;
            region.classList.add('paused');
            region.classList.add('active');
            break;
        }
        default: {
            clusiveTTS.isReadingState = false;
            clusiveTTS.isPausedState = false;
            region.classList.remove('paused');
            region.classList.remove('active');
        }
    }
};

clusiveTTS.stopReadingDetermineApi = function() {
    'use strict';

    if (clusiveTTS.region.mode === 'Readium') {
        console.debug('Readium read aloud stop called');
        d2reader.stopReadAloud();
    } else {
        console.debug('read aloud stop called');
        clusiveTTS.stopReading();
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
    clusiveTTS.resetHighlight();
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

    if (!elem) {
        return false;
    }
    // Special case to keep element as readable
    if (elem.hasAttribute(ATTRIBUTE_FORCE_READ)) {
        return true;
    }
    return Boolean(clusiveTTS.outerWidthMargin(elem) > 0 && clusiveTTS.outerHeightMargin(elem) > 0 && elem.getClientRects().length && $(elem).outerHeight(true) > 0 && window.getComputedStyle(elem).visibility !== 'hidden');
};

clusiveTTS.isReadable = function(node) {
    'use strict';

    var element = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;

    // if (!clusiveTTS.isVisuallyVisible(element)) { return false; }
    if (!node.data.trim().length > 0) { return false; }
    if (/script|style|button|input|optgroup|option|select|textarea/i.test(element.tagName)) { return false; }
    if (element.closest('[aria-hidden="true"]')) { return false; }

    return true;
};

clusiveTTS.readQueuedElements = function() {
    'use strict';

    var toRead = null;

    while (clusiveTTS.elementsToRead.length && toRead === null) {
        toRead = clusiveTTS.elementsToRead.shift();
        // Check for hidden - allows items shown mid-read to be included
        if (!clusiveTTS.isVisuallyVisible(toRead.element.parentElement)) {
            toRead = null;
        }
    }

    if (typeof toRead !== 'undefined' && toRead !== null) {
        var end = toRead.end ? toRead.end : null;
        clusiveTTS.readElement(toRead.element, toRead.offset, end);
    } else {
        console.debug('Done reading elements');
        clusiveTTS.resetState();
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

clusiveTTS.onEnd = function() {
    'use strict';

    clusiveTTS.utterance = null;
    if (!clusiveTTS.isPaused) {
        clusiveTTS.resetHighlight();
        clusiveTTS.readQueuedElements();
    }
};

clusiveTTS.readElement = clusiveDebounce(function(textElement, offset, end) {
    'use strict';

    var synth = clusiveTTS.synth;
    var elementText = textElement.textContent;
    var contentText = end ? elementText.slice(offset, end) : elementText.slice(offset);

    // Store then wrap text node so content can be replaced
    clusiveTTS.resetHighlight();
    clusiveTTS.textElement = textElement;
    clusiveTTS.createActive(textElement);

    // Determine any localized voice
    var langIso = clusiveTTS.getLangAttribute(textElement);
    console.debug('langIso', langIso);
    var langVoices = clusiveTTS.getVoicesForLanguage(langIso);
    clusiveTTS.voiceLocal = langVoices.length > 0 ? langVoices[0] : null;
    clusiveTTS.utterance = clusiveTTS.makeUtterance(contentText);

    clusiveTTS.utterance.onboundary = function(e) {
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

        clusiveTTS.currentQueueItem = {
            element: textElement,
            offset: offset + e.charIndex,
            end: end
        };

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

    clusiveTTS.utterance.onend = function() {
        console.debug('utterance ended');
        clusiveTTS.onEnd();
    };

    if (!clusiveTTS.isPaused) {
        synth.speak(clusiveTTS.utterance);
        clusiveTTS.updateUI('play');
    }

    if (!synth.speaking) {
        synth.resume();
        clusiveTTS.updateUI('resume');
    }
}, 100);

clusiveTTS.resetState = function() {
    'use strict';

    clusiveTTS.currentQueueItem = null;
    clusiveTTS.utterance = null;
    clusiveTTS.isPaused = false;
};

clusiveTTS.resetHighlight = function() {
    'use strict';

    console.debug('read aloud reset highlight');
    // Replace current active text with stored textnode, and reset store
    if (clusiveTTS.copiedElement && clusiveTTS.textElement) {
        clusiveTTS.copiedElement.replaceWith(clusiveTTS.textElement);
    }
    clusiveTTS.copiedElement = null;
    clusiveTTS.textElement = null;
};

clusiveTTS.makeUtterance = function(text) {
    'use strict';

    if (typeof SpeechSynthesisUtterance === 'function') {
        var utt = new SpeechSynthesisUtterance(text);
        if (clusiveTTS.voiceLocal) {
            utt.voice = clusiveTTS.voiceLocal;
        } else if (clusiveTTS.voiceCurrent) {
            utt.voice = clusiveTTS.voiceCurrent;
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

clusiveTTS.read = function(selector) {
    'use strict';

    if (typeof selector === 'undefined' || selector === null) {
        selector = 'main';
    }

    var elem = clusiveTTS.getElement(selector);

    var nodesToRead = clusiveTTS.getReadableTextNodes(elem);
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
    var focusNode = selection.focusNode;
    var firstNodeOffset;
    var lastNodeOffset;
    var toRead = [];

    if (selectionDirection === clusiveSelection.directions.FORWARD) {
        firstNodeOffset = selection.anchorOffset;
        lastNodeOffset = selection.focusOffset;
    } else {
        firstNodeOffset = selection.focusOffset;
        lastNodeOffset = selection.anchorOffset;
    }

    // TODO: how to preserve ranges, while not selecting the substituted ones?
    selection.removeAllRanges();

    if (filteredElements.length) {
        // Check first and last elements to see if they are hidden and reset offsets accordingly
        if (!clusiveTTS.isVisuallyVisible(filteredElements[0].parentElement) && filteredElements.length > 1) {
            firstNodeOffset = 0;
        }
        if (!clusiveTTS.isVisuallyVisible(filteredElements[filteredElements.length - 1].parentElement)) {
            lastNodeOffset = null;
        }
        // Remove hidden text elements
        filteredElements = filteredElements.filter(function(elem) {
            return clusiveTTS.isVisuallyVisible(elem.parentElement);
        });
    }

    // Still have items after filter?
    if (filteredElements.length) {
        filteredElements.forEach(function(elem, i) {
            var textOffset = i === 0 ? firstNodeOffset : 0;
            var textEnd = i === filteredElements.length - 1 ? lastNodeOffset : null;

            // Reported last selected node (focusNode) might not be within filteredElements
            // so we will need to adjust the focusOffset for the last readable filteredElement
            if (elem !== focusNode) {
                textEnd = null;
            }

            console.debug('textOffset/textEnd', textOffset, textEnd);

            var elementToRead = {
                element: elem,
                offset: textOffset,
                end: textEnd
            };
            if (textOffset !== textEnd) {
                toRead.push(elementToRead);
            }
        });

        clusiveTTS.readElements(toRead);
    } else {
        clusiveTTS.stopReading();
    }
};

clusiveTTS.getLangAttribute = function(node) {
    'use strict';

    var element = node.nodeType === Node.TEXT_NODE ? node.parentElement : node;
    element = element.closest('[lang]');
    if (element && element.nodeName !== 'HTML') {
        return element.getAttribute('lang');
    }
    return null;
};

clusiveTTS.getVoices = function() {
    'use strict';

    var voices =  window.speechSynthesis.getVoices();
    voices = window.speechSynthesis.getVoices().filter(function(voice) {
        return voice.localService === true;
    });
    return voices;
};

// Return all voices known to the system for the given language.
// Language argument can be of the form "en" or "en-GB".
// If system default voice is on this list, it will be listed first.
clusiveTTS.getVoicesForLanguage = function(language) {
    'use strict';

    var voices = [];
    var defaultVoices = [];
    if (!language) {
        return voices;
    }
    clusiveTTS.getVoices().forEach(function(voice) {
        // Handle inconsistent voice locale syntax on Android
        var voiceLang = voice.lang.replace('_', '-').substring(0, language.length);
        if (voiceLang === language) {
            if (voice.default) {
                defaultVoices.push(voice);
            } else {
                voices.push(voice);
            }
        }
    });

    // Put system default voice at the beginning of the list
    voices = defaultVoices.concat(voices);

    return voices;
};

clusiveTTS.setCurrentVoice = function(name) {
    'use strict';

    if (name) {
        window.speechSynthesis.getVoices().forEach(function(voice) {
            if (voice.name === name) {
                clusiveTTS.voiceCurrent = voice;
                if (clusiveTTS.readerReady) {
                    var voiceSpecs = {
                        usePublication: true,
                        lang: voice.lang,
                        name: voice.name
                    };
                    console.debug('setting D2Reader voice to ', voiceSpecs);
                    d2reader.applyTTSSettings({
                        voice: voiceSpecs
                    });
                }
            }
        });
    } else {
        clusiveTTS.voiceCurrent = null;
        if (clusiveTTS.readerReady) {
            console.debug('Unsetting D2Reader voice');
            d2reader.applyTTSSettings({
                voice: null
            });
        }
    }
};

// Force a 'default' voice
// Assume base language of `en`
// Check user languages for region specific `en` variant - otherwise default to `en-US`
// Use first matching voice in list
clusiveTTS.getDefaultVoice = function() {
    'use strict';

    // Reference: https://stackoverflow.com/questions/1043339/
    // Possibly useful in future? - https://stackoverflow.com/a/29106129
    var userLanguages = window.navigator.languages || [window.navigator.language || window.navigator.userLanguage];
    var defaultVoice = null;
    var langVoices = [];

    userLanguages.some(function(lang) {
        if (lang.startsWith('en-')) {
            langVoices = clusiveTTS.getVoicesForLanguage(lang);
            defaultVoice = langVoices.length > 0 ? langVoices[0] : null;
            if (defaultVoice !== null) {
                return true;
            }
        }
        return false;
    });

    if (defaultVoice === null) {
        langVoices = clusiveTTS.getVoicesForLanguage('en-US');
        defaultVoice = langVoices.length > 0 ? langVoices[0] : null;
    }

    if (defaultVoice === null) {
        langVoices = clusiveTTS.getVoicesForLanguage('en');
        defaultVoice = langVoices.length > 0 ? langVoices[0] : null;
    }

    // Case where browser does not return any voices - (Safari v15.4)
    if (defaultVoice === null) {
        return false;
    }

    console.debug('getDefaultVoice', defaultVoice.name);

    return defaultVoice.name;
};

clusiveTTS.updateSettings = function(settings) {
    'use strict';

    console.debug('updateSettings begin');

    // Store queue and stop reading
    var queue = clusiveTTS.elementsToRead;
    clusiveTTS.elementsToRead = [];
    if (Object.prototype.hasOwnProperty.call(settings, 'rate')) {
        clusiveTTS.voiceRate = settings.rate;
    }
    if (Object.prototype.hasOwnProperty.call(settings, 'voice')) {
        clusiveTTS.setCurrentVoice(settings.voice);
    }

    if (clusiveTTS.region.mode === 'Readium') {
        console.debug('updateSettings end D2Reader');
        return;
    }

    // Prepend any current queue item back onto to reading queue if it does not match
    // the first item in the queue already, to reduce some potential repetition.
    if (clusiveTTS.currentQueueItem) {
        if (clusiveTTS.currentQueueItem.element !== queue.element && clusiveTTS.currentQueueItem.offset !== queue.offset) {
            queue.unshift(clusiveTTS.currentQueueItem);
        }
        clusiveTTS.currentQueueItem = null;
    }
    clusiveTTS.elementsToRead = queue;
    window.speechSynthesis.cancel();
    clusiveTTS.utterance = null;
    clusiveTTS.onEnd();

    console.debug('updateSettings end');
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
    var anchorNode = selection.anchorNode;
    var focusNode = selection.focusNode;
    var anchorElement = selection.anchorNode.nodeType === Node.TEXT_NODE ? selection.anchorNode.parentElement : selection.anchorNode;
    var focusElement = selection.focusNode.nodeType === Node.TEXT_NODE ? selection.focusNode.parentElement : selection.focusNode;
    var anchorParent = selection.anchorNode.parentElement;
    var focusParent = selection.focusNode.parentElement;

    // Selection within a single element, direction can be determined by comparing anchor and focus offset
    if (anchorNode === focusNode) {
        selectionDirection = selection.anchorOffset < selection.focusOffset ? clusiveSelection.directions.FORWARD : clusiveSelection.directions.BACKWARD;
    // Nested node (test against parentElement due to Firefox)
    } else if (anchorElement.contains(focusNode) || anchorParent.contains(focusNode)) {
        selectionDirection = clusiveSelection.directions.BACKWARD;
    } else if (focusElement.contains(anchorNode) || focusParent.contains(anchorNode)) {
        selectionDirection = clusiveSelection.directions.FORWARD;
    // Order of anchorNode/focusNode within document
    } else {
        selectionDirection = anchorNode.compareDocumentPosition(focusNode) === Node.DOCUMENT_POSITION_FOLLOWING ? clusiveSelection.directions.FORWARD : clusiveSelection.directions.BACKWARD;
    }

    console.debug('selectionDirection', selectionDirection);
    return selectionDirection;
};

clusiveTTS.toggle = function(e) {
    'use strict';

    clusiveTTS.setRegion(e.currentTarget);

    if (clusiveTTS.region.mode === 'Readium') {
        console.debug('Readium read aloud play button clicked');
        if (!clusiveTTS.synth.speaking) {
            d2reader.startReadAloud();
            clusiveTTS.updateUI('play');
        } else {
            d2reader.stopReadAloud();
            clusiveTTS.updateUI('stop');
        }
    } else {
        console.debug('read aloud play button clicked');
        if (!clusiveTTS.synth.speaking) {
            var selector = clusiveTTS.getSelectorFromElement(e.currentTarget);
            if (clusiveTTS.region.mode === 'dialog') {
                selector = e.currentTarget.closest('.modal, .popover');
            }
            clusiveTTS.resetState();
            clusiveTTS.read(selector);
            clusiveTTS.updateUI('play');
        } else {
            clusiveTTS.stopReading();
            clusiveTTS.updateUI('stop');
        }
    }
};

clusiveTTS.stop = function() {
    'use strict';

    clusiveTTS.stopReadingDetermineApi();
    clusiveTTS.updateUI('stop');
};

clusiveTTS.pause = function() {
    'use strict';

    if (clusiveTTS.region.mode === 'Readium') {
        console.debug('Readium read aloud pause button clicked');
        d2reader.pauseReadAloud();
    } else {
        console.debug('read aloud pause button clicked');
        // Don't reset `userScrolled` here, otherwise page might jump due to async reading
        clusiveTTS.isPaused = true;
        clusiveTTS.synth.pause();
    }
    clusiveTTS.updateUI('pause');
};

clusiveTTS.resume = function() {
    'use strict';

    if (clusiveTTS.region.mode === 'Readium') {
        console.debug('Readium read aloud resume button clicked');
        d2reader.resumeReadAloud();
    } else {
        console.debug('read aloud resume button clicked');
        clusiveTTS.userScrolled = false;

        // Resume by speaking utterance if one is active
        clusiveTTS.isPaused = false;
        if (!clusiveTTS.utterance) {
            clusiveTTS.onEnd();
        }
        setTimeout(function() {
            window.speechSynthesis.resume();
        }, 110);
    }
    clusiveTTS.updateUI('resume');
};
