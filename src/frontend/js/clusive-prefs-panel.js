/* global cisl, fluid_3_0_0, DJANGO_STATIC_ROOT */

/*
    This code defines canonical representations of the various preference settings,
    how they are stored, and enactors for preferences that are not done through Readium.
 */

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
                panel: null,
                alias: null
            },
            textFont: {
                panel: null,
                alias: null
            },
            textSize: {
                panel: null,
                alias: null
            },
            lineSpace: {
                panel: null,
                alias: null
            },
            glossary: {
                type: 'cisl.prefs.glossary',
                enactor: {
                    type: 'cisl.prefs.enactor.glossary'
                },
                panel: null
            },
            scroll: {
                type: 'cisl.prefs.scroll',
                panel: null
            },
            readSpeed: {
                type: 'cisl.prefs.readSpeed',
                enactor: {
                    type: 'cisl.prefs.enactor.readSpeed'
                },
                panel: null
            },
            readVoices: {
                type: 'cisl.prefs.readVoices',
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
            'fluid.prefs.lineSpace': {
                type: 'number',
                default: 1.6,
                minimum: 0.7,
                maximum: 2,
                multipleOf: 0.1
            }
        }
    });

    // Add a voice speed preference for TTS
    fluid.defaults('cisl.prefs.schemas.readSpeed', {
        gradeNames: ['fluid.prefs.schemas'],
        schema: {
            'cisl.prefs.readSpeed': {
                type: 'number',
                default: 1,
                mininum: 0.5,
                maximum: 2,
                multipleOf: 0.25

            }
        }
    });

    // Enactor for TTS voice speed
    fluid.defaults('cisl.prefs.enactor.readSpeed', {
        gradeNames: ['fluid.prefs.enactor'],
        preferenceMap: {
            'cisl.prefs.readSpeed': {
                'model.readSpeed': 'value'
            }
        },
        modelListeners: {
            'readSpeed': {
                listener: '{that}.enactReadSpeed',
                args: ['{that}.model.readSpeed'],
                namespace: 'enactReadSpeed'
            }
        },
        invokers: {
            'enactReadSpeed': {
                funcName: "cisl.prefs.enactor.readSpeed.enactReadSpeed",
                args: "{arguments}.0"
            }
        }
    });

    cisl.prefs.enactor.readSpeed.enactReadSpeed = function (readSpeed) {
        console.log("cisl.prefs.enactor.readSpeed.enactReadSpeed", readSpeed);
        clusiveTTS.voiceRate = readSpeed;
    }

    // Add a preferred voices preference for TTS
    fluid.defaults('cisl.prefs.schemas.readVoices', {
        gradeNames: ['fluid.prefs.schemas'],
        schema: {
            'cisl.prefs.readVoices': {
            type: 'array',
            default: []
            }
        }
    });

    // Preference for paged vs. scrolled layout
    fluid.defaults('cisl.prefs.schemas.scroll', {
        gradeNames: ['fluid.prefs.schemas'],
        schema: {
            'cisl.prefs.scroll': {
                type: 'boolean',
                default: true
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

        var readerWindow = clusiveContext.reader.window;

        if (readerWindow && readerWindow.markCuedWords && readerWindow.unmarkCuedWords) {
            console.debug('readerWindow');
            if (enableGlossary) {
                console.debug('mark cued words');
                readerWindow.markCuedWords();
            } else {
                console.debug('unmark cued words');
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

    cisl.prefs.getSettings = function(that) {
        console.debug('calling CISL prefs Editor fetch impl');
        return that.getSettings();
    };

    // Fire a non-Infusion document event that non-Infusion
    // code can hook into to respond to preference changes
    cisl.prefs.dispatchPreferenceUpdateEvent = function() {
        var event = new Event('update.cisl.prefs');
        document.dispatchEvent(event);
    };

}(fluid_3_0_0));
