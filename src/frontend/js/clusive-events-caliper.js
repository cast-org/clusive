/* global PAGE_EVENT_ID, clusive, clusiveContext, clusiveEvents */

$(document).ready(function() {
    'use strict';

    var addCaliperEventToQueue = function(eventType, control, value, action) {
        console.debug('Adding caliper event to queue: ', eventType, control, value);
        window.clusiveEvents.messageQueue.add({
            type: 'CE',
            caliperEvent: {
                type: eventType,
                control: control,
                value: value,
                action: action
            },
            readerInfo: clusiveContext.reader.info,
            eventId: PAGE_EVENT_ID
        });
    };

    var addVocabCheckSkippedEventToQueue = function() {
        window.clusiveEvents.addCaliperEventToQueue(window.clusiveEvents.caliperEventTypes.ASSESSMENT_ITEM_EVENT,
            'checkin', null, window.clusiveEvents.caliperEventActions.ASSESSMENT_ITEM_SKIPPED);
    };

    var addTipRelatedActionToQueue = function(action) {
        window.clusiveEvents.messageQueue.add({
            type: 'TRA',
            action: action,
            readerInfo: clusiveContext.reader.info,
            eventId: PAGE_EVENT_ID
        });
    };

    window.clusiveEvents = {
        messageQueue: clusive.djangoMessageQueue({
            config: {
                localStorageKey: 'clusive.messageQueue.caliperEvents',
                lastQueueFlushInfoKey: 'clusive.messageQueue.caliperEvents.log.lastQueueFlushInfo'
            }
        }),
        caliperEventTypes: {
            TOOL_USE_EVENT: 'TOOL_USE_EVENT',
            ASSESSMENT_ITEM_EVENT: 'ASSESSMENT_ITEM_EVENT'
        },
        caliperEventActions: {
            USED: 'USED',
            ASSESSMENT_ITEM_SKIPPED: 'SKIPPED',
            ASSESSMENT_ITEM_COMPLETED: 'COMPLETED'
        },
        dataAttributes: {
            HANDLER: 'data-cle-handler',
            CONTROL: 'data-cle-control',
            VALUE: 'data-cle-value'
        },

        addCaliperEventToQueue: addCaliperEventToQueue,
        addTipRelatedActionToQueue: addTipRelatedActionToQueue,
        addVocabCheckSkippedEventToQueue: addVocabCheckSkippedEventToQueue

    };

    // Listen for 'click' events on elements with the data-cle attributes.
    var $body = $('body');
    $body.on('click', '*[' + clusiveEvents.dataAttributes.HANDLER + '=\'click\']', function() {
        var eventControl = $(this).attr(clusiveEvents.dataAttributes.CONTROL);
        var eventValue = $(this).attr(clusiveEvents.dataAttributes.VALUE);
        console.debug('Event click:', eventControl, eventValue);
        if (typeof typeof eventControl !== 'undefined'
            && typeof eventValue !== 'undefined') {
            addCaliperEventToQueue(window.clusiveEvents.caliperEventTypes.TOOL_USE_EVENT,
                eventControl, eventValue, window.clusiveEvents.caliperEventActions.USED);
        } else {
            console.warn('  Event clicked object was missing required attribute.');
        }
    });

    $body.on('click', '*[data-clusive-tip-action]', function(event) {
        var action = $(this).attr('data-clusive-tip-action');
        console.debug('data-clusive-tip-action', action, event);
        addTipRelatedActionToQueue(action);
    });
});
