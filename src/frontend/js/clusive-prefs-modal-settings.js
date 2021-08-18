/* global cisl, fluid_3_0_0 */

/*
    Defines the behavior of the preferences panel and how its markup relates to the defined Fluid preferences.
 */

(function(fluid) {
    'use strict';

    fluid.defaults('cisl.prefs.modalSettings', {
        gradeNames: ['fluid.binder.bindOnCreate'],
        model: {
            modalSettings: {},
            // Linked to preferences editor preferences
            preferences: null
        },
        mappedValues: {
            modalLineSpacingToPreference: {
                short: 1.2,
                default: 1.6,
                tall: 2
            },
            preferenceLineSpaceToModal: {
                1.2: 'short',
                1.6: 'default',
                2: 'tall'
            },
            modalLetterSpacingToPreference: {
                default: 1,
                wide: 1.25,
                wider: 1.5
            },
            preferenceLetterSpaceToModal: {
                1: 'default',
                1.25: 'wide',
                1.5: 'wider'
            },
            modalScrollToPreference: {
                scroll: true,
                paged: false
            },
            preferenceScrollToModal: {
                true: 'scroll',
                false: 'paged'
            }
        },
        invokers: {
            setModalSettingsByPreferences: {
                funcName: 'cisl.prefs.modalSettings.setModalSettingsByPreferences',
                args: ['{that}.model.preferences', '{that}']
            }
        },
        listeners: {
            'onCreate.setupVoiceListing': {
                funcName: 'cisl.prefs.modalSettings.setupVoiceListing',
                args: ['{that}']
            }
        },
        modelListeners: {
            'modalSettings.textSize': {
                funcName: 'cisl.prefs.modalSettings.applyModalSettingToPreference',
                args: ['{change}.value', 'preferences.fluid_prefs_textSize', '{that}'],
                excludeSource: 'init'
            },
            'modalSettings.lineSpacing': {
                funcName: 'cisl.prefs.modalSettings.applyModalSettingToPreference',
                args: ['@expand:cisl.prefs.modalSettings.getMappedValue({change}.value, {that}.options.mappedValues.modalLineSpacingToPreference)', 'preferences.fluid_prefs_lineSpace', '{that}'],
                excludeSource: 'init'
            },
            'modalSettings.letterSpacing': {
                funcName: 'cisl.prefs.modalSettings.applyModalSettingToPreference',
                args: ['@expand:cisl.prefs.modalSettings.getMappedValue({change}.value, {that}.options.mappedValues.modalLetterSpacingToPreference)', 'preferences.fluid_prefs_letterSpace', '{that}'],
                excludeSource: 'init'
            },
            'modalSettings.font': {
                funcName: 'cisl.prefs.modalSettings.applyModalSettingToPreference',
                args: ['{change}.value', 'preferences.fluid_prefs_textFont', '{that}'],
                excludeSource: 'init'
            },
            'modalSettings.color': {
                funcName: 'cisl.prefs.modalSettings.applyModalSettingToPreference',
                args: ['{change}.value', 'preferences.fluid_prefs_contrast', '{that}'],
                excludeSource: 'init'
            },
            'modalSettings.glossary': {
                funcName: 'cisl.prefs.modalSettings.applyModalSettingToPreference',
                args: ['{change}.value', 'preferences.cisl_prefs_glossary', '{that}'],
                excludeSource: 'init'
            },
            'modalSettings.readSpeed': {
                funcName: 'cisl.prefs.modalSettings.applyModalSettingToPreference',
                args: ['{change}.value', 'preferences.cisl_prefs_readSpeed', '{that}'],
                excludeSource: 'init'
            },
            'modalSettings.translationLanguage': {
                funcName: 'cisl.prefs.modalSettings.applyModalSettingToPreference',
                args: ['{change}.value', 'preferences.cisl_prefs_translationLanguage', '{that}'],
                excludeSource: 'init'
            },
            'modalSettings.readVoice': {
                funcName: 'cisl.prefs.modalSettings.handleChosenVoiceSetting',
                args: ['{change}.value', '{that}'],
                excludeSource: 'init'
            },
            'modalSettings.scroll': {
                funcName: 'cisl.prefs.modalSettings.applyModalSettingToPreference',
                args: ['@expand:cisl.prefs.modalSettings.getMappedValue({change}.value, {that}.options.mappedValues.modalScrollToPreference)',
                    'preferences.cisl_prefs_scroll', '{that}'],
                excludeSource: 'init'
            },
            'preferences': {
                func: '{that}.setModalSettingsByPreferences',
                excludeSource: 'applyModalSettingToPreference'
            }
        },
        selectors: {
            textSize: '.cislc-modalSettings-textSize',
            lineSpacing: '.cislc-modalSettings-lineSpacing',
            letterSpacing: '.cislc-modalSettings-letterSpacing',
            font: '.cislc-modalSettings-font',
            color: '.cislc-modalSettings-color',
            glossary: '.cislc-modalSettings-glossary',
            scroll: '.cislc-modalSettings-scroll',
            readSpeed: '.cislc-modalSettings-readSpeed',
            readVoice: '.cislc-modalSettings-readVoice',
            resetDisplay: '.cislc-modalSettings-reset-display',
            resetReading: '.cislc-modalSettings-reset-reading',
            languageSelect: '.cislc-modalSettings-languageSelect',            
            voiceButton: '.voice-button'
        },
        bindings: {
            textSize: 'modalSettings.textSize',
            lineSpacing: 'modalSettings.lineSpacing',
            letterSpacing: 'modalSettings.letterSpacing',
            font: 'modalSettings.font',
            color: 'modalSettings.color',
            readVoice: 'modalSettings.readVoice',
            readSpeed: 'modalSettings.readSpeed',
            scroll: 'modalSettings.scroll',
            languageSelect: 'modalSettings.translationLanguage',
            glossaryCheckbox: {
                selector: 'glossary',
                path: 'modalSettings.glossary',
                rules: {
                    domToModel: {
                        '': {
                            transform: {
                                type: 'fluid.binder.transforms.checkToBoolean',
                                inputPath: ''
                            }
                        }
                    },
                    modelToDom: {
                        '': {
                            transform: {
                                type: 'fluid.binder.transforms.booleanToCheck',
                                inputPath: ''
                            }
                        }
                    }
                }
            }

        }
    });

    cisl.prefs.modalSettings.getMappedValue = function(changedValue, map) {
        return map[changedValue];
    };

    cisl.prefs.modalSettings.applyModalSettingToPreference = function(changedValue, path, that) {
        that.applier.change(path, changedValue, "ADD", "applyModalSettingToPreference");
        cisl.prefs.dispatchPreferenceUpdateEvent();
    };

    cisl.prefs.modalSettings.setModalSettingsByPreferences = function(preferences, that) {

        that.applier.change('modalSettings.textSize', fluid.get(preferences, 'fluid_prefs_textSize'));

        that.applier.change('modalSettings.font', fluid.get(preferences, 'fluid_prefs_textFont'));

        that.applier.change('modalSettings.lineSpacing', cisl.prefs.modalSettings.getMappedValue(fluid.get(preferences, 'fluid_prefs_lineSpace'), that.options.mappedValues.preferenceLineSpaceToModal));

        that.applier.change('modalSettings.letterSpacing', cisl.prefs.modalSettings.getMappedValue(fluid.get(preferences, 'fluid_prefs_letterSpace'), that.options.mappedValues.preferenceLetterSpaceToModal));

        that.applier.change('modalSettings.color', fluid.get(preferences, 'fluid_prefs_contrast'));

        that.applier.change('modalSettings.glossary', fluid.get(preferences, 'cisl_prefs_glossary'));

        that.applier.change('modalSettings.scroll', cisl.prefs.modalSettings.getMappedValue(fluid.get(preferences, 'cisl_prefs_scroll'), that.options.mappedValues.preferenceScrollToModal));

        that.applier.change('modalSettings.readSpeed', fluid.get(preferences, 'cisl_prefs_readSpeed'));

        cisl.prefs.modalSettings.handleReadVoicesPreference(fluid.get(preferences, 'cisl_prefs_readVoices'), that);

        that.applier.change('modalSettings.translationLanguage', fluid.get(preferences, 'cisl_prefs_translationLanguage'));

        cisl.prefs.dispatchPreferenceUpdateEvent();
    };


    cisl.prefs.modalSettings.setupVoiceListing = function (that) {
        console.log("cisl.prefs.modalSettings.setupVoiceListing");
        clusiveTTS.getVoicesForLanguage('en').forEach(function (voice) {
            console.debug("setupVoiceListing for ", voice);
            var optionMarkup = `<option value="${voice.name}">${voice.name}</option>`                        
            var readVoiceSelect = that.locate("readVoice");            
            readVoiceSelect.append(optionMarkup);
        });
        cisl.prefs.modalSettings.handleReadVoicesPreference(fluid.get(that.model.preferences, "cisl_prefs_readVoices"), that);
    };

    cisl.prefs.modalSettings.handleChosenVoiceSetting = function(chosenVoice, that) {
        console.debug("handleChosenVoiceSetting started; chosen voice: " + chosenVoice);
        var currentReadVoices = fluid.get(that.model.preferences, 'cisl_prefs_readVoices');
        console.debug("currentReadVoices preference:", currentReadVoices);

        // Remove the voice if it's already in the list
        var filteredReadVoices;
        if(Array.isArray(currentReadVoices)) {
            filteredReadVoices = currentReadVoices.filter(function(voice) {
                if(voice !== chosenVoice) return true;
            });
        } else filteredReadVoices = [];

        // Create a new array with the chosen voice at the front 
        var newReadVoices = [chosenVoice].concat(filteredReadVoices);

        console.debug("new read voices: ", newReadVoices);

        // Set array on the preference model
        that.applier.change('preferences.cisl_prefs_readVoices', newReadVoices);

        // Set chosen voice in the TTS module
        clusiveTTS.setCurrentVoice(chosenVoice);

    }

    cisl.prefs.modalSettings.handleReadVoicesPreference = function(readVoices, that) {
        console.debug("handleReadVoicesPreference", readVoices, that);
        if(! readVoices || ! readVoices.forEach || readVoices.length === 0) {            
            return;
        }

        console.debug("cisl.prefs.modalSettings.handleReadVoicesPreference started; readVoices: ", readVoices);
        var voiceFound = false;
        var voiceOptions = that.locate('readVoice').find('option');
        console.debug("handleReadVoicesPreference:voiceOptions", voiceOptions);
        readVoices.forEach(function (preferredVoice) {
            if(voiceFound) {
                return;
            }
            console.debug("handleReadVoicesPreference:Checking for preferred voice: " + preferredVoice);     

            voiceOptions.each(function(idx) {
                if(voiceFound) {
                    return;
                }
                var voiceName = $(this).val();
                console.debug("handleReadVoicesPreference:Current voice option being checked: ", voiceName, $(this));
                if(voiceName === preferredVoice && voiceName !== "default") {
                    console.debug("handleReadVoicesPreference:Preferred voice found ", voiceName, preferredVoice);
                    that.locate('readVoice').val(preferredVoice);
                    voiceFound = true;
                }
            });                   
        });

    }

    fluid.registerNamespace('fluid.binder.transforms');

    /**
     *
     * Transform the value returned by jQuery.val for a single checkbox into a boolean.
     *
     * @param {Array} value - An array of values, either the value attribute of a ticked checkbox, or "on" if the checkbox has no value specified.
     * @return {Boolean} - `true` if the first value is checked, `false`.
     *
     */
    fluid.binder.transforms.checkToBoolean = function(value) {
        return Boolean(fluid.get(value, 0));
    };

    fluid.binder.transforms.checkToBoolean.invert = function(transformSpec) {
        transformSpec.type = 'fluid.binder.transforms.booleanToCheck';
        return transformSpec;
    };

    fluid.defaults('fluid.binder.transforms.checkToBoolean', {
        gradeNames: ['fluid.standardTransformFunction', 'fluid.lens'],
        invertConfiguration: 'fluid.binder.transforms.checkToBoolean.invert'
    });

    /**
     *
     * Transform a boolean model value into the value used for checkboxes by jQuery.val.
     *
     * @param {Boolean} value - The value to be passed to the DOM.
     * @return {Array} - An array with the first value set to "on" if the value is `true`, an empty Array otherwise.
     *
     */
    fluid.binder.transforms.booleanToCheck = function(value) {
        return value ? ['on'] : [];
    };

    fluid.binder.transforms.booleanToCheck.invert = function(transformSpec) {
        transformSpec.type = 'fluid.binder.transforms.checkToBoolean';
        return transformSpec;
    };

    fluid.defaults('fluid.binder.transforms.booleanToCheck', {
        gradeNames: ['fluid.standardTransformFunction', 'fluid.lens'],
        invertConfiguration: 'fluid.binder.transforms.booleanToCheck.invert'
    });
}(fluid_3_0_0));
