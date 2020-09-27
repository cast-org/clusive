/* global cisl, clusive, fluid_3_0_0, fluid, DJANGO_STATIC_ROOT, DJANGO_CSRF_TOKEN */

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
                default: 1.2,
                tall: 1.6,
                taller: 2
            },
            preferenceLineSpaceToModal: {
                1.2: 'default',
                1.6: 'tall',
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
        that.applier.change(path, changedValue);

        cisl.prefs.eventUpdate();
    };

    cisl.prefs.modalSettings.setModalSettingsByPreferences = function(preferences, that) {
        that.applier.change('modalSettings.textSize', fluid.get(preferences, 'fluid_prefs_textSize'));

        that.applier.change('modalSettings.font', fluid.get(preferences, 'fluid_prefs_textFont'));

        that.applier.change('modalSettings.lineSpacing', cisl.prefs.modalSettings.getMappedValue(fluid.get(preferences, 'fluid_prefs_lineSpace'), that.options.mappedValues.preferenceLineSpaceToModal));

        that.applier.change('modalSettings.letterSpacing', cisl.prefs.modalSettings.getMappedValue(fluid.get(preferences, 'fluid_prefs_letterSpace'), that.options.mappedValues.preferenceLetterSpaceToModal));

        that.applier.change('modalSettings.color', fluid.get(preferences, 'fluid_prefs_contrast'));

        that.applier.change('modalSettings.glossary', fluid.get(preferences, 'cisl_prefs_glossary'));
    };

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
