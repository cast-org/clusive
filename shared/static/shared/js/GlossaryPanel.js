var fluid_3_0_0 = fluid_3_0_0 || {};

(function ($, fluid) {
    "use strict";

    /*************************************
     * Preferences Editor Glossary *
     *************************************/


     /**
      * A sub-component of fluid.prefs that renders the "Glossary" panel of the user preferences interface.
      */

    fluid.defaults("cisl.prefs.panel.glossary", {
        gradeNames: ["fluid.prefs.panel.switchAdjuster"],
        preferenceMap: {
            "cisl.prefs.glossary": {
                "model.value": "value"
            }
        },
        panelOptions: {
            labelIdTemplate: "glossary-label-%guid"
        },
        protoTree: {
            description: {messagekey: "toggleDescription"},
            label: {messagekey: "label"}
        }
    });

})(jQuery, fluid_3_0_0);
