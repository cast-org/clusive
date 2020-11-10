'use strict'

var addControlInteractionToQueue = function (control, value) {    
    console.debug("Adding control interaction to queue: ", control, value)
    clusiveEvents.messageQueue.add({
        "type": "CE", 
        "caliperEvent": {"type": clusiveEvents.caliperEventTypes.TOOL_USE_EVENT, "control": control, "value": value},
        "readerInfo": clusiveContext.reader.info,
        "eventId": PAGE_EVENT_ID
    });
};

var clusiveEvents = {
    messageQueue: clusive.djangoMessageQueue(),    
    caliperEventTypes: {
        TOOL_USE_EVENT: "TOOL_USE_EVENT"
    },    
    trackedControlInteractions: [
        {
            selector: ".btn.tts-play",
            handler: "click",
            control: "tts-play",
            value: "clicked"
        },
        {
            selector: ".btn.tts-pause",
            handler: "click",
            control: "tts-pause",
            value: "clicked"
        },
        {
            selector: ".btn.tts-resume",
            handler: "click",
            control: "tts-resume",
            value: "clicked"
        },
        {
            selector: ".btn.tts-stop",
            handler: "click",
            control: "tts-stop",
            value: "clicked"
        }         
    ],
    addControlInteractionToQueue: addControlInteractionToQueue    
}

$(document).ready(function () {    

    // Build additional control interaction objects here from any data-clusive-event attributes on page markup
    // synax: data-clusive-event="[handler]|[control]|[value]"
    // example: data-clusive-event="click|settings-sidebar|opened"    
    $("*[data-cle-handler]").each(function (i, control) {
        // data-clusive-event attribute 
        var elm = $(control);
        var eventHandler = $(control).attr("data-cle-handler");
        var eventControl = $(control).attr("data-cle-control");        
        var eventValue = $(control).attr("data-cle-value");        
        console.debug("data-cle-handler attribute found", elm, eventHandler, eventControl, eventValue)
        if(eventHandler !== undefined && eventControl !== undefined && eventValue !== undefined) {
            var interactionDef = {
                selector: elm,
                handler: eventHandler,
                control: eventControl,
                value: eventValue
            }
            clusiveEvents.trackedControlInteractions.push(interactionDef);        
        } else {
            console.debug("tried to add event logging, but missing a needed data-cle-* attribute on the element: ", elm)
        }
        
    });

    // Set up events control interactions here
    clusiveEvents.trackedControlInteractions.forEach(function (interactionDef, i) {              
        var control = $(interactionDef.selector);
        console.debug("Event for control tracking: ", interactionDef, control)      
        var handler = interactionDef.handler;
        $(interactionDef.selector)[handler](function () {                    
            addControlInteractionToQueue(interactionDef.control, interactionDef.value);
        })
    });            
})