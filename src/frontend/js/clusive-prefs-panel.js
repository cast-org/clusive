/* global cisl, fluid_3_0_0, DJANGO_STATIC_ROOT */

(function(fluid) {
    'use strict';

    // This removes the tableOfContents and
    // enhanceInputs preferences from the
    // default Infusion starter auxiliary schema
    fluid.defaults('cisl.prefs.auxSchema.starter', {
        gradeNames: ['fluid.prefs.auxSchema.starter'],
        mergePolicy: {
            'auxiliarySchema.tableOfContents': 'replace',
            'auxiliarySchema.enhanceInputs': 'replace'
        },
        auxiliarySchema: {
            tableOfContents: null,
            enhanceInputs: null,
            contrast: {
                classes: {
                    default: 'clusive-theme-default',
                    night: 'clusive-theme-night',
                    sepia: 'clusive-theme-sepia'
                },
                panel: null
            },
            textFont: {
                panel: null
            },
            textSize: {
                panel: null
            },
            lineSpace: {
                panel: null
            },
            glossary: {
                type: "cisl.prefs.glossary",
                enactor: {
                    type: "cisl.prefs.enactor.glossary"
                },
                panel: null,
            }
        }
    });

    // Redefine the existing contrast schema used by the starter
    // to remove
    fluid.defaults('fluid.prefs.schemas.contrast', {
        gradeNames: ['fluid.prefs.schemas'],
        schema: {
            'fluid.prefs.contrast': {
                type: 'string',
                default: 'default',
                enum: ['default', 'night', 'sepia']
            }
        }
    });

    // Add a boolean preference for the glossary
    fluid.defaults("cisl.prefs.schemas.glossary", {
        gradeNames: ["fluid.prefs.schemas"],
        schema: {
            "cisl.prefs.glossary": {
                "type": "boolean",
                "default": true
            }
        }
    });

    fluid.defaults("cisl.prefs.enactor.glossary", {
        gradeNames: ["fluid.prefs.enactor"],
        preferenceMap: {
            "cisl.prefs.glossary": {
                "model.glossary": "value"
            }
        },
        modelListeners: {
            glossary: {
                listener: "{that}.enactGlossary",
                args: ["{that}.model.glossary"],
                namespace: "enactGlossary"
            }
        },
        invokers: {
            enactGlossary: {
                funcName: "cisl.prefs.enactor.glossary.enactGlossary",
                args: ["{arguments}.0", "{that}"]
            }
        }
    });
    
    cisl.prefs.enactor.glossary.enactGlossary = function(enableGlossary, that) {
        console.log("enact glossary", enableGlossary, that);
        var readerIframe = $("#D2Reader-Container").find("iframe"); 
        var readerWindow;
        if(readerIframe.length > 0) {
            readerWindow = readerIframe[0].contentWindow;
        }        
        
        if(readerWindow && readerWindow.markCuedWords && readerWindow.unmarkCuedWords) {
            console.log("readerWindow");
            if(enableGlossary) {
                console.log("mark");
                readerWindow.markCuedWords();
            } else {
                console.log("unmark");
                readerWindow.unmarkCuedWords();
            }
        }
    };

    fluid.defaults('cisl.prefs.composite.separatedPanel', {
        gradeNames: ['fluid.prefs.separatedPanel'],
        iframeRenderer: {
            markupProps: {
                src: DJANGO_STATIC_ROOT + 'shared/html/SeparatedPanelPrefsEditorFrame.html'
            }
        }
    });

    fluid.defaults('cisl.prefs.auxSchema.letterSpace', {
        gradeNames: ['fluid.prefs.auxSchema.letterSpace'],
        auxiliarySchema: {
            letterSpace: {
                panel: null
            }
        }
    });

    fluid.defaults('cisl.prefs.modalSettings', {
        gradeNames: ['gpii.binder.bindOnCreate'],
        model: {
            modalSettings: {},
            // Linked to preferences editor preferences
            preferences: null
        },
        mappedValues: {
            modalLineSpacingToPreference: {
                shorter: 1.2,
                default: 1.6,
                taller: 2
            },
            preferenceLineSpaceToModal: {
                1.2: 'shorter',
                1.6: 'default',
                2: 'taller'
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
            }
        },
        invokers: {
            setModalSettingsByPreferences: {
                funcName: 'cisl.prefs.modalSettings.setModalSettingsByPreferences',
                args: ['{that}.model.preferences', '{that}']
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
            'preferences': {
                func: '{that}.setModalSettingsByPreferences',
                includeSource: 'init'
            }
        },
        selectors: {
            textSize: '.cislc-modalSettings-textSize',
            lineSpacing: '.cislc-modalSettings-lineSpacing',
            letterSpacing: '.cislc-modalSettings-letterSpacing',
            font: '.cislc-modalSettings-font',
            color: '.cislc-modalSettings-color',
            glossary: '.cislc-modalSettings-glossary',
            reset: '.cislc-modalSettings-reset'
        },
        bindings: {
            textSize: 'modalSettings.textSize',
            lineSpacing: 'modalSettings.lineSpacing',
            letterSpacing: 'modalSettings.letterSpacing',
            font: 'modalSettings.font',
            color: 'modalSettings.color',            
            glossaryCheckbox: {
                selector: "glossary",
                path: "modalSettings.glossary",
                rules: {
                    domToModel: {
                        "": {
                            transform: {
                                type: "gpii.binder.transforms.checkToBoolean",
                                inputPath: ""
                            }
                        }
                    },
                    modelToDom: {
                        "": {
                            transform: {
                                type: "gpii.binder.transforms.booleanToCheck",
                                inputPath: ""
                            }
                        }
                    }                    
                }
            },
            
        }
    });

    cisl.prefs.modalSettings.getMappedValue = function(changedValue, map) {
        // console.log("getMappedValue", changedValue, map)
        return map[changedValue];
    };

    cisl.prefs.modalSettings.applyModalSettingToPreference = function(changedValue, path, that) {
        // console.log("applyModalSetting", changedValue, path, that);        
        that.applier.change(path, changedValue);
    };

    cisl.prefs.modalSettings.setModalSettingsByPreferences = function(preferences, that) {
        console.log('cisl.prefs.modalSettings.setModalSettingsByPreferences', preferences);

        that.applier.change('modalSettings.textSize', fluid.get(preferences, 'fluid_prefs_textSize'));

        that.applier.change('modalSettings.font', fluid.get(preferences, 'fluid_prefs_textFont'));

        that.applier.change('modalSettings.lineSpacing', cisl.prefs.modalSettings.getMappedValue(fluid.get(preferences, 'fluid_prefs_lineSpace'), that.options.mappedValues.preferenceLineSpaceToModal));

        that.applier.change('modalSettings.letterSpacing', cisl.prefs.modalSettings.getMappedValue(fluid.get(preferences, 'fluid_prefs_letterSpace'), that.options.mappedValues.preferenceLetterSpaceToModal));

        that.applier.change('modalSettings.color', fluid.get(preferences, 'fluid_prefs_contrast'));

        that.applier.change('modalSettings.glossary', fluid.get(preferences, 'cisl_prefs_glossary'));
    };

    fluid.registerNamespace("gpii.binder.transforms");

    /**
     *
     * Transform the value returned by jQuery.val for a single checkbox into a boolean.
     *
     * @param {Array} value - An array of values, either the value attribute of a ticked checkbox, or "on" if the checkbox has no value specified.
     * @return {Boolean} - `true` if the first value is checked, `false`.
     *
     */
    gpii.binder.transforms.checkToBoolean = function (value) {
        return fluid.get(value, 0) ? true : false;
    };

    gpii.binder.transforms.checkToBoolean.invert = function (transformSpec) {
        transformSpec.type = "gpii.binder.transforms.booleanToCheck";
        return transformSpec;
    };

    fluid.defaults("gpii.binder.transforms.checkToBoolean", {
        gradeNames: ["fluid.standardTransformFunction", "fluid.lens"],
        invertConfiguration: "gpii.binder.transforms.checkToBoolean.invert"
    });

    /**
     *
     * Transform a boolean model value into the value used for checkboxes by jQuery.val.
     *
     * @param {Boolean} value - The value to be passed to the DOM.
     * @return {Array} - An array with the first value set to "on" if the value is `true`, an empty Array otherwise.
     *
     */
    gpii.binder.transforms.booleanToCheck = function (value) {
        return value ? ["on"] : [];
    };

    gpii.binder.transforms.booleanToCheck.invert = function (transformSpec) {
        transformSpec.type = "gpii.binder.transforms.checkToBoolean";
        return transformSpec;
    };

    fluid.defaults("gpii.binder.transforms.booleanToCheck", {
        gradeNames: ["fluid.standardTransformFunction", "fluid.lens"],
        invertConfiguration: "gpii.binder.transforms.booleanToCheck.invert"
    });
    
}(fluid_3_0_0));
