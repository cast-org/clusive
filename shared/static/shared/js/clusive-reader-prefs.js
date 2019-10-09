/* global fluid, cisl */

(function (fluid) {
    "use strict";
    
    fluid.defaults("cisl.prefs.readerPreferencesBridge", {
        gradeNames: ["fluid.modelComponent"],        
        model: {
            // Must be linked to a preferences editor model instance
            preferences: null,
            // Contains values mapped from the preferences editor model 
            // to the Reader equivalents, with transforms as defined 
            // in model relay block
            readerPreferences: {                
            }
        },    
        modelRelay: {
            "readerPrefences.fontSize": {
                target: "readerPreferences.fontSize",
                backward: {
                    excludeSource: "*"
                },
                singleTransform: {
                    type: "fluid.transforms.valueMapper",
                    defaultInput: "{that}.model.preferences.fluid_prefs_textSize",
                    match: [
                        {
                            inputValue: "small",
                            outputValue: 75
                        },
                        {
                            inputValue: "medium",
                            outputValue: 100
                        },
                        {
                            inputValue: "large",
                            outputValue: 150
                        },                        {
                            inputValue: "x-large",
                            outputValue: 200
                        }
                    ]
                }
            },
            "readerPreferences.letterSpacing": {
                target: "readerPreferences.letterSpacing",
                backward: {
                    excludeSource: "*"
                },
                singleTransform: {
                    type: "fluid.transforms.binaryOp",
                    "left": "{that}.model.preferences.fluid_prefs_letterSpace",
                    "operator": "-",                    
                    "right": 0.999
                }
            },
            "readerPreferences.lineHeight": {
                target: "readerPreferences.lineHeight",
                backward: {
                    excludeSource: "*"
                },
                singleTransform: {
                    type: "fluid.transforms.value",
                    "input": "{that}.model.preferences.fluid_prefs_lineSpace"
                }
            },
            "readerPreferences.appearance": {
                target: "readerPreferences.appearance",
                backward: {
                    excludeSource: "*"
                },
                singleTransform: {
                    type: "fluid.transforms.valueMapper",
                    defaultInput: "{that}.model.preferences.fluid_prefs_contrast",
                    match: [
                        {
                            inputValue: "default",
                            outputValue: "day"
                        },
                        {
                            inputValue: "wb",
                            outputValue: "night"
                        },
                        {
                            inputValue: "bw",
                            outputValue: "day"
                        }
                    ]
                }                
            }
        },
        modelListeners: {
            "readerPreferences.fontSize": {
                func: "cisl.prefs.readerPreferencesBridge.enactPreferenceToReader",
                args: ["{change}.value", "fontSize"]
            },                      
            "readerPreferences.letterSpacing": {
                 func: "cisl.prefs.readerPreferencesBridge.enactPreferenceToReader",                
                 args: ["{change}.value", "letterSpacing"]
            },
            "readerPreferences.lineHeight": {
                func: "cisl.prefs.readerPreferencesBridge.enactPreferenceToReader",                
                args: ["{change}.value", "lineHeight"]
           },
            "preferences.fluid_prefs_textFont": {
                func: "cisl.prefs.readerPreferencesBridge.enactReaderTextFont",
                args: ["{change}.value"]
            },
            "readerPreferences.appearance": {
                func: "cisl.prefs.readerPreferencesBridge.enactPreferenceToReader",                
                args: ["{change}.value", "appearance"]
            }            
        }
    });

    cisl.prefs.readerPreferencesBridge.getReaderInstance = function () {
        var readerDefined = typeof D2Reader;      
        
        if(readerDefined !== "undefined") {
            return D2Reader
        } else return null;
    }

    cisl.prefs.readerPreferencesBridge.setReadiumCSSUserVariable = function (name, value) {
        var readerHtmlElem = $("#D2Reader-Container").find("iframe").contents().find("html");
        readerHtmlElem.css(name, value);            
    }

    cisl.prefs.readerPreferencesBridge.applyUserSetting = function (settingName, settingValue) {
        var reader = cisl.prefs.readerPreferencesBridge.getReaderInstance();
        if(reader) {                      
            var settingsObj = 
            {
                [settingName]:settingValue
            };
            reader.applyUserSettings(settingsObj);
        }    
    }

    cisl.prefs.readerPreferencesBridge.enactPreferenceToReader = function (changeValue, readerSetting) {             
        cisl.prefs.readerPreferencesBridge.applyUserSetting(readerSetting, changeValue);
    }

    cisl.prefs.readerPreferencesBridge.enactReaderTextFont = function (change) {
        
        var reader = cisl.prefs.readerPreferencesBridge.getReaderInstance();

        var fontFamilyMap = {
            "default": "Original",
            "times": "Georgia, Times, Times New Roman, serif",
            "arial": "Arial, Helvetica",
            "verdana": "Verdana",
            "comic": "Comic Sans MS, sans-serif",
            "open-dyslexic": "opendyslexic"
        };
        

        // TODO: have to find another way to do this - gets reset by the 
        // reader whenever applyUserSettings is called, though works
        // when preference is itself applied from the panel
        if(reader) {                                    
            cisl.prefs.readerPreferencesBridge.applyUserSetting("fontFamily", fontFamilyMap[change]);
        }
    }

})(fluid_3_0_0);