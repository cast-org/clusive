/* global cisl, clusive, fluid_3_0_0, gpii, DJANGO_STATIC_ROOT, DJANGO_CSRF_TOKEN */

(function(fluid) {
    'use strict';

    fluid.defaults('clusive.messageQueue', {       
        gradeNames: ["fluid.modelComponent"],
        model: {
            queue: []
        },
        config: {
            // Where and how to send messages to when trying to flush
            target: {
                url: null,
                method: "POST"
            },
            // Interval for trying to flush queue
            flushInterval: 60000
        },
        events: {
            queueShouldFlush: null,
            queueFlushSuccess: null,
            queueFlushFailure: null
        },
        listeners: {
            "onCreate.setFlushInterval": {
                func: "clusive.messageQueue.setFlushInterval",
                args: ["{that}"]
            },
            "queueShouldFlush.flushQueue": {
                funcName: "{that}.flush"
            },
            "queueFlushSuccess.clearQueue": {
                func: "{that}.applier.change",
                args: ["queue", []]
            }
        },
        invokers: {
            add: {
                funcName: "clusive.messageQueue.addMessage",
                args: ["{that}", "{arguments}.0"]
            },
            wrapMessage: {
                funcName: "clusive.messageQueue.wrapMessage",
                args: ["{arguments}.0"]
            },
            flush: {
                funcName: "clusive.messageQueue.flushQueue",
                args: ["{that}"]
            },
            flushQueueImpl: {
                funcName: "fluid.notImplemented",
                args: ["{that}", "{arguments}.0"]
            }
        },
    });    

    clusive.messageQueue.flushQueue = function (that) {
        var promise = fluid.promise();
        promise.then(
            function(value) {
                that.events.queueFlushSuccess.fire(value);
            },
            function(error) {
                that.events.queueFlushFailure.fire(error);
            })
        that.flushQueueImpl(promise);            
    }

    clusive.messageQueue.setFlushInterval = function (that) {
        var flushInterval = that.options.config.flushInterval;
        setInterval(function () {
            that.events.queueShouldFlush.fire();
        }, flushInterval)
    }

    // A message is any POJO
    clusive.messageQueue.addMessage = function(that, message) {        
        var newQueue = fluid.get(that.model, "queue");        
        newQueue.push(that.wrapMessage(message));
        that.applier.change("queue", newQueue);
    }

    clusive.messageQueue.wrapMessage = function(message) {
        var timestamp = new Date().toISOString();
        var wrappedMessage = {
            message: message,            
            timestamp: timestamp
        };
        return wrappedMessage;
    }

}(fluid_3_0_0));