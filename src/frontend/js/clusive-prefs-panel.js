/* global cisl, fluid_3_0_0, DJANGO_STATIC_ROOT */

(function(fluid) {
    'use strict';

    fluid.defaults('clusive.prefs.djangoStore', {
        gradeNames: ['fluid.dataSource'],
        storeConfig: {
            getURL: '/account/prefs',
            setURL: '/account/prefs',
            resetURL: '/account/prefs/profile'
        },
        components: {
            encoding: {
                type: 'fluid.dataSource.encoding.none'
            }
        },
        listeners: {
            'onRead.impl': {
                listener: 'clusive.prefs.djangoStore.getUserPreferences',
                args: ['{arguments}.1']
            }
        },
        invokers: {
            get: {
                args: ['{that}', '{arguments}.0', '{that}.options.storeConfig']
            }
        }
    });

    fluid.defaults('clusive.prefs.djangoStore.writable', {
        gradeNames: ['fluid.dataSource.writable'],
        listeners: {
            'onWrite.impl': {
                listener: 'clusive.prefs.djangoStore.setUserPreferences'
            }
        },
        invokers: {
            set: {
                args: ['{that}', '{arguments}.0', '{arguments}.1', '{that}.options.storeConfig']
            }
        }
    });

    fluid.makeGradeLinkage('clusive.prefs.djangoStore.linkage', ['fluid.dataSource.writable', 'clusive.prefs.djangoStore'], 'clusive.prefs.djangoStore.writable');

    clusive.prefs.djangoStore.getUserPreferences = function(directModel) {
        console.debug('clusive.prefs.djangoStore.getUserPreferences', directModel);

        var getURL = directModel.getURL;

        var djangoStorePromise = fluid.promise();

        $.get(getURL, function(data) {
            console.debug(getURL);
            console.debug(data);
            djangoStorePromise.resolve({
                preferences: data
            });
        }).fail(function(error) {
            console.error('an error occured', error);
            djangoStorePromise.reject('error');
        });

        return djangoStorePromise;
    };

    clusive.prefs.djangoStore.setUserPreferences = function(model, directModel) {
        console.debug('clusive.prefs.djangoStore.setUserPreferences', directModel, model);
        console.debug(arguments);

        if ($.isEmptyObject(model)) {
            var resetURL = directModel.resetURL;
            $.ajax({
                type: "POST",
                url: resetURL,
                headers: {
                    'X-CSRFToken': DJANGO_CSRF_TOKEN
                },
                data: JSON.stringify({adopt: 'default'}),
                success: function (data) {
                    console.debug("reset preferences to default", data);
                },

            })            
        } else {           
            var setURL = directModel.setURL;            
            $.ajax({
                type: "POST",
                url: setURL,
                headers: {
                    'X-CSRFToken': DJANGO_CSRF_TOKEN
                },
                data: JSON.stringify(fluid.get(model, 'preferences')),
                success: function (data) {
                    console.debug("set preferences", data);
                },

            })
        }
    };

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
                type: 'cisl.prefs.glossary',
                enactor: {
                    type: 'cisl.prefs.enactor.glossary'
                },
                panel: null
            }
        }
    });

    // Redefine the existing contrast schema used by the starter    
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

    fluid.defaults('fluid.prefs.schemas.lineSpace', {
        gradeNames: ['fluid.prefs.schemas'],
        schema: {
            "fluid.prefs.lineSpace": {
                "type": "number",
                "default": 1.6,
                "minimum": 0.7,
                "maximum": 2,
                "multipleOf": 0.1
            }
        }
    });

    // Add a boolean preference for the glossary
    fluid.defaults('cisl.prefs.schemas.glossary', {
        gradeNames: ['fluid.prefs.schemas'],
        schema: {
            'cisl.prefs.glossary': {
                type: 'boolean',
                default: true
            }
        }
    });

    fluid.defaults('cisl.prefs.enactor.glossary', {
        gradeNames: ['fluid.prefs.enactor'],
        preferenceMap: {
            'cisl.prefs.glossary': {
                'model.glossary': 'value'
            }
        },
        modelListeners: {
            glossary: {
                listener: '{that}.enactGlossary',
                args: ['{that}.model.glossary'],
                namespace: 'enactGlossary'
            }
        },
        invokers: {
            enactGlossary: {
                funcName: 'cisl.prefs.enactor.glossary.enactGlossary',
                args: ['{arguments}.0', '{that}']
            }
        }
    });

    cisl.prefs.enactor.glossary.enactGlossary = function(enableGlossary, that) {
        console.debug('enact glossary', enableGlossary, that);
        var readerIframe = $('#D2Reader-Container').find('iframe');
        var readerWindow;
        if (readerIframe.length > 0) {
            readerWindow = readerIframe[0].contentWindow;
        }

        if (readerWindow && readerWindow.markCuedWords && readerWindow.unmarkCuedWords) {
            console.debug('readerWindow');
            if (enableGlossary) {
                console.debug('mark');
                readerWindow.markCuedWords();
            } else {
                console.debug('unmark');
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

    cisl.prefs.getSettings = function(that, isLoggedIn) {
        console.debug('calling CISL prefs Editor fetch impl');
        console.debug('isLoggedIn', isLoggedIn);

        var isLoggedIn = false;
        if (!isLoggedIn) {
            console.warn('Not logged in, using local cookie for fetch method');
            return that.getSettings();
        }
    };

    cisl.prefs.setSettings = function(model, directModel, set) {
        console.debug('calling CISL prefs Editor setSettings');

        var isLoggedIn = false;
        if (!isLoggedIn) {
            console.warn('Not logged in, using local cookie for write method');
            return that.setSettings(model, directModel, set);
        }
    };

    fluid.defaults('cisl.prefs.modalSettings', {
        gradeNames: ['gpii.binder.bindOnCreate'],
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
                                type: 'gpii.binder.transforms.checkToBoolean',
                                inputPath: ''
                            }
                        }
                    },
                    modelToDom: {
                        '': {
                            transform: {
                                type: 'gpii.binder.transforms.booleanToCheck',
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
    };

    cisl.prefs.modalSettings.setModalSettingsByPreferences = function(preferences, that) {
        that.applier.change('modalSettings.textSize', fluid.get(preferences, 'fluid_prefs_textSize'));

        that.applier.change('modalSettings.font', fluid.get(preferences, 'fluid_prefs_textFont'));

        that.applier.change('modalSettings.lineSpacing', cisl.prefs.modalSettings.getMappedValue(fluid.get(preferences, 'fluid_prefs_lineSpace'), that.options.mappedValues.preferenceLineSpaceToModal));

        that.applier.change('modalSettings.letterSpacing', cisl.prefs.modalSettings.getMappedValue(fluid.get(preferences, 'fluid_prefs_letterSpace'), that.options.mappedValues.preferenceLetterSpaceToModal));

        that.applier.change('modalSettings.color', fluid.get(preferences, 'fluid_prefs_contrast'));

        that.applier.change('modalSettings.glossary', fluid.get(preferences, 'cisl_prefs_glossary'));
    };

    fluid.registerNamespace('gpii.binder.transforms');

    /**
     *
     * Transform the value returned by jQuery.val for a single checkbox into a boolean.
     *
     * @param {Array} value - An array of values, either the value attribute of a ticked checkbox, or "on" if the checkbox has no value specified.
     * @return {Boolean} - `true` if the first value is checked, `false`.
     *
     */
    gpii.binder.transforms.checkToBoolean = function(value) {
        return Boolean(fluid.get(value, 0));
    };

    gpii.binder.transforms.checkToBoolean.invert = function(transformSpec) {
        transformSpec.type = 'gpii.binder.transforms.booleanToCheck';
        return transformSpec;
    };

    fluid.defaults('gpii.binder.transforms.checkToBoolean', {
        gradeNames: ['fluid.standardTransformFunction', 'fluid.lens'],
        invertConfiguration: 'gpii.binder.transforms.checkToBoolean.invert'
    });

    /**
     *
     * Transform a boolean model value into the value used for checkboxes by jQuery.val.
     *
     * @param {Boolean} value - The value to be passed to the DOM.
     * @return {Array} - An array with the first value set to "on" if the value is `true`, an empty Array otherwise.
     *
     */
    gpii.binder.transforms.booleanToCheck = function(value) {
        return value ? ['on'] : [];
    };

    gpii.binder.transforms.booleanToCheck.invert = function(transformSpec) {
        transformSpec.type = 'gpii.binder.transforms.checkToBoolean';
        return transformSpec;
    };

    fluid.defaults('gpii.binder.transforms.booleanToCheck', {
        gradeNames: ['fluid.standardTransformFunction', 'fluid.lens'],
        invertConfiguration: 'gpii.binder.transforms.booleanToCheck.invert'
    });
}(fluid_3_0_0));
