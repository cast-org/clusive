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
    save: function(url, data) {
        clusiveAutosave.queue.add({"type": "AS", "url": url, "data": data});
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
                console.log("local data for url: " + url + " found", latestLocalData);
                callback(latestLocalData);
            } else {                   
                console.log("No local data for url: " + url + ", trying to get from server");
                $.get(url, function(data) {
                    console.log("Found data on server for url: " + url);
                    callback(data);                    
                }).fail(function(error) {
                    if (error.status === 404) {
                        console.debug('No matching data on server for url: ' + url);
                    } else {
                        console.warn('failed to get data: ', error.status);
                    }
                });
            }                 
        }                
};