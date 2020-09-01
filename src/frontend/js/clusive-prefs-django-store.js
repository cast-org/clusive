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
        },
        invokers: {
            flushQueueImpl: {
                funcName: "clusive.djangoMessageQueue.flushQueueImpl"                
            },
            wrapMessage: {
                funcName: "clusive.djangoMessageQueue.wrapMessage",
                args: ["{arguments}.0"]
            }            
        }
    });

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
                args: ["{arguments}.0", "{arguments}.1", "{that}.messageQueue"]
            }
        },
        invokers: {
            set: {
                args: ['{that}', '{arguments}.0', '{arguments}.1', '{that}.options.storeConfig']
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
            // Implement debounce here
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

    clusive.prefs.djangoStore.setUserPreferences = function(model, directModel, messageQueue) {
        console.debug('clusive.prefs.djangoStore.setUserPreferences', directModel, model, messageQueue);
        
        // TODO: switch this over to use the messageQueue as well
        if ($.isEmptyObject(model)) {
            var resetURL = directModel.resetURL;
            $.ajax(resetURL, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': DJANGO_CSRF_TOKEN
                },
                data: JSON.stringify({
                    adopt: 'default'
                })
            })
                .done(function(data) {
                    console.debug('resetting preferences to default', data);
                    clusive.prefs.djangoStore.getUserPreferences(directModel);
                })
                .fail(function(jqXHR, textStatus, errorThrown) {
                    console.error('an error occured trying to reset preferences', jqXHR, textStatus, errorThrown);
                });
        } else {
            messageQueue.add({"type": "PC", "preferences": fluid.get(model, 'preferences')})          
        }
    };
}(fluid_3_0_0));