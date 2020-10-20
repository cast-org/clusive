'use strict'

var caliperMessageQueue = clusive.djangoMessageQueue();

var playButton = $(".btn-tool.tts-play");



caliperMessageQueue.add({
    "type": "CE", 
    "caliperEvent": {"type": "ToolUseEvent"}
});