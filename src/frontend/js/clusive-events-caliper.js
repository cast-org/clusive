'use strict'

var addControlInteractionToQueue = function (control, value) {    
    console.debug("Adding control interaction to queue: ", control, value)
    clusiveEvents.messageQueue.add({
        "type": "CE", 
        "caliperEvent": {"type": clusiveEvents.caliperEventTypes.TOOL_USE_EVENT, "control": control, "value": value},
        "readerInfo": clusiveContext.reader.info
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
    $("*[data-clusive-event").each(function (i, control) {
        // data-clusive-event attribute 
        console.debug("data-clusive-event", control)
        var defsValsFromAttr = $(control).attr("data-clusive-event").split("|");
        if(defsValsFromAttr.length < 3) {
            console.debug("invalid data-clusive-event attribute value on control", control);
        }
        var interactionDef = {
            selector: control,
            handler: defsValsFromAttr[0],
            control: defsValsFromAttr[1],
            value: defsValsFromAttr[2]
        }
        clusiveEvents.trackedControlInteractions.push(interactionDef);
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