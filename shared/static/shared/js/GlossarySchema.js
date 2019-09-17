var fluid_3_0_0 = fluid_3_0_0 || {};

(function (fluid) {
    "use strict";


    /*******************************************************************************
    * Starter auxiliary schema grade
    *
    * Contains the settings for the glossary preference
    *******************************************************************************/

    // Fine-tune the starter aux schema and add glossary preference
    fluid.defaults("cisl.prefs.auxSchema.glossary", {
        gradeNames: ["fluid.prefs.auxSchema"],
        auxiliarySchema: {
            "message": "%messagePrefix/prefsEditor.json",
            glossary: {
                type: "cisl.prefs.glossary",
                enactor: {
                    type: "cisl.prefs.enactor.glossary"
                },
                panel: {
                    type: "cisl.prefs.panel.glossary",
                    container: ".flc-prefsEditor-glossary",
                    template: "../src/html/PrefsEditorTemplate-glossaryToggle.html",
                    message: "../src/messages/glossary.json"
                }
            }
        }
    });


    /*******************************************************************************
    * Primary Schema
    *******************************************************************************/

    // add extra prefs to the starter primary schemas

    fluid.defaults("cisl.prefs.schemas.glossary", {
        gradeNames: ["fluid.prefs.schemas"],
        schema: {
            "cisl.prefs.glossary": {
                "type": "boolean",
                "default": true
            }
        }
    });

})(fluid_3_0_0);
