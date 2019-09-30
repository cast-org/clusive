/* global fluid, cisl */

(function (fluid) {
    "use strict";
    
    fluid.defaults("cisl.prefs.reader", {
        gradeNames: ["fluid.modelComponent"],        
        model: {
            // Must be linked to a preferences editor model instance
            preferences: null,
        },
        modelListeners: {
            "preferences.fluid_prefs_textSize": {
                    func: "cisl.prefs.reader.enactReaderTextSize",
                    args: ["{change}.value", "{that}.options.settingMaps.textSizeToFontScale"]
            },                      
            "preferences.fluid_prefs_letterSpace": {
                    func: "{that}.enactReaderLetterSpace",
                    args: ["{change}.value"]
            },
            "preferences.fluid_prefs_lineSpace": {
                func: "{that}.enactReaderLineSpace",
                args: ["{change}.value"]
            },
            "preferences.fluid_prefs_textFont": {
                func: "{that}.enactReaderTextFont",
                args: ["{change}.value"]
            },
            "preferences.fluid_prefs_contrast": {
                func: "{that}.enactReaderContrast",
                args: ["{change}.value"]
            }            
        },
        settingMaps: {
            textSizeToFontScale: {
                "small": 0.75,
                "medium": 1,
                "large": 1.5,
                "x-large": 2                
            }
        },
        invokers: {
            enactReaderLetterSpace: {
                funcName: "cisl.prefs.reader.enactReaderLetterSpace",
                args: ["{arguments}.0"]                
            },
            enactReaderLineSpace: {
                funcName: "cisl.prefs.reader.enactReaderLineSpace",
                args: ["{arguments}.0"]                
            },
            enactReaderTextFont: {
                funcName: "cisl.prefs.reader.enactReaderTextFont",
                args: ["{arguments}.0"]                
            },
            enactReaderContrast: {
                funcName: "cisl.prefs.reader.enactReaderContrast",
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


    cisl.prefs.reader.setReadiumCSSUserVariable = function (name, value) {
        var readerHtmlElem = $("#D2Reader-Container").find("iframe").contents().find("html");
        readerHtmlElem.css(name, value);            
    }

    cisl.prefs.reader.applyUserSetting = function (settingName, settingValue) {
        var reader = cisl.prefs.reader.getReaderInstance();
        if(reader) {                      
            var settingsObj = 
            {
                [settingName]:settingValue
            };
            reader.applyUserSettings(settingsObj);
        }    
    }

    cisl.prefs.reader.enactReaderTextSize = function (change, settingsMap) {     
        cisl.prefs.reader.applyUserSetting("fontSize", settingsMap[change] * 100);        
    }

    cisl.prefs.reader.enactReaderLetterSpace = function (change) {    
        var reader = cisl.prefs.reader.getReaderInstance();    
        if(reader) {
            // Reader won't change on a 0 value for this setting
            reader.applyUserSettings({letterSpacing: change - 0.999})            
        }
    }
    
    cisl.prefs.reader.enactReaderLineSpace = function (change) {   
        var reader = cisl.prefs.reader.getReaderInstance();
        if(reader) {            
            reader.applyUserSettings({lineHeight: change})            
        }        
    }

    cisl.prefs.reader.enactReaderTextFont = function (change) {
        
        var reader = cisl.prefs.reader.getReaderInstance();

        var fontFamilyMap = {
            "default": "Original",
            "times": "Georgia, Times, Times New Roman, serif",
            "arial": "Arial",
            "verdana": "Verdana",
            "comic": "Comic Sans MS, sans-serif",
            "open-dyslexic": "opendyslexic"
        };
        
        if(reader) {            
            cisl.prefs.reader.setReadiumCSSUserVariable("--USER__fontFamily", fontFamilyMap[change]);            
        }
    }

    cisl.prefs.reader.enactReaderContrast = function (change) {
        var reader = cisl.prefs.reader.getReaderInstance();
        console.log("enactReaderContrast", change);

        var contrastMap = {
            "default": "day",
            "bw": "day",
            "wb": "night"
        }

        if(reader) {            
            reader.applyUserSettings({appearance: contrastMap[change]})            
        }
    }

})(fluid_3_0_0);

// fluid_prefs_contrast: "default"