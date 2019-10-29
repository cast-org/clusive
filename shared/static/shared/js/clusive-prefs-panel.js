/* global fluid, cisl */

(function (fluid) {
    "use strict";

    // This removes the tableOfContents and
    // enhanceInputs preferences from the
    // default Infusion starter auxiliary schema
    fluid.defaults("cisl.prefs.auxSchema.starter", {
        gradeNames: ["fluid.prefs.auxSchema.starter"],
        mergePolicy: {
            "auxiliarySchema.tableOfContents": "replace",
            "auxiliarySchema.enhanceInputs": "replace"
        },
        auxiliarySchema: {
            "tableOfContents": null,
            "enhanceInputs": null,       
        }
    });

    // Redefine the existing contrast schema used by the starter
    // to remove
    fluid.defaults("fluid.prefs.schemas.contrast", {
        gradeNames: ["fluid.prefs.schemas"],
        schema: {
            "fluid.prefs.contrast": {
                "type": "string",
                "default": "default",
                "enum": ["default", "bw", "wb", "lgdg", "gw", "bbr"]
            }
        }
    });

    fluid.defaults("cisl.prefs.composite.separatedPanel", {
        gradeNames: ["fluid.prefs.separatedPanel"],
        iframeRenderer: {
            markupProps: {
                src: DJANGO_STATIC_ROOT + "shared/html/SeparatedPanelPrefsEditorFrame.html"
            }
        }
    });

    fluid.defaults("cisl.prefs.auxSchema.glossary.demo", {
        gradeNames: ["cisl.prefs.auxSchema.glossary"],
        auxiliarySchema: {
            glossary: {
                panel: {
                    template: DJANGO_STATIC_ROOT + "shared/html/PrefsEditorTemplate-glossaryToggle.html",
                    message: DJANGO_STATIC_ROOT + "shared/messages/glossary.json"
                },
                enactor: {
                    type: "cisl.prefs.enactor.glossary.demo"
                }
            }
        }
    });

    fluid.defaults("cisl.prefs.enactor.glossary.demo", {
        gradeNames: ["cisl.prefs.enactor.glossary"],
        invokers: {
            applyGlossary: {
                funcName: "cisl.prefs.enactor.glossary.demo.applyGlossary",
                args: ["{arguments}.0",
                "{that}"
                ]
            }
        }
    });

    cisl.prefs.enactor.glossary.demo.applyGlossary = function(enableGlossary, that) {        
        // Apply glossary step
        cisl.prefs.enactor.glossary.applyGlossary(enableGlossary, that);
    };

    fluid.defaults("cisl.prefs.modalSettings", {
        gradeNames: ["gpii.binder.bindOnCreate"],
        listeners: {
            "onCreate.log": {
                "this": "console",
                "method": "log",
                "args": ["{that}"]
            }
        },
        model: {
            modalSettings: {                
            },
            // Linked to preferences editor preferences
            preferences: null
        },
        mappedValues: {
            modalLineSpacing: {
                "default": 1,
                "tall": 1.5,
                "taller": 2
            },
            modalLetterSpacing: {
                "default": 1,
                "wide": 1.2,
                "wider": 1.4
            },
            modalColor: {
                "default": "default",
                "wb": "wb",
                "bbr": "bbr"
            }
        },
        modelListeners: {
            "modalSettings.textSize": {
                funcName: "cisl.prefs.modalSettings.applyModalSettingToPreference",
                args: ["{change}.value", "preferences.fluid_prefs_textSize", "{that}"],
                excludeSource: "init"
            },
            "modalSettings.lineSpacing": {
                funcName: "cisl.prefs.modalSettings.applyModalSettingToPreference",
                args: ["@expand:cisl.prefs.modalSettings.getMappedValue({change}.value, {that}.options.mappedValues.modalLineSpacing)", "preferences.fluid_prefs_lineSpace", "{that}"],
                excludeSource: "init"
            },
            "modalSettings.letterSpacing": {
                funcName: "cisl.prefs.modalSettings.applyModalSettingToPreference",
                args: ["@expand:cisl.prefs.modalSettings.getMappedValue({change}.value, {that}.options.mappedValues.modalLetterSpacing)", "preferences.fluid_prefs_letterSpace", "{that}"],
                excludeSource: "init"
            },            
            "modalSettings.font": {
                funcName: "cisl.prefs.modalSettings.applyModalSettingToPreference",
                args: ["{change}.value", "preferences.fluid_prefs_textFont", "{that}"],
                excludeSource: "init"
            },
            "modalSettings.color": {
                funcName: "cisl.prefs.modalSettings.applyModalSettingToPreference",
                args: ["@expand:cisl.prefs.modalSettings.getMappedValue({change}.value, {that}.options.mappedValues.modalColor)", "preferences.fluid_prefs_contrast", "{that}"],
                excludeSource: "init"
            }                 
        },
        selectors: {
            textSize: ".cislc-modalSettings-textSize",
            lineSpacing: ".cislc-modalSettings-lineSpacing",
            letterSpacing: ".cislc-modalSettings-letterSpacing",
            font: ".cislc-modalSettings-font",
            color: ".cislc-modalSettings-color",
            reset: ".cislc-modalSettings-reset"
        },
        bindings: {
            textSize: "modalSettings.textSize",
            lineSpacing: "modalSettings.lineSpacing",
            letterSpacing: "modalSettings.letterSpacing",
            font: "modalSettings.font",
            color: "modalSettings.color"
        }
    })

    cisl.prefs.modalSettings.getMappedValue = function (changedValue, map) {
        console.log("getMappedValue", changedValue, map)
        return map[changedValue];
    };

    cisl.prefs.modalSettings.applyModalSettingToPreference = function (changedValue, path, that) {
        console.log("applyModalSetting", changedValue, path, that);
        that.applier.change(path, changedValue);
    }

})(fluid_3_0_0);