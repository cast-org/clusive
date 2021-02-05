/* global cisl, clusive, fluid_3_0_0, gpii, DJANGO_STATIC_ROOT, DJANGO_CSRF_TOKEN */

(function(fluid) {
    'use strict';

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
            // Holds the initial model (defaults) from the prefs editor
            initialModel: {                
            },
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
                type: "clusive.djangoMessageQueue",
                options: {
                    config: {                        
                        localStorageKey: "clusive.messageQueue.preferenceChanges",
                        lastQueueFlushInfoKey: "clusive.messageQueue.preferenceChanges.log.lastQueueFlushInfo"
                    }
                }
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
                args: ["{arguments}.0", "{arguments}.1", "{that}.messageQueue", "{that}.initialModel"]
            }
        },
        invokers: {
            set: {
                args: ['{that}', '{arguments}.0', '{arguments}.1', '{that}.options.storeConfig']
            },
            adopt: {
                funcName: 'clusive.prefs.djangoStore.adoptPreferenceSet',
                args: ['{arguments}.0', "{that}.messageQueue", "{that}"]
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

    clusive.prefs.djangoStore.adoptPreferenceSet = function(prefSetName, messageQueue, that) {
        console.log('clusive.prefs.djangoStore.adoptPreferenceSet');
        var adoptURL = that.options.storeConfig.resetURL;
        $.ajax(adoptURL, {
            method: 'POST',
            headers: {
                'X-CSRFToken': DJANGO_CSRF_TOKEN
            },
            data: JSON.stringify({
                adopt: prefSetName,
                eventId: PAGE_EVENT_ID
            })
        })
            .done(function(adoptSet) {
                console.debug('adopting preference from preference set', adoptSet);
                var prefsPromise = that.get();
                prefsPromise.then(function (currentPrefs) {
                    var updatedPreferences = {};
                    $.extend(updatedPreferences, currentPrefs.preferences, adoptSet);
                    console.log("updatedPreferences", updatedPreferences);
                    messageQueue.add({"type": "PC", "preferences": updatedPreferences, "readerInfo": clusiveContext.reader.info, "eventId": PAGE_EVENT_ID});
                    that.events.onPreferencesSetAdopted.fire(updatedPreferences);
                });
            })
            .fail(function(jqXHR, textStatus, errorThrown) {
                console.error('an error occured trying to adopt a preference set', jqXHR, textStatus, errorThrown);
            });
    };

    clusive.prefs.djangoStore.setUserPreferences = function(model, directModel, messageQueue, initialModel) {        
        console.debug('clusive.prefs.djangoStore.setUserPreferences', directModel, model, messageQueue, initialModel);
        // Merge non-default preferences (the ones relayed from the editor) with defaults for storage
        var prefsToSave = $.extend({}, fluid.get(initialModel, "preferences"), fluid.get(model, "preferences"));        
        console.debug("prefsToSave would be: ", prefsToSave);
        messageQueue.add({"type": "PC", "preferences": prefsToSave, "readerInfo": clusiveContext.reader.info, "eventId": PAGE_EVENT_ID});
    };
    
}(fluid_3_0_0));