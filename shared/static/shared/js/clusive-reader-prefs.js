/* global fluid, cisl */

(function (fluid) {
    "use strict";
    
    fluid.defaults("cisl.prefs.reader", {
        gradeNames: ["fluid.modelComponent"],        
        model: {
            // Must be linked to a preferences editor model instance
            preferences: null
        },
        modelListeners: {
            "preferences.fluid_prefs_textSize": {
                    func: "{that}.enactReaderTextSize",
                    args: ["{change}.value"]
            },                      
            "preferences.fluid_prefs_letterSpace": {
                    func: "{that}.enactReaderLetterSpace",
                    args: ["{change}.value"]
            },
            "preferences.fluid_prefs_lineSpace": {
                func: "{that}.enactReaderLineSpace",
                args: ["{change}.value"]
        }                                                                                        
        },
        invokers: {
            enactReaderTextSize: {
                funcName: "cisl.prefs.reader.enactReaderTextSize",
                args: ["{arguments}.0"]
            },
            enactReaderLetterSpace: {
                funcName: "cisl.prefs.reader.enactReaderLetterSpace",
                args: ["{arguments}.0"]                
            },
            enactReaderLineSpace: {
                funcName: "cisl.prefs.reader.enactReaderLineSpace",
                args: ["{arguments}.0"]                
            }            
        }
    });

    cisl.prefs.reader.getReaderInstance = function () {
        var readerDefined = typeof D2Reader;      
        
        if(readerDefined !== "undefined") {
            return D2Reader
        } else return null;
    }

    cisl.prefs.reader.enactReaderTextSize = function (change) {     
        var reader = cisl.prefs.reader.getReaderInstance();
        var fontScaleMap = {
            "small": "0.75",
            "medium": "1",
            "large": "1.5",
            "x-large": "2"
        };
        if(reader) {                      
            reader.applyUserSettings({fontSize:fontScaleMap[change] * 100})
        }        
    }

    cisl.prefs.reader.enactReaderLetterSpace = function (change) {    
        var reader = cisl.prefs.reader.getReaderInstance();    
        if(reader) {
            // Reader won't change on a 0 value for this setting
            reader.applyUserSettings({letterSpacing: change - 0.999})            
        }
    }

    // This one doesn't currently work because the lineheight pref
    cisl.prefs.reader.enactReaderLineSpace = function (change) {   
        var reader = cisl.prefs.reader.getReaderInstance();
        if(reader) {            
            reader.applyUserSettings({lineHeight: change})
            console.log("enactReaderLineSpace", change)
        }        
    }

})(fluid_3_0_0);

// fluid_prefs_contrast: "default"

// fluid_prefs_lineSpace: 1
// ​​​
// fluid_prefs_textFont: "verdana"