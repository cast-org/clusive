/* global clusiveTTS, contextLookup, contextTransform, d2reader, getTocTitle, hotkeys, notify, shortcut */

// Uses `hotkeys-js`
// Repo: https://github.com/jaywcjlove/hotkeys

(function($) {
    'use strict';

    // keys:  key combination used to trigger hotkey routine
    // routine: logic used to determine course of action when hotkey is pressed
    // blocker: logic used to determine if `keys` should be blocked at reader level - boolean value of true is always block
    var HOTKEYS = [
        {
            keys: 'alt+k',
            routine: 'shortcutDialog',
            blocker: true
        },
        {
            keys: 'alt+t',
            routine: 'tocDialog',
            blocker: true
        },
        {
            keys: 'alt+h',
            routine: 'highlightDialog',
            blocker: true
        },
        {
            keys: 'alt+,',
            routine: 'settingsDisplayDialog',
            blocker: true
        },
        {
            keys: 'alt+.',
            routine: 'settingsReadingToolsDialog',
            blocker: true
        },
        {
            keys: 'alt+a',
            routine: 'ttsToggle',
            blocker: true
        },
        {
            keys: 'space',
            routine: 'ttsPause',
            blocker: 'ttsPauseBlocker'
        },
        {
            keys: 'alt+f',
            routine: 'searchFocus',
            blocker: true
        },
        {
            keys: 'alt+r',
            routine: 'readerFocus',
            blocker: true
        },
        {
            keys: 'left',
            routine: 'pagePrev',
            blocker: true
        },
        {
            keys: 'right',
            routine: 'pageNext',
            blocker: true
        },
        {
            keys: 'alt+pageup',
            routine: 'sectionPrev',
            blocker: true
        },
        {
            keys: 'alt+pagedown',
            routine: 'sectionNext',
            blocker: true
        },
        {
            keys: 'alt+l',
            routine: 'libraryPage',
            blocker: true
        },
        {
            keys: 'alt+d',
            routine: 'contextLookup',
            blocker: 'contextLookupBlocker'
        },
        {
            keys: 'alt+s',
            routine: 'contextTransform',
            blocker: 'contextTransformBlocker'
        },
        {
            keys: 'alt+w',
            routine: 'whereAmI',
            blocker: true
        }
    ];

    var SELECTOR_SHORTCUTS_BTN = '#shortcutsLocator';
    var SELECTOR_SHORTCUTS_DIALOG = '#shortcutsPop';

    var SELECTOR_READER_FRAME = '#frameReader';

    var SELECTOR_TOC_BTN = '#tocButton';
    var SELECTOR_TOC_MODAL = '#modalToc';
    var SELECTOR_TOC_TAB = '#tocTab';
    var SELECTOR_TOC_PANEL = '#tocPanel';
    var SELECTOR_HIGHLIGHT_TAB = '#notesTab';
    var SELECTOR_HIGHLIGHT_PANEL = '#notesPanel';

    var SELECTOR_SETTINGS_BTN = '#settingsButton';
    var SELECTOR_SETTINGS_MODAL = '#modalSettings';
    var SELECTOR_SETTINGS_DISPLAY_TAB = '#settingsDisplayTab';
    var SELECTOR_SETTINGS_DISPLAY_PANEL = '#setting0';
    var SELECTOR_SETTINGS_READ_TAB = '#settingsReadingTab';
    var SELECTOR_SETTINGS_READ_PANEL = '#setting1';

    var SELECTOR_READ_ALOUD_REGIONS = '.sidebar-tts, .dialog-tts';
    var SELECTOR_READ_ALOUD_GLOBAL_PLAY = '.sidebar-end .tts-play';
    var SELECTOR_READ_ALOUD_ACTIVE = '.sidebar-tts.active';

    var SELECTOR_GLOSSARY_DIALOG = '#glossaryPop';
    var SELECTOR_SIMPLIFY_DIALOG = '#simplifyPop';

    var shortcutModule = function() {
        this.readerDocument = null;
        this.readerFound = false;
        this.readerFrame = null;
        this.readerOwner = null;
    };

    shortcutModule.ROUTINE = {
        // Show keyboard shortcuts dialog
        shortcutDialog : function(event, keys) {
            if ($.CFW_isVisible(document.querySelector(SELECTOR_SHORTCUTS_DIALOG))) {
                if (event) { event.preventDefault(); }
                document.querySelector(SELECTOR_SHORTCUTS_DIALOG).focus();
                return;
            }
            if (document.querySelector(SELECTOR_SHORTCUTS_BTN)) {
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-shortcuts-dialog', keys);
                var callback = function() {
                    document.querySelector(SELECTOR_SHORTCUTS_DIALOG).focus();
                };
                shortcut.popoverOpen(SELECTOR_SHORTCUTS_BTN, SELECTOR_SHORTCUTS_DIALOG, callback);
            }
        },

        // TOC list
        tocDialog : function(event, keys) {
            if (document.querySelector(SELECTOR_TOC_BTN)) {
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-toc-panel', keys);
                var callback = function() {
                    shortcut.tabOpenFocus(SELECTOR_TOC_TAB, SELECTOR_TOC_PANEL);
                };
                shortcut.modalOpen(SELECTOR_TOC_BTN, SELECTOR_TOC_MODAL, callback);
            }
        },

        // Highlight dialog
        highlightDialog : function(event, keys) {
            if (shortcut.readerFound && shortcut.hasReaderSelection()) {
                // Create highlight
                if (typeof d2reader === 'object') {
                    if (event) { event.preventDefault(); }
                    shortcut.addEvent('hotkey-highlight-create', keys);
                    d2reader.highlighter.doHighlight();
                    shortcut.clearAllSelection();
                    d2reader.highlighter.toolboxHide();
                }
            } else if (document.querySelector(SELECTOR_TOC_BTN)) {
                // Open highlight panel
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-highlight-panel', keys);
                var callback = function() {
                    shortcut.tabOpenFocus(SELECTOR_HIGHLIGHT_TAB, SELECTOR_HIGHLIGHT_PANEL);
                };
                shortcut.modalOpen(SELECTOR_TOC_BTN, SELECTOR_TOC_MODAL, callback);
            }
        },

        // Settings: Display dialog
        settingsDisplayDialog : function(event, keys) {
            if (document.querySelector(SELECTOR_SETTINGS_BTN)) {
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-settings-display', keys);
                var callback = function() {
                    shortcut.tabOpenFocus(SELECTOR_SETTINGS_DISPLAY_TAB, SELECTOR_SETTINGS_DISPLAY_PANEL);
                };
                shortcut.modalOpen(SELECTOR_SETTINGS_BTN, SELECTOR_SETTINGS_MODAL, callback);
            }
        },

        // Settings: Reading tools dialog
        settingsReadingToolsDialog : function(event, keys) {
            if (document.querySelector(SELECTOR_SETTINGS_BTN)) {
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-settings-reading-tools', keys);
                var callback = function() {
                    shortcut.tabOpenFocus(SELECTOR_SETTINGS_READ_TAB, SELECTOR_SETTINGS_READ_PANEL);
                };
                shortcut.modalOpen(SELECTOR_SETTINGS_BTN, SELECTOR_SETTINGS_MODAL, callback);
            }
        },

        // Read-aloud - play/stop
        ttsToggle : function(event, keys) {
            // Check for selection within reader
            if (shortcut.readerFound && shortcut.hasReaderSelection()) {
                // Read only selected text
                if (typeof d2reader === 'object') {
                    if (event) { event.preventDefault(); }
                    shortcut.addEvent('hotkey-tts-play-reader-selection', keys);
                    d2reader.highlighter.speak();
                    shortcut.clearAllSelection();
                    d2reader.highlighter.toolboxHide();
                    return;
                }
            }

            var ttsRegions = document.querySelectorAll(SELECTOR_READ_ALOUD_REGIONS);
            var result = shortcut.filterElementsForVisible(ttsRegions);
            if (event) { event.preventDefault(); }

            if (result.length) {
                // Default to 'global' play button
                var ttsBtn = document.querySelector(SELECTOR_READ_ALOUD_GLOBAL_PLAY);
                if (!$.CFW_isVisible(ttsBtn)) {
                    ttsBtn = null;
                }
                // Find current activeElement to determine location
                var activeElm = document.activeElement;
                // Check for parent dialog and find it's play button
                var dialog = activeElm.closest('.modal, .popover');
                if (dialog !== null) {
                    ttsBtn = dialog.querySelector('.tts-play');
                }
                if (ttsBtn !== null) {
                    shortcut.addEvent('hotkey-tts-play', keys);
                    clusiveTTS.toggle({
                        currentTarget: ttsBtn
                    });
                    return;
                }
            }

            shortcut.addEvent('hotkey-tts-stop', keys);
            clusiveTTS.stop();
        },

        // Read-aloud - pause/resume
        ttsPause : function(event, keys) {
            var ttsRegions = document.querySelectorAll(SELECTOR_READ_ALOUD_REGIONS);
            var result = shortcut.filterElementsForVisible(ttsRegions);

            if (result.length && clusiveTTS.isReadingState) {
                if (event) { event.preventDefault(); }
                if (clusiveTTS.isPausedState) {
                    shortcut.addEvent('hotkey-tts-resume', keys);
                    clusiveTTS.resume();
                } else {
                    shortcut.addEvent('hotkey-tts-pause', keys);
                    clusiveTTS.pause();
                }
            }
        },

        // Search - focus on search field
        // - currently only library and bookshare - not at same time
        searchFocus: function(event, keys) {
            var searchElm = document.querySelector('input[type="search"]');
            if (searchElm !== null) {
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-search-focus', keys);
                searchElm.focus();
            }
        },

        // Reader - focus content
        readerFocus: function(event, keys) {
            if (shortcut.readerFound && typeof d2reader === 'object') {
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-reader-focus', keys);
                shortcut.focusReaderBody();
            }
        },

        // Reader navigation - previous page
        pagePrev: function(event, keys) {
            if (shortcut.readerFound && typeof d2reader === 'object') {
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-reader-navigation-pagination-previous', keys);
                d2reader.previousPage();
            }
        },

        // Reader navigation - next page
        pageNext: function(event, keys) {
            if (shortcut.readerFound && typeof d2reader === 'object') {
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-reader-navigation-pagination-next', keys);
                d2reader.nextPage();
            }
        },

        // Reader navigation - previous section/resource
        sectionPrev: function(event, keys) {
            if (shortcut.readerFound && typeof d2reader === 'object') {
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-reader-navigation-section-previous', keys);
                shortcut.processAdd(function() {
                    shortcut.focusReaderBody();
                });
                d2reader.previousResource();
            }
        },

        // Reader navigation - next section/resource
        sectionNext: function(event, keys) {
            if (shortcut.readerFound && typeof d2reader === 'object') {
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-reader-navigation-section-next', keys);
                shortcut.processAdd(function() {
                    shortcut.focusReaderBody();
                });
                d2reader.nextResource();
            }
        },

        // Library page
        libraryPage: function(event, keys) {
            if (!window.location.pathname.includes('/library/')) {
                if (event) { event.preventDefault(); }
                shortcut.addEvent('hotkey-library', keys);
                window.location.href = '/reader';
            }
        },

        // Context menu - word lookup (definition)
        contextLookup: function(event, keys) {
            if (shortcut.readerFound) {
                if (shortcut.hasReaderSelection()) {
                    // Do lookup
                    if (event) { event.preventDefault(); }
                    shortcut.addEvent('hotkey-lookup', keys);
                    contextLookup(shortcut.getReaderSelection().toString());
                    shortcut.clearReaderSelection();
                    if (typeof d2reader === 'object') {
                        d2reader.highlighter.toolboxHide();
                    }
                } else if ($.CFW_isVisible(document.querySelector(SELECTOR_GLOSSARY_DIALOG))) {
                    // Focus the glossary popover
                    if (event) { event.preventDefault(); }
                    document.querySelector(SELECTOR_GLOSSARY_DIALOG).focus();
                }
            }
        },

        // Context menu - transform (simplifiy, translate, ...)
        contextTransform: function(event, keys) {
            if (shortcut.readerFound) {
                if (shortcut.hasReaderSelection()) {
                    // Do transform
                    if (event) { event.preventDefault(); }
                    shortcut.addEvent('hotkey-transform', keys);
                    contextTransform(shortcut.getReaderSelection().toString());
                    shortcut.clearReaderSelection();
                    if (typeof d2reader === 'object') {
                        d2reader.highlighter.toolboxHide();
                    }
                } else if ($.CFW_isVisible(document.querySelector(SELECTOR_SIMPLIFY_DIALOG))) {
                    // Focus the simplify/transform popover
                    if (event) { event.preventDefault(); }
                    document.querySelector(SELECTOR_SIMPLIFY_DIALOG).focus();
                }
            }
        },

        // 'Where am I?'
        whereAmI: function(event, keys) {
            var title = null;
            var percent = null;
            var msg = '';

            if (event) { event.preventDefault(); }
            shortcut.addEvent('hotkey-whereami', keys);

            if (shortcut.readerFound) {
                // Give location within reader document
                title = getTocTitle();
                percent = Math.round(parseFloat(d2reader.currentLocator.locations.totalProgression) * 100);
                msg = 'You are ' + percent + '% through ' + title;
            } else {
                title = document.title.replace(' | Clusive', '');
                msg = 'You are on Clusive\'s ' + title + ' page';
            }

            notify.show(msg);
        }
    };

    // Internal reader blocker checks
    // No need for `readerFound` check as reader will always exist for internal blockers
    shortcutModule.BLOCKER = {
        ttsPauseBlocker: function() {
            var ttsActive = document.querySelector(SELECTOR_READ_ALOUD_ACTIVE);
            if (ttsActive !== null) {
                return true;
            }
            return false;
        },
        contextLookupBlocker: function() {
            if (shortcut.hasReaderSelection() || $.CFW_isVisible(document.querySelector(SELECTOR_GLOSSARY_DIALOG))) {
                return true;
            }
            return false;
        },
        contextTransformBlocker: function() {
            if (shortcut.hasReaderSelection() || $.CFW_isVisible(document.querySelector(SELECTOR_SIMPLIFY_DIALOG))) {
                return true;
            }
            return false;
        }
    };

    shortcutModule.prototype = {
        attachReaderFrame : function() {
            var that = this;

            this.readerFrame = document.querySelector(SELECTOR_READER_FRAME);
            if (this.readerFrame !== null) {
                this.readerFound = true;
                // Pass keydown from reader frame to parent document
                this.readerOwner = this.readerFrame.ownerDocument;
                this.readerDocument = this.readerFrame.contentDocument || this.readerFrame.contentWindow.document;

                // Block all hotkey combos at reader level
                this.readerFrame.contentWindow.blockHotkeys(HOTKEYS);

                // Pass keydown from reader frame to parent document
                $(this.readerDocument)
                    .off('keydown.clusive.shortcut')
                    .on('keydown.clusive.shortcut', function(event) {
                        that.ownerDispatchEvent(event);
                    });
            }
        },

        invokeRoutine : function(keysList, routineName, event) {
            shortcut.routine[routineName](event, keysList);
        },

        doBlockInternal : function(blockerName) {
            if (typeof blockerName === 'undefined') {
                blockerName = null;
            }
            if (blockerName === true) {
                return true;
            }
            if (blockerName !== null && Object.prototype.hasOwnProperty.call(shortcut, blockerName)) {
                if (shortcut.blocker[blockerName]() === true) {
                    return true;
                }
            }
            // Keydown event should not be blocked by default
            return false;
        },

        process : function() {
            $(document.body).trigger('process.shortcut');
        },

        processAdd : function(callback) {
            var that = this;
            $(document.body)
                .off('process.shortcut')
                .one('process.shortcut', function() {
                    that._execute(callback);
                });
        },

        hasReader : function() {
            return this.readerFound;
        },

        ownerDispatchEvent : function(event) {
            var editable = false;

            // Filter out editable items
            // [contenteditable="true"], input, textarea, select - unless readonly
            var target = event.target;
            var tagName = target.tagName;
            if (target.isContentEditable || (tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT') && !target.readOnly) {
                editable = true;
            }

            if (!editable) {
                var eventProperties = {
                    bubbles : true,
                    cancelable : true,
                    key: event.key,
                    code: event.code,
                    location: event.location,
                    ctrlKey: event.ctrlKey,
                    shiftKey: event.shiftKey,
                    altKey: event.altKey,
                    metaKey: event.metaKey,
                    repeat: event.repeat,
                    isComposing: event.isComposing,
                    charCode: event.charCode,
                    keyCode: event.keyCode,
                    which: event.which,
                    getModifierState: event.getModifierState
                };

                this.triggerKeyboardEvent(this.readerOwner, 'keydown', eventProperties);
                // Force keyup to 'clear' the presses  in hotkeys-js.
                // Needed for Firefox due to frame document changing on reader resource change.
                // When document changes, keyup is not typically not dispatched before change
                // or after keyup handler is re-attached, causing loss of update to hotkey-js.
                this.triggerKeyboardEvent(this.readerOwner, 'keyup', eventProperties);
            }
        },

        triggerKeyboardEvent : function(element, eventName, extraData) {
            var e = new KeyboardEvent(eventName, extraData);
            element.dispatchEvent(e);
        },

        tabOpenFocus : function(tabBtn, tabPanel) {
            var panel = document.querySelector(tabPanel);
            if (panel.classList.contains('in')) {
                panel.focus();
                return;
            }
            $(tabBtn)
                .off('afterShow.cfw.tab.shortcut')
                .one('afterShow.cfw.tab.shortcut', function() {
                    panel.focus();
                })
                .CFW_Tab('show');
        },

        filterElementsForVisible : function(items) {
            var itemsArr = Array.from(items);
            var result = itemsArr.filter(function(element) {
                return $.CFW_isVisible(element);
            });
            return result;
        },

        getVisibleModal : function() {
            var items = document.querySelectorAll('.modal');
            var result = this.filterElementsForVisible(items);
            return $.CFW_getElement(result[0]);
        },

        modalCloseOther : function(selector, callback) {
            var that = this;
            var modalVis = this.getVisibleModal();
            if (modalVis && (!modalVis.matches(selector) || selector === null)) {
                $(modalVis)
                    .off('afterHide.cfw.modal.shortcut')
                    .one('afterHide.cfw.modal.shortcut', function() {
                        that._execute(callback);
                    })
                    .CFW_Modal('hide');
            }
            this._execute(callback);
        },

        modalOpen : function(modalBtn, modalDialog, callback) {
            var that = this;

            var modalOpenCallback = function() {
                var dialog = document.querySelector(modalDialog);
                if (dialog.classList.contains('in')) {
                    that._execute(callback);
                    return;
                }
                $(dialog)
                    .off('afterShow.cfw.modal.shortcut')
                    .one('afterShow.cfw.modal.shortcut', function() {
                        that._execute(callback);
                    });
                $(modalBtn).CFW_Modal('show');
            };

            this.modalCloseOther(modalDialog, modalOpenCallback);
        },

        popoverOpen : function(popoverBtn, popoverDialog, callback) {
            var that = this;

            var dialog = document.querySelector(popoverDialog);
            if (dialog.classList.contains('in')) {
                that._execute(callback);
                return;
            }
            $(popoverBtn)
                .off('afterShow.cfw.popover.shortcut')
                .one('afterShow.cfw.popover.shortcut', function() {
                    that._execute(callback);
                })
                .CFW_Popover('show');
        },

        updateTabIndex : function(element) {
            if (!element.hasAttribute('tabindex')) {
                element.setAttribute('tabindex', -1);
            }
        },

        getReaderBody : function() {
            var readerFrame = document.querySelector(SELECTOR_READER_FRAME);
            var readerDocument = readerFrame.contentDocument || readerFrame.contentWindow.document;
            return readerDocument.body;
        },

        focusReaderBody : function() {
            var that = this;

            // Clean hotkey-js _downKeys[]
            var eventFocus = new Event('focus');
            window.dispatchEvent(eventFocus);

            var focusReaderCallback = function() {
                var readerBody = that.getReaderBody();
                that.updateTabIndex(readerBody);
                setTimeout(function() {
                    readerBody.focus();
                });
            };

            this.modalCloseOther(null, focusReaderCallback);
        },

        isSelection : function(selection) {
            if (selection === null) {
                return false;
            }
            return !(selection.type === 'None' || selection.type === 'Caret');
        },

        getClusiveSelection : function() {
            return window.getSelection();
        },

        hasClusiveSelection : function() {
            return this.isSelection(this.getClusiveSelection());
        },

        clearClusiveSelection : function() {
            window.getSelection().removeAllRanges();
        },

        getReaderSelection : function() {
            return this.readerDocument.getSelection();
        },

        hasReaderSelection : function() {
            return this.isSelection(this.getReaderSelection());
        },

        clearReaderSelection : function() {
            this.readerDocument.getSelection().removeAllRanges();
        },

        clearAllSelection : function() {
            this.clearClusiveSelection();
            this.clearReaderSelection();
        },

        addEvent : function(eventControl, eventValue) {
            if (typeof eventControl === 'undefined' || typeof eventValue === 'undefined') {
                return;
            }
            window.clusiveEvents.addCaliperEventToQueue(
                window.clusiveEvents.caliperEventTypes.TOOL_USE_EVENT,
                eventControl,
                eventValue,
                window.clusiveEvents.caliperEventActions.USED
            );
        },

        _execute : function(callback) {
            if (typeof callback === 'function') {
                callback();
            }
        },

        routine : shortcutModule.ROUTINE,
        blocker : shortcutModule.BLOCKER
    };

    HOTKEYS.forEach(function(item) {
        hotkeys(item.keys, function(event) {
            shortcut.invokeRoutine(item.keys, item.routine, event);
        });
    });

    window.shortcut = shortcutModule.prototype;
}(jQuery));
