/* global cisl, clusive, fluid_3_0_0, gpii, DJANGO_STATIC_ROOT, DJANGO_CSRF_TOKEN */

(function(fluid) {
    'use strict';

    fluid.defaults("clusive.logoutFlushManager", {
        gradeNames: ["fluid.component", "fluid.resolveRootSingle"],
        singleRootType: "clusive.logoutFlushManager",
        members: {
            numberOfQueues: 0,
            completedFlushes: 0
        }
    });

    var logoutFlushManager = clusive.logoutFlushManager();

    // Message queue implementation to work with the Django store
    fluid.defaults("clusive.djangoMessageQueue", {
        gradeNames: ["clusive.messageQueue"],
        config: {
            // Where and how to send messages to when trying to flush
            target: {
                url: '/messagequeue/',
                method: "POST"
            },
            flushInterval: "@expand:{that}.getFlushInterval(20000)",
            flushIntervalOverrideKey: "clusive.messageQueue.config.flushInterval",
            lastQueueFlushInfoKey: "clusive.messageQueue.log.lastQueueFlushInfo",
            logoutLinkSelector: "#logoutLink"
        },
        components: {
            logoutFlushManager: "{logoutFlushManager}"
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
            getFlushInterval: {
                funcName: "clusive.djangoMessageQueue.getFlushInterval",
                args: ["{arguments}.0", "{that}.options.config.flushIntervalOverrideKey"]
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
            },
            setlastQueueFlushInfo: {
                funcName: "clusive.djangoMessageQueue.setlastQueueFlushInfo",
                args: ["{arguments}.0", "{that}.options.config.lastQueueFlushInfoKey"]
            }
        },
        listeners: {
            "onCreate.attachLogoutEvents": {
                funcName: "clusive.djangoMessageQueue.attachLogoutEvents",
                args: ["{that}"]
            },
            "onCreate.registerWithLogoutFlushManager": {
                funcName: "clusive.djangoMessageQueue.registerWithLogoutFlushManager",
                args: ["{logoutFlushManager}"]
            },
            "logoutFlushComplete.doLogout": {
                funcName: "clusive.djangoMessageQueue.doLogout",
                args: ["{that}", "{arguments}.0", "{arguments}.1"]
            }                        
        }
    });

    clusive.djangoMessageQueue.registerWithLogoutFlushManager = function (logoutFlushManager) {
        logoutFlushManager.numberOfQueues = logoutFlushManager.numberOfQueues+1;
    };

    clusive.djangoMessageQueue.getFlushInterval = function (defaultInterval, flushIntervalOverrideKey) {        
        var flushIntervalOverrideValue = window.localStorage.getItem(flushIntervalOverrideKey);        
        if(flushIntervalOverrideValue) {
            console.log("flushIntervalOverrideValue found", flushIntervalOverrideValue);
            return flushIntervalOverrideValue;
        } else {
            return defaultInterval;
        }        
    }            

    clusive.djangoMessageQueue.setlastQueueFlushInfo = function(returnMessage, lastQueueFlushInfoKey) {        
        var flushInfo = {
            returnMessage: returnMessage,
            timestamp: new Date().toISOString()
        }
        window.localStorage.setItem(lastQueueFlushInfoKey, JSON.stringify(flushInfo));
    }

    clusive.djangoMessageQueue.logoutFlush = function (that) {           
        if(that.isQueueEmpty()) {
            // Mark flush complete on the logoutFlushManger
            that.logoutFlushManager.completedFlushes = that.logoutFlushManager.completedFlushes+1;
        } else {
            clusive.messageQueue.flushQueue(that, that.setupLogoutFlushPromise);
        }
    }    

    clusive.djangoMessageQueue.setupLogoutFlushPromise = function (that, promise) {        
        promise.then(
            function(value) {                
                that.events.queueFlushSuccess.fire(value);
                that.logoutFlushManager.completedFlushes = that.logoutFlushManager.completedFlushes+1;
                that.events.logoutFlushComplete.fire(that.logoutFlushManager.numberOfQueues, that.logoutFlushManager.completedFlushes);                
            },
            function(error) {                
                that.events.queueFlushFailure.fire(error);
                that.logoutFlushManager.completedFlushes = that.logoutFlushManager.completedFlushes+1;
                that.events.logoutFlushComplete.fire(that.logoutFlushManager.numberOfQueues, that.logoutFlushManager.completedFlushes);                
            })    
    }

    clusive.djangoMessageQueue.attachLogoutEvents = function (that) {
        var logoutLinkSelector = that.options.config.logoutLinkSelector;        
                
        $(logoutLinkSelector).click(
            function (e) {                                                    
                $(logoutLinkSelector).text("Saving changes...").fadeIn();                    
                e.preventDefault();
                that.logoutFlush();                   
            }
        );
    };

    clusive.djangoMessageQueue.doLogout = function (that, numberOfQueues, completedFlushes) {        
        console.log("doLogout", that, numberOfQueues, completedFlushes);
        if(completedFlushes >= numberOfQueues) {
            PageTiming.reportEndTime(); 
            var logoutLinkSelector = that.options.config.logoutLinkSelector;
            $(logoutLinkSelector).text("Logging out").fadeIn();        
            window.location = $(logoutLinkSelector).attr("href");
        }
    }

    // Concrete implementation of the queue flushing that works with 
    // the server-side message queue
    clusive.djangoMessageQueue.flushQueueImpl = function (that, flushPromise) {
        // Don't flush queue if we don't have a username
        if(!DJANGO_USERNAME) return;        
        that.sendingQueue.username = DJANGO_USERNAME;
        $.ajax(that.options.config.target.url, {
            method: that.options.config.target.method,
            headers: {
                'X-CSRFToken': DJANGO_CSRF_TOKEN
            },
            data: JSON.stringify(that.sendingQueue)
        })
            .done(function(data) {
                that.setlastQueueFlushInfo(data);
                flushPromise.resolve({"success": 1});
            })
            .fail(function(err) {
                that.setlastQueueFlushInfo(err);
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