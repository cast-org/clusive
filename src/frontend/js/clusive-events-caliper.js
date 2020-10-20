'use strict'

var caliperMessageQueue = clusive.djangoMessageQueue();

var caliperEventTypes = {
    TOOL_USE_EVENT: "TOOL_USE_EVENT"
}

var trackedControlInteractions = [
    {
        selector: ".btn-tool.tts-play",
        handler: "click",
        control: "tts-play",
        value: "clicked"
    }
];

var addControlInteractionToQueue = function (control, value) {
    console.debug("Adding control interaction to queue: ", control, value)
    caliperMessageQueue.add({
        "type": "CE", 
        "caliperEvent": {"type": caliperEventTypes.TOOL_USE_EVENT, "control": control, "value": value}
    });
};

$(document).ready(function () {
    trackedControlInteractions.forEach(function (interactionDef, i) {        
        var control = $(interactionDef.selector);
        var handler = interactionDef.handler;
        $(interactionDef.selector).click(function () {                    
            addControlInteractionToQueue(interactionDef.control, interactionDef.value);
        })
    });
})