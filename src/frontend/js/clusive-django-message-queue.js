/* global cisl, clusive, fluid_3_0_0, gpii, DJANGO_STATIC_ROOT, DJANGO_CSRF_TOKEN */

(function(fluid) {
    'use strict';

    // Message queue implementation to work with the Django store
    fluid.defaults("clusive.djangoMessageQueue", {
        gradeNames: ["clusive.messageQueue"],
        config: {
            // Where and how to send messages to when trying to flush
            target: {
                url: '/messagequeue/',
                method: "POST"
            },
            flushInterval: 180000,
            logoutLinkSelector: "#logoutLink"
        },
        events: {
            logoutFlushComplete: null
        },
        invokers: {
            flushQueueImpl: {
                funcName: "clusive.djangoMessageQueue.flushQueueImpl"                
            },
            wrapMessage: {
                funcName: "clusive.djangoMessageQueue.wrapMessage",
                args: ["{arguments}.0"]
            },
            isQueueEmpty: {
                funcName: "clusive.djangoMessageQueue.isQueueEmpty",
                args: ["{that}"]
            },
            logoutFlush: {
                funcName: "clusive.djangoMessageQueue.logoutFlush",
                args: ["{that}"]
            },
            setupLogoutFlushPromise: {
                funcName: "clusive.djangoMessageQueue.setupLogoutFlushPromise",
                args: ["{that}", "{arguments}.0"]
            }
        },
        listeners: {
            "onCreate.attachLogoutEvents": {
                funcName: "clusive.djangoMessageQueue.attachLogoutEvents",
                args: ["{that}"]
            },
            "logoutFlushComplete.doLogout": {
                funcName: "clusive.djangoMessageQueue.doLogout",
                args: ["{that}"]
            }                        
        }
    });

    clusive.djangoMessageQueue.logoutFlush = function (that) {        
        clusive.messageQueue.flushQueue(that, that.setupLogoutFlushPromise);
    }    

    clusive.djangoMessageQueue.setupLogoutFlushPromise = function (that, promise) {        
        promise.then(
            function(value) {
                that.events.queueFlushSuccess.fire(value);
                that.events.logoutFlushComplete.fire();
            },
            function(error) {
                that.events.queueFlushFailure.fire(error);
                that.events.logoutFlushComplete.fire();
            })    
    }

    clusive.djangoMessageQueue.attachLogoutEvents = function (that) {
        var logoutLinkSelector = that.options.config.logoutLinkSelector;        
                
        $(logoutLinkSelector).click(
            function (e) {                
                if(! that.isQueueEmpty()) { 
                    console.log("logout link clicked while queue not empty");
                    $(logoutLinkSelector).text("Saving changes...").fadeIn();                    
                    e.preventDefault();
                    that.logoutFlush();
                }                                
            }
        );
    };

    clusive.djangoMessageQueue.doLogout = function (that) {        
        var logoutLinkSelector = that.options.config.logoutLinkSelector;
        $(logoutLinkSelector).text("Logging out").fadeIn();        
        window.location = $(logoutLinkSelector).attr("href");
    }

    // Concrete implementation of the queue flushing that works with 
    // the server-side message queue
    clusive.djangoMessageQueue.flushQueueImpl = function (that, flushPromise) {
        that.sendingQueue.username = DJANGO_USERNAME;
        $.ajax(that.options.config.target.url, {
            method: that.options.config.target.method,
            headers: {
                'X-CSRFToken': DJANGO_CSRF_TOKEN
            },
            data: JSON.stringify(that.sendingQueue)
        })
            .done(function(data) {
                flushPromise.resolve({"success": 1});
            })
            .fail(function(err) {
                flushPromise.reject({"error": err});
            });
    };

    // Add current username to each individual message
    clusive.djangoMessageQueue.wrapMessage = function(message) {
        var wrappedMessage = clusive.messageQueue.wrapMessage(message);
        wrappedMessage.username = DJANGO_USERNAME;
        return wrappedMessage;
    }

    // Check if both the queue and the sending queue are empty 
    // (no outstanding or in-flight messages)
    clusive.djangoMessageQueue.isQueueEmpty = function (that) {        
        return (that.queue.length === 0 && $.isEmptyObject(that.sendingQueue));
    };

}(fluid_3_0_0));