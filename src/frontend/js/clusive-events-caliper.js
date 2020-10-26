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
    },
    {
        selector: ".btn-tool.tts-pause",
        handler: "click",
        control: "tts-pause",
        value: "clicked"
    },
    {
        selector: ".btn-tool.tts-resume",
        handler: "click",
        control: "tts-resume",
        value: "clicked"
    },
    {
        selector: ".btn-tool.tts-stop",
        handler: "click",
        control: "tts-stop",
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