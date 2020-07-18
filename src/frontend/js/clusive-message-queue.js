/* global cisl, clusive, fluid_3_0_0, gpii, DJANGO_STATIC_ROOT, DJANGO_CSRF_TOKEN */

(function(fluid) {
    'use strict';

    fluid.defaults('clusive.messageQueue', {       
        gradeNames: ["fluid.modelComponent"],
        model: {
            queue: []
        },
        config: {
            // Where to send messages to when emptying
            target: {
                url: null,
                method: "POST"
            },
            // Interval for trying to empty queue
            holdLength: 60000
        },
        events: {
            queueShouldEmpty: null,
            queueEmptySuccess: null,
            queueEmptyFailure: null
        },
        listeners: {
            "onCreate.setEmptyInterval": {
                func: "clusive.messageQueue.setEmptyInterval",
                args: ["{that}"]
            },
            "queueShouldEmpty.emptyQueue": {
                funcName: "{that}.empty"
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
            empty: {
                funcName: "clusive.messageQueue.emptyQueue",
                args: ["{that}"]
            },
            emptyQueueImpl: {
                funcName: "fluid.notImplemented",
                args: ["{that}", "{arguments}.0"]
            }
        },
    });    

    clusive.messageQueue.emptyQueue = function (that) {
        var promise = fluid.promise();
        promise.then(
            function(value) {
                that.events.queueEmptySuccess.fire(value);
            },
            function(error) {
                that.events.queueEmptyFailure.fire(error);
            })
        that.emptyQueueImpl(promise);            
    }

    clusive.messageQueue.setEmptyInterval = function (that) {
        var holdLength = that.options.config.holdLength;
        setInterval(function () {
            that.events.queueShouldEmpty.fire();
        }, holdLength)
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