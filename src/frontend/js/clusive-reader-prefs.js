/* global fluid_3_0_0, cisl, d2reader */

/*
    Defines interactions between Clusive preferences and Readium.
 */

(function(fluid) {
    'use strict';

    fluid.defaults('cisl.prefs.readerPreferencesBridge', {
        gradeNames: ['fluid.modelComponent'],
        model: {
            // Must be linked to a preferences editor model instance
            preferences: null,
            // Contains values mapped from the preferences editor model
            // to the Reader equivalents, with transforms as defined
            // in model relay block
            readerPreferences: {}
        },
        modelRelay: {
            'readerPrefences.fontSize': {
                target: 'readerPreferences.fontSize',
                backward: {
                    excludeSource: '*'
                },
                singleTransform: {
                    type: 'fluid.transforms.binaryOp',
                    left: '{that}.model.preferences.fluid_prefs_textSize',
                    operator: '*',
                    right: 100
                }
            },
            'readerPreferences.fontFamily': {
                target: 'readerPreferences.fontFamily',
                backward: {
                    excludeSource: '*'
                },
                singleTransform: {
                    type: 'fluid.transforms.valueMapper',
                    defaultInput: '{that}.model.preferences.fluid_prefs_textFont',
                    match: [
                        {
                            inputValue: 'default',
                            outputValue: 'Original'
                        },
                        {
                            inputValue: 'times',
                            outputValue: 'Georgia, Times, Times New Roman, serif'
                        },
                        {
                            inputValue: 'arial',
                            outputValue: 'Arial, Helvetica'
                        }, {
                            inputValue: 'verdana',
                            outputValue: 'Verdana'
                        },
                        {
                            inputValue: 'comic',
                            outputValue: 'Comic Sans MS, sans-serif'
                        }, {
                            inputValue: 'open-dyslexic',
                            outputValue: 'OpenDyslexicRegular'
                        }
                    ]
                }
            },
            'readerPreferences.letterSpacing': {
                target: 'readerPreferences.letterSpacing',
                backward: {
                    excludeSource: '*'
                },
                singleTransform: {
                    type: 'fluid.transforms.binaryOp',
                    left: '{that}.model.preferences.fluid_prefs_letterSpace',
                    operator: '-',
                    right: 0.999
                }
            },
            'readerPreferences.lineHeight': {
                target: 'readerPreferences.lineHeight',
                backward: {
                    excludeSource: '*'
                },
                singleTransform: {
                    type: 'fluid.transforms.value',
                    input: '{that}.model.preferences.fluid_prefs_lineSpace'
                }
            },
            'readerPreferences.appearance': {
                target: 'readerPreferences.appearance',
                backward: {
                    excludeSource: '*'
                },
                singleTransform: {
                    type: 'fluid.transforms.valueMapper',
                    defaultInput: '{that}.model.preferences.fluid_prefs_contrast',
                    match: [
                        {
                            inputValue: 'default',
                            outputValue: 'day'
                        },
                        {
                            inputValue: 'night',
                            outputValue: 'clusive-night'
                        },
                        {
                            inputValue: 'sepia',
                            outputValue: 'clusive-sepia'
                        }
                    ]
                }
            },
            'readerPreferences.tts.rate': {
                target: 'readerPreferences.tts.rate',
                backward: {
                    excludeSource: '*'
                },
                singleTransform: {
                    type: 'fluid.transforms.value',
                    input: '{that}.model.preferences.cisl_prefs_readSpeed'
                }
            },
            'readerPreferences.scroll': {
                target: 'readerPreferences.verticalScroll',
                backward: {
                    excludeSource: '*'
                },
                singleTransform: {
                    type: 'fluid.transforms.valueMapper',
                    defaultInput: '{that}.model.preferences.cisl_prefs_scroll',
                    match: [
                        {
                            inputValue: true,
                            outputValue: 'readium-scroll-on'
                        },
                        {
                            inputValue: false,
                            outputValue: 'readium-scroll-off'
                        }
                    ]
                }
            },
            'readerPreferences.glossary': {
                target: 'readerPreferences.glossary',
                backward: {
                    excludeSource: '*'
                },
                singleTransform: {
                    type: 'fluid.transforms.value',
                    input: '{that}.model.preferences.cisl_prefs_glossary'
                }
            }
        },
        modelListeners: {
            'readerPreferences.fontSize': {
                func: 'cisl.prefs.readerPreferencesBridge.applyUserSetting',
                args: ['fontSize', '{change}.value'],
                excludeSource: "init"
            },
            'readerPreferences.fontFamily': {
                func: 'cisl.prefs.readerPreferencesBridge.applyUserSetting',
                args: ['fontFamily', '{change}.value'],
                excludeSource: "init"
            },
            'readerPreferences.letterSpacing': {
                func: 'cisl.prefs.readerPreferencesBridge.applyUserSetting',
                args: ['letterSpacing', '{change}.value'],
                excludeSource: "init"
            },
            'readerPreferences.lineHeight': {
                func: 'cisl.prefs.readerPreferencesBridge.applyUserSetting',
                args: ['lineHeight', '{change}.value'],
                excludeSource: "init"
            },
            'readerPreferences.appearance': {
                func: 'cisl.prefs.readerPreferencesBridge.applyUserSetting',
                args: ['appearance', '{change}.value'],
                excludeSource: "init"
            },
            'readerPreferences.tts.rate': {
                func: 'cisl.prefs.readerPreferencesBridge.applyUserTTSSetting',
                args: ['rate', '{change}.value'],
                excludeSource: "init"
            },
            'readerPreferences.verticalScroll': {
                func: 'cisl.prefs.readerPreferencesBridge.applyUserSetting',
                args: ['verticalScroll', '{change}.value'],
                excludeSource: "init"
            },
            'readerPreferences.glossary': {
                func: 'cisl.prefs.readerPreferencesBridge.applyGlossarySetting',
                args: ['show', '{change}.value'],
                excludeSource: "init"
            }
        },
        listeners: {
            'onCreate.dispatchCreateEvent': {
                func: 'cisl.prefs.readerPreferencesBridge.dispatchCreateEvent',
                args: ["{that}"]
            }
        }
    });

    cisl.prefs.readerPreferencesBridge.dispatchCreateEvent = function (that) {
        console.debug("cisl.prefs.readerPreferencesBridge.dispatchCreateEvent", that);
        var evt = new CustomEvent("cisl.prefs.readerPreferencesBridge.onCreate", {"bubbles": true, "cancelable": false, "detail": {"readerPreferences": that.model.readerPreferences}});
        document.dispatchEvent(evt);
    }

    cisl.prefs.readerPreferencesBridge.applyUserSetting = function(settingName, settingValue) {
        console.debug('applyUserSetting: ', settingName, settingValue);
        var reader = clusiveContext.reader.instance;
        if (reader && reader.applyUserSettings) {
            var settingsObj =
            {
                [settingName]:settingValue
            };

            reader.applyUserSettings(settingsObj);
        }
    };

    cisl.prefs.readerPreferencesBridge.applyUserTTSSetting = function(ttsSettingName, settingValue) {
        console.debug("cisl.prefs.readerPreferencesBridge.applyUserTTSSetting", ttsSettingName, settingValue)
        var reader = clusiveContext.reader.instance;
        if (reader && reader.applyUserSettings) {
            var settingsObj =
            {
                [ttsSettingName]:settingValue
            };
            reader.applyTTSSettings(settingsObj);
        }
    };

    cisl.prefs.readerPreferencesBridge.applyGlossarySetting = function(settingName, settingValue) {
        console.debug('cisl.prefs.readerPreferencesBridge.applyGlossarySetting', settingName, settingValue)
        var reader = clusiveContext.reader.instance;
        if (reader) {
            if (settingValue) {
                d2reader.showLayer('definitions')
            } else {
                d2reader.hideLayer('definitions')
            }
        }
    }

}(fluid_3_0_0));
