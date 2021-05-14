/* Code for comprehension and affect assessments */
/* global clusive, clusiveContext, PAGE_EVENT_ID, DJANGO_CSRF_TOKEN, fluid, D2Reader */
/* exported clusiveAutosave */

var clusiveAutosave = {
    queue: clusive.djangoMessageQueue({
            config: {                        
                localStorageKey: "clusive.messageQueue.autosave",
                lastQueueFlushInfoKey: "clusive.messageQueue.autosave.log.lastQueueFlushInfo"
            }
        }),
    // Test if data is equivalent for autosave purposes        
    isEquivalentData: function (oldData, newData) {        
        var isEquivalent = true;
        if(!oldData || !newData) {
            isEquivalent = false;
        }
        Object.keys(newData).forEach(function (key) {
            if(newData[key] !== oldData[key]) {                
                isEquivalent = false;                
            }
        });        
        return isEquivalent;                
    },
    save: function(url, data) {        
        var lastData = clusiveAutosave.lastDataCache[url];        
        var isNewData = !clusiveAutosave.isEquivalentData(lastData, data);                
        if(isNewData) {
            console.debug("adding changed data for URL " + url + "to autosave queue: ", data);
            clusiveAutosave.queue.add({"type": "AS", "url": url, "data": JSON.stringify(data)});
            clusiveAutosave.lastDataCache[url] = data; 
        } else {
            console.debug("no changed data for URL " + url + ", not adding to autosave queue", data)
        }
    },
    retrieve: 
        function(url, callback) {
            var hasLocal = false;                
            var autosaveMessages = [].concat(clusiveAutosave.queue.getMessages()).filter(function (item) {                    
                    if(item.content.type === "AS" && item.content.url === url) {
                        return true;
                    }                    
            });
            
            if(autosaveMessages.length > 0) {                                        
                var latestLocalData = JSON.parse(autosaveMessages.pop().content.data);                
                callback(latestLocalData);
                clusiveAutosave.lastDataCache[url] = latestLocalData;
            } else {                   
                console.debug("No local data for url: " + url + ", trying to get from server");
                $.get(url, function(data) {                    
                    callback(data);                    
                    clusiveAutosave.lastDataCache[url] = data;
                }).fail(function(error) {
                    if (error.status === 404) {
                        console.debug('No matching data on server for url: ' + url);
                    } else {
                        console.warn('failed to get data: ', error.status);
                    }
                });
            }                 
        },
    // Maintains per-url record of data to avoid unneeded autosaving
    lastDataCache: {
    }
};