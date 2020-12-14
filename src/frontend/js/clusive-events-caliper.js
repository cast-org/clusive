/* global PAGE_EVENT_ID, clusive */

$(document).ready(function() {
    'use strict';

    var addCaliperEventToQueue = function(eventType, control, value) {
        console.debug('Adding caliper event to queue: ', eventType, control, value);
        window.clusiveEvents.messageQueue.add({
            type: 'CE',
            caliperEvent: {
                type: eventType,
                control: control,
                value: value
            },
            readerInfo: clusiveContext.reader.info,
            eventId: PAGE_EVENT_ID
        });
    };

    var addVocabCheckSkippedEventToQueue = function() {
        window.clusiveEvents.addCaliperEventToQueue(window.clusiveEvents.caliperEventTypes.ASSESSMENT_ITEM_EVENT, 'word_rating', 'SKIPPED')
    }

    var addTipRelatedActionToQueue = function(action) {
        window.clusiveEvents.messageQueue.add({
            type: 'TRA',
            action: action
        });
    };
    
    window.clusiveEvents = {        
        messageQueue: clusive.djangoMessageQueue({
            config: {
                localStorageKey: "clusive.messageQueue.caliperEvents"
            }
        }),
        caliperEventTypes: {
            TOOL_USE_EVENT: 'TOOL_USE_EVENT',
            ASSESSMENT_ITEM_EVENT: 'ASSESSMENT_ITEM_EVENT'
        },
        dataAttributes: {
            HANDLER: 'data-cle-handler',
            CONTROL: 'data-cle-control',
            VALUE: 'data-cle-value'
        },
        trackedControlInteractions: [
            /*
                control interactions to track can be added centrally here if needed,
                but in most cases using the data-cle-* attributes on the markup
                will be more appropriate
            */
            // {
            //     selector: ".btn.tts-play",
            //     handler: "click",
            //     control: "tts-play",
            //     value: "clicked"
            // }
        ],
        addCaliperEventToQueue: addCaliperEventToQueue,
        addTipRelatedActionToQueue: addTipRelatedActionToQueue,
        addVocabCheckSkippedEventToQueue: addVocabCheckSkippedEventToQueue
    };

    // Build additional control interaction objects here from any data-clusive-event attributes on page markup
    // synax: data-clusive-event="[handler]|[control]|[value]"
    // example: data-clusive-event="click|settings-sidebar|opened"
    $('*[data-cle-handler]').each(function(i, control) {
        // data-clusive-event attribute
        var elm = $(control);
        var eventHandler = $(control).attr(clusiveEvents.dataAttributes.HANDLER);
        var eventControl = $(control).attr(clusiveEvents.dataAttributes.CONTROL);
        var eventValue = $(control).attr(clusiveEvents.dataAttributes.VALUE);
        console.debug('data-cle-handler attribute found', elm, eventHandler, eventControl, eventValue);
        if (eventHandler !== undefined && eventControl !== undefined && eventValue !== undefined) {
            var interactionDef = {
                selector: elm,
                handler: eventHandler,
                control: eventControl,
                value: eventValue
            };
            clusiveEvents.trackedControlInteractions.push(interactionDef);
        } else {
            console.debug('tried to add event logging, but missing a needed data-cle-* attribute on the element: ', elm);
        }
    });

    // Set up events control interactions here
    clusiveEvents.trackedControlInteractions.forEach(function(interactionDef) {
        var control = $(interactionDef.selector);
        console.debug('Event for control tracking: ', interactionDef, control);
        var handler = interactionDef.handler;
        $(interactionDef.selector)[handler](function() {
            addCaliperEventToQueue(window.clusiveEvents.caliperEventTypes.TOOL_USE_EVENT, interactionDef.control, interactionDef.value);
        });
    });

    $('body').on('click', '*[data-clusive-tip-action]', function(event) {
        var action = $(this).attr('data-clusive-tip-action');
        console.debug('data-clusive-tip-action', action, event);
        addTipRelatedActionToQueue(action);
    });
});
