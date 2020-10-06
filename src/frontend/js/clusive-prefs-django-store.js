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
            flushInterval: 60000,
            logoutLinkSelector: "#logoutLink"
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
            }          
        },
        listeners: {
            "onCreate.attachLogoutEvents": {
                funcName: "clusive.djangoMessageQueue.attachLogoutEvents",
                args: ["{that}"]
            }
        }
    });

    // Check if both the queue and the sending queue are empty 
    // (no outstanding or in-flight messages)
    clusive.djangoMessageQueue.isQueueEmpty = function (that) {        
        return (that.queue.length === 0 && $.isEmptyObject(that.sendingQueue));
    };

    clusive.djangoMessageQueue.attachLogoutEvents = function (that) {
        var logoutLinkSelector = that.options.config.logoutLinkSelector;        
        
        $(logoutLinkSelector).mouseenter(
            function () {   
                if(! that.isQueueEmpty()) {
                    console.debug("Mouse entered logout link, flushing message queue.");
                    that.flush();        
                }
            }
        );
        
        $(logoutLinkSelector).focus(
            function () {      
                if(! that.isQueueEmpty()) {
                    console.debug("Keyboard focus entered logout link, flushing message queue.");  
                    that.flush();
                }
            }
        );
    };

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

    fluid.defaults('clusive.prefs.djangoStore', {
        gradeNames: ['fluid.dataSource'],
        storeConfig: {
            getURL: '/account/prefs',
            setURL: '/account/prefs',
            resetURL: '/account/prefs/profile',
            // In milliseconds, helps prevent repeated calls on initial construction
            debounce: 1000
        },
        events: {
            onPreferencesSetAdopted: null
        },
        members: {
            // Holds the time a request was last made
            lastRequestTime: null,
            // Holds the last response for reuse if within the debounce time
            lastResponse: null,
            // Holds whether or not a request is in flight
            requestIsInFlight: false
        },
        components: {
            encoding: {
                type: 'fluid.dataSource.encoding.none'
            },            
            messageQueue: {
                type: "clusive.djangoMessageQueue"
            }
            
        },
        listeners: {
            'onRead.impl': {
                listener: 'clusive.prefs.djangoStore.getUserPreferences',
                args: ['{arguments}.1', "{that}.messageQueue", "{that}.lastRequestTime", "{that}"]
            }
        },
        invokers: {
            get: {
                args: ['{that}', '{arguments}.0', '{that}.options.storeConfig']
            }
        }
    });

    fluid.defaults('clusive.prefs.djangoStore.writable', {
        gradeNames: ['fluid.dataSource.writable'],
        listeners: {
            'onWrite.impl': {
                listener: 'clusive.prefs.djangoStore.setUserPreferences',
                args: ["{arguments}.0", "{arguments}.1", "{that}.messageQueue", "{that}.lastRequestTime", "{that}"]
            }
        },
        invokers: {
            set: {
                args: ['{that}', '{arguments}.0', '{arguments}.1', '{that}.options.storeConfig']
            },
            adopt: {
                funcName: 'clusive.prefs.djangoStore.adoptPreferenceSet',
                args: ['{arguments}.0', "{that}.messageQueue", "{that}.lastRequestTime", "{that}"]
            }
        }
    });

    fluid.makeGradeLinkage('clusive.prefs.djangoStore.linkage', ['fluid.dataSource.writable', 'clusive.prefs.djangoStore'], 'clusive.prefs.djangoStore.writable');

    clusive.prefs.djangoStore.getUserPreferences = function(directModel, messageQueue, lastRequestTime, that) {
        console.debug('clusive.prefs.djangoStore.getUserPreferences', directModel, messageQueue);

        var djangoStorePromise = fluid.promise();

        var preferenceChangeMessages = [].concat(messageQueue.queue).filter(function (item) {
            if(item.content.type === "PC") {
                return true;
            }
        }) 
        
        if(preferenceChangeMessages.length > 0) {
            // Check for any preference changes in the message queue; 
            // if there are any, the latest is them, not what's 
            // available from the server; return the last preference change 
            // from the queue
            var latestPreferences = preferenceChangeMessages.pop().content.preferences;
            console.debug("Get user preferences from the outstanding message queue", latestPreferences);
            djangoStorePromise.resolve({
                preferences: latestPreferences
            });            
            
        } else {
            // Debounce implementation
            var currentTime = new Date();
            var timeDiff;
            if(lastRequestTime) {
                timeDiff = currentTime.getTime() - lastRequestTime.getTime();
            }

            var debounce = directModel.debounce;
            
            var getURL = directModel.getURL;
            
            // Use cached result if within debounce time
            if(timeDiff < debounce && that.lastResponse) {
                console.debug('Get user preferences from cache of last result');
                djangoStorePromise.resolve({
                    preferences: that.lastResponse
                });
            } else if(that.requestIsInFlight) {
                djangoStorePromise.reject('Won\'t get user preferences from server, another GET request is currently in flight')                
            } else {
                that.requestIsInFlight = true;
                $.get(getURL, function(data) {
                    that.requestIsInFlight = false;
                    console.debug('Get user preferences from the server ', getURL);
                    console.debug('Received preferences: ', data);
                    that.lastResponse = data;
                    that.lastRequestTime = currentTime;
    
                    djangoStorePromise.resolve({
                        preferences: data
                    });
                }).fail(function(error) {
                    that.requestIsInFlight = false;
                    console.error('Error getting preferences:', error);
                    djangoStorePromise.reject('error');
                });
            }                            
        }
        return djangoStorePromise;
    };

    clusive.prefs.djangoStore.adoptPreferenceSet = function(prefSetName, messageQueue, lastRequestTime, that) {
        console.log('clusive.prefs.djangoStore.adoptPreferenceSet');
        var adoptURL = that.options.storeConfig.resetURL;
        $.ajax(adoptURL, {
            method: 'POST',
            headers: {
                'X-CSRFToken': DJANGO_CSRF_TOKEN
            },
            data: JSON.stringify({
                adopt: prefSetName
            })
        })
            .done(function(adoptSet) {                    
                console.debug('adopting preference from preference set', adoptSet);    
                var prefsPromise = that.get();                
                prefsPromise.then(function (currentPrefs) {
                    var updatedPreferences = {};
                    $.extend(updatedPreferences, currentPrefs.preferences, adoptSet);
                    console.log("updatedPreferences", updatedPreferences);
                    messageQueue.add({"type": "PC", "preferences": updatedPreferences});
                    // this is not a good way to do this
                    clusivePrefs.prefsEditorLoader.applier.change("preferences", updatedPreferences);
                    that.events.onPreferencesSetAdopted.fire();
                });                                
            })
            .fail(function(jqXHR, textStatus, errorThrown) {
                console.error('an error occured trying to adopt a preference set', jqXHR, textStatus, errorThrown);
            });     
    };

    clusive.prefs.djangoStore.setUserPreferences = function(model, directModel, messageQueue, lastRequestTime, that) {
        console.debug('clusive.prefs.djangoStore.setUserPreferences', directModel, model, messageQueue);        
        messageQueue.add({"type": "PC", "preferences": fluid.get(model, 'preferences')});                  
    };
}(fluid_3_0_0));