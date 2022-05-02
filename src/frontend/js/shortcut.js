/* global hotkeys, shortcut */

// Uses `hotkeys-js`
// Repo: https://github.com/jaywcjlove/hotkeys

(function($) {
    'use strict';

    var HOTKEY_TOC = 'alt+t';
    var HOTKEY_HIGHLIGHT = 'alt+h';
    var HOTKEY_SETTINGS_DISPLAY = 'alt+,';
    var HOTKEY_SETTINGS_READ = 'alt+.';

    var SELECTOR_READER_FRAME = '#frameReader';

    var SELECTOR_TOC_BTN = '#tocButton';
    var SELECTOR_TOC_MODAL = '#modalToc';
    var SELECTOR_TOC_TAB = '#tocTab';
    var SELECTOR_TOC_PANEL = '#tocPanel';
    var SELECTOR_HIGHLIGHT_TAB = '#notesTab';
    var SELECTOR_HIGHLIGHT_PANEL = '#notesPanel';

    var SELECTOR_SETTINGS_BTN = '#settingsButton';
    var SELECTOR_SETTINGS_MODAL = '#modalSettings';
    var SELECTOR_SETTINGS_DISPLAY_TAB = '[data-cfw-tab-target="#setting0"]';
    var SELECTOR_SETTINGS_DISPLAY_PANEL = '#setting0';
    var SELECTOR_SETTINGS_READ_TAB = '[data-cfw-tab-target="#setting1"]';
    var SELECTOR_SETTINGS_READ_PANEL = '#setting1';

    var shortcutModule = function() {
        this.readerFound = false;
        this.readerFrame = null;
        this.readerOwner = null;
    };

    shortcutModule.prototype = {
        attachReaderFrame : function() {
            var that = this;

            this.readerFrame = document.querySelector(SELECTOR_READER_FRAME);
            if (this.readerFrame !== null) {
                this.readerFound = true;
                // Pass keydown and keyup from reader frame to parent document
                this.readerOwner = this.readerFrame.ownerDocument;
                $(this.readerFrame.contentWindow.document)
                    .off('keydown.clusive.shortcut  keyup.clusive.shortcut')
                    .on('keydown.clusive.shortcut keyup.clusive.shortcut', function(event) {
                        that.ownerDispatchEvent(event);
                    });
            }
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

                this.triggerKeyboardEvent(this.readerOwner, event.type, eventProperties);
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
                .one('afterShow.cfw.tab', function() {
                    panel.focus();
                })
                .CFW_Tab('show');
        },

        getVisibleModal : function() {
            var items = document.querySelectorAll('.modal');
            var itemsArr = Array.from(items);
            var result = itemsArr.filter(function(element) {
                return $.CFW_isVisible(element);
            });
            return $.CFW_getElement(result[0]);
        },

        modalCloseOther : function(selector) {
            var modalVis = this.getVisibleModal();
            if (modalVis && !modalVis.matches(selector)) {
                $(modalVis).CFW_Modal('hide');
            }
        },

        modalOpen : function(modalBtn, modalDialog, callback) {
            var that = this;
            this.modalCloseOther(modalDialog);
            var dialog = document.querySelector(modalDialog);
            if (dialog.classList.contains('in')) {
                this._execute(callback);
                return;
            }
            $(dialog)
                .one('afterShow.cfw.modal', function() {
                    that._execute(callback);
                });
            $(modalBtn).CFW_Modal('show');
        },

        _execute : function(callback) {
            if (typeof callback === 'function') {
                callback();
            }
        }
    };

    // TOC list
    hotkeys(HOTKEY_TOC, function(event) {
        if (document.querySelector(SELECTOR_TOC_BTN)) {
            event.preventDefault();
            var callback = function() {
                shortcut.tabOpenFocus(SELECTOR_TOC_TAB, SELECTOR_TOC_PANEL);
            };
            shortcut.modalOpen(SELECTOR_TOC_BTN, SELECTOR_TOC_MODAL, callback);
        }
    });

    // Highlight list
    hotkeys(HOTKEY_HIGHLIGHT, function(event) {
        if (document.querySelector(SELECTOR_TOC_BTN)) {
            event.preventDefault();
            var callback = function() {
                shortcut.tabOpenFocus(SELECTOR_HIGHLIGHT_TAB, SELECTOR_HIGHLIGHT_PANEL);
            };
            shortcut.modalOpen(SELECTOR_TOC_BTN, SELECTOR_TOC_MODAL, callback);
        }
    });

    // Settings - display panel
    hotkeys(HOTKEY_SETTINGS_DISPLAY, function(event) {
        if (document.querySelector(SELECTOR_SETTINGS_BTN)) {
            event.preventDefault();
            var callback = function() {
                shortcut.tabOpenFocus(SELECTOR_SETTINGS_DISPLAY_TAB, SELECTOR_SETTINGS_DISPLAY_PANEL);
            };
            shortcut.modalOpen(SELECTOR_SETTINGS_BTN, SELECTOR_SETTINGS_MODAL, callback);
        }
    });

    // Settings - reading panel
    hotkeys(HOTKEY_SETTINGS_READ, function(event) {
        if (document.querySelector(SELECTOR_SETTINGS_BTN)) {
            event.preventDefault();
            var callback = function() {
                shortcut.tabOpenFocus(SELECTOR_SETTINGS_READ_TAB, SELECTOR_SETTINGS_READ_PANEL);
            };
            shortcut.modalOpen(SELECTOR_SETTINGS_BTN, SELECTOR_SETTINGS_MODAL, callback);
        }
    });

    window.shortcut = shortcutModule.prototype;
}(jQuery));

