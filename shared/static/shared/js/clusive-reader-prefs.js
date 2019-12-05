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
                    type: "fluid.transforms.binaryOp",
                    "left": "{that}.model.preferences.fluid_prefs_textSize",
                    "operator": "*",                    
                    "right": 100                  
                }
            },
            "readerPreferences.fontFamily": {
                target: "readerPreferences.fontFamily",
                backward: {
                    excludeSource: "*"
                },
                singleTransform: {
                    type: "fluid.transforms.valueMapper",
                    defaultInput: "{that}.model.preferences.fluid_prefs_textFont",
                    match: [
                        {
                            inputValue: "default",
                            outputValue: "Original"
                        },
                        {
                            inputValue: "times",
                            outputValue: "Georgia, Times, Times New Roman, serif"
                        },
                        {
                            inputValue: "arial",
                            outputValue: "Arial, Helvetica"
                        },                        {
                            inputValue: "verdana",
                            outputValue: "Verdana"
                        },
                        {
                            inputValue: "comic",
                            outputValue: "Comic Sans MS, sans-serif"
                        },                        {
                            inputValue: "open-dyslexic",
                            outputValue: "OpenDyslexicRegular"
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
                            inputValue: "night",
                            outputValue: "night"
                        },
                        {
                            inputValue: "sepia",
                            outputValue: "sepia"
                        }                                          
                    ]
                }                
            }
        },
        modelListeners: {
            "readerPreferences.fontSize": {
                func: "cisl.prefs.readerPreferencesBridge.applyUserSetting",
                args: [ "fontSize", "{change}.value"]
            },           
            "readerPreferences.fontFamily": {
                func: "cisl.prefs.readerPreferencesBridge.applyUserSetting",
                args: ["fontFamily", "{change}.value"]
            },                                  
            "readerPreferences.letterSpacing": {
                 func: "cisl.prefs.readerPreferencesBridge.applyUserSetting",                
                 args: ["letterSpacing", "{change}.value"]
            },
            "readerPreferences.lineHeight": {
                func: "cisl.prefs.readerPreferencesBridge.applyUserSetting",                
                args: ["lineHeight", "{change}.value"]
           },
            "readerPreferences.appearance": {
                func: "cisl.prefs.readerPreferencesBridge.applyUserSetting",                
                args: ["appearance", "{change}.value"]
            }            
        }
    });

    cisl.prefs.readerPreferencesBridge.getReaderInstance = function () {
        var readerDefined = typeof D2Reader;      
        
        if(readerDefined !== "undefined") {
            return D2Reader
        } else return null;
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

})(fluid_3_0_0);