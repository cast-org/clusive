/* global fluid, cisl */

(function (fluid) {
    "use strict";

    var djangoStaticPrefix = "/static/"

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
            "textSize": {
                "classes": {
                    "small": "cisl-textSize-small",
                    "medium": "cisl-textSize-medium",
                    "large": "cisl-textSize-large",
                    "x-large": "cisl-textSize-x-large"
                },
                "panel": {
                    type: "cisl.prefs.panel.textSize",
                    template: djangoStaticPrefix + "shared/html/PrefsEditorTemplate-textSize.html",
                    message: djangoStaticPrefix + "shared/messages/textSize.json"
                },
                "enactor": {
                    type: "cisl.prefs.enactor.textSize"
                }
            }
        }
    });

    // TODO: there is probably a better way to do these
    // modifications to the starter schemas, but this is
    // reasonably fast

    fluid.defaults("fluid.prefs.schemas.textSize", {
    gradeNames: ["fluid.prefs.schemas"],
    schema: {
        "fluid.prefs.textSize": {
            "type": "string",
            "default": "medium",
            "enum": ["small", "medium", "large", "x-large"]
            }
        }
    });

    fluid.defaults("cisl.prefs.enactor.textSize", {
        gradeNames: "fluid.prefs.enactor.textSize",
        fontScaleMap: {
            "small": "0.75",
            "medium": "1",
            "large": "1.5",
            "x-large": "2"
        },
        invokers: {
            set: {
                funcName: "cisl.prefs.enactor.textSize.set",
                args: ["{arguments}.0", "{that}", "{that}.options.fontScaleMap", "{that}.getTextSizeInPx"]
            }
    }
    });

    cisl.prefs.enactor.textSize.set = function (size, that, fontScaleMap, getTextSizeInPxFunc) {
        // translate the selection choice into a times multiplier
        var times = fontScaleMap[size];
        // delegate to the standard fluid.prefs function
        fluid.prefs.enactor.textSize.set(times, that, getTextSizeInPxFunc);
    };

    fluid.defaults("cisl.prefs.panel.textSize", {
        gradeNames: ["fluid.prefs.panel.themePicker"],
        preferenceMap: {
            "fluid.prefs.textSize": {
                "model.value": "value",
                "controlValues.theme": "enum"
                }
        },
        "classnameMap": {
            "theme": {
                "small": "cisl-textSize-small",
                "medium": "cisl-textSize-medium",
                "large": "cisl-textSize-large",
                "x-large": "cisl-textSize-x-large"
            }
        },
        selectors: {
            header: ".flc-prefsEditor-textSize-header",
            themeRow: ".flc-prefsEditor-themeRow",
            themeLabel: ".flc-prefsEditor-theme-label",
            themeInput: ".flc-prefsEditor-themeInput",
            label: ".flc-prefsEditor-themePicker-label",
            textFontDescr: ".flc-prefsEditor-themePicker-descr"
        },
        selectorsToIgnore: ["header"],
        styles: {
            defaultThemeLabel: "fl-prefsEditor-themePicker-defaultThemeLabel"
        },
        stringArrayIndex: {
            theme: [
                "textSize-small",
                "textSize-medium",
                "textSize-large",
                "textSize-x-large"
            ]
        },
        controlValues: {
            theme: ["small", "medium", "large", "x-large"]
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
                src: djangoStaticPrefix + "shared/js/lib/infusion/src/framework/preferences/html/SeparatedPanelPrefsEditorFrame.html"
            }
        },
        distributeOptions: {

        }
    });

    fluid.defaults("cisl.prefs.auxSchema.glossary.demo", {
        gradeNames: ["cisl.prefs.auxSchema.glossary"],
        auxiliarySchema: {
            glossary: {
                panel: {
                    template: djangoStaticPrefix + "shared/js/lib/infusion/src/framework/preferences/html/PrefsEditorTemplate-glossaryToggle.html",
                    message: djangoStaticPrefix + "shared/js/lib/infusion/src/framework/preferences/messages/glossary.json"
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

})(fluid_3_0_0);