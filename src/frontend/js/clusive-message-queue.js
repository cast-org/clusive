/* global cisl, clusive, fluid_3_0_0, gpii, DJANGO_STATIC_ROOT, DJANGO_CSRF_TOKEN */

(function(fluid) {
    'use strict';

    fluid.defaults('clusive.messageQueue', {       
        gradeNames: ["fluid.component"],    
        members: {
            queue: []
        },
        config: {
            // Where and how to send messages to when trying to flush
            target: {
                url: null,
                method: "POST"
            },
            // Interval for trying to flush queue
            flushInterval: 60000,
            localStorageKey: "clusive.messageQueue.queue"
        },
        events: {
            queueShouldFlush: null,
            queueFlushSuccess: null,
            queueFlushFailure: null,
            syncedToLocalStorage: null        
        },
        listeners: {
            "onCreate.syncFromLocalStorage": {
                func: "clusive.messageQueue.syncFromLocalStorage",
                args: ["{that}"]                
            },
            "onCreate.setFlushInterval": {
                funcName: "{that}.setFlushInterval"                
            },
            "queueShouldFlush.flushQueue": {
                funcName: "{that}.flush"
            },
            "queueFlushSuccess.clearQueue": {
                func: "{that}.clearQueue",                
            }           
        },
        invokers: {
            add: {
                funcName: "clusive.messageQueue.addMessage",
                args: ["{that}", "{arguments}.0"]
            },
            clearQueue: {
                funcName: "clusive.messageQueue.clearQueue",
                args: ["{that}"]                
            },
            getMessages: {
                funcName: "clusive.messageQueue.getMessages",
                args: ["{that}"]
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
            },
            setFlushInterval: {
                funcName: "clusive.messageQueue.setFlushInterval",
                args: ["{that}"]
            },
            syncFromLocalStorage: {
                funcName: "clusive.messageQueue.syncFromLocalStorage",
                args: ["{that}"]
            },
            syncToLocalStorage: {
                funcName: "clusive.messageQueue.syncToLocalStorage",
                args: ["{that}"]
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
        // Make sure we're synced up with any changes in local storage
        // that other components might have caused
        that.syncFromLocalStorage();      
        var newQueue = fluid.get(that, "queue");        
        newQueue.push(that.wrapMessage(message));
        that.queue = newQueue;
        that.syncToLocalStorage();
    }

    // Get the current queue of messages
    clusive.messageQueue.getMessages = function(that) {
        that.syncFromLocalStorage();
        return that.queue;
    }

    clusive.messageQueue.wrapMessage = function(message) {
        var timestamp = new Date().toISOString();
        var wrappedMessage = {
            content: message,            
            timestamp: timestamp
        };
        return wrappedMessage;
    }

    clusive.messageQueue.syncFromLocalStorage = function(that) {            
        var messagesInLocalStorage = localStorage.getItem(that.options.config.localStorageKey);                
        if(messagesInLocalStorage) {             
            var parsedMessages = JSON.parse(messagesInLocalStorage);  
            that.queue = parsedMessages;                      
        }
    }

    clusive.messageQueue.syncToLocalStorage = function(that) {           
        localStorage.setItem(that.options.config.localStorageKey, JSON.stringify(that.queue));
        that.events.syncedToLocalStorage.fire();
    }

    clusive.messageQueue.clearQueue = function(that) { 
        that.queue = [];        
        localStorage.removeItem(that.options.config.localStorageKey);
    }

}(fluid_3_0_0));