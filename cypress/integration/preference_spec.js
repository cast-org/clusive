// Relies on user accounts created by `python manage.py createrostersamples`

describe('Preferences', () => {    

    var readerSelector = 'iframe[data-cy="reader-frame"]'

    var openPanel = function() {
        cy.get('a#djHideToolBarButton').click();                
        cy.get('span.icon-settings').first().click()   
    }

    var logIn = function(username, password) {
        cy.visit('http://localhost:8000')                
        cy.get('input#id_username').type(username)
        cy.get('input#id_password').type(password)
        cy.get('button').contains('Log in').click()        
    }

    var preferenceExpects = {
        fontFamily: {
            reader: {
                prop: '--USER__fontFamily',
                values: {
                    comic: 'Comic Sans MS, sans-serif'                
                }
            },
            ui: {
                values: {
                    comic: 'fl-font-comic-sans'
                }
            }
        },
        theme: {
            reader: {
                prop: '--USER__appearance',
                values: {
                    night: 'clusive-night'
                }
            },
            ui: {
                values: {
                    night: 'clusive-theme-night'
                }
            }
        },        
    }

    var checkClusiveUIPreferenceClass = function(pref, expectedValue) {
        cy.get('body').should('have.class', preferenceExpects[pref].ui.values[expectedValue])   
    }

    var verifyClusiveUIPreferences = function() {
        checkClusiveUIPreferenceClass('fontFamily', 'comic')
        checkClusiveUIPreferenceClass('theme', 'night')
    }

    var checkReaderPreferenceProp = function(pref, expectedValue) {
        cy.iframe(readerSelector).should('have.css', preferenceExpects[pref].reader.prop, preferenceExpects[pref].reader.values[expectedValue])        
    }

    var verifyReaderPreferences = function() {
        checkReaderPreferenceProp("fontFamily", "comic")        
        checkReaderPreferenceProp("theme", "night")            
    }

    // Logs in as the samstudent user
    before(() => {
        logIn('samstudent', 'samstudent_pass')
    })

    // Preserve the session cookie so we don't have to log in multiple times
    beforeEach(() => {        
        Cypress.Cookies.preserveOnce('sessionid')
      })

    // Clear the cookies at the end of the whole test suite
    after(() => {
        cy.clearCookies()
    })

    it('Visits the Clues to Clusive article, and sets the font to comic sans and the theme to dark', () => {   
        cy.visit('http://localhost:8000/reader/6/2')                                
        
        cy.frameLoaded(readerSelector)
        
        cy.iframe(readerSelector).contains('Clusive is a learning environment')

        openPanel();
        cy.get('input[value=comic').click({force: true})        
        cy.get('input[value=night').click({force: true})
        verifyClusiveUIPreferences();
        verifyReaderPreferences();
    })              

    it('Reloads the page; the font is still set to comic sans, the page theme is still dark', () => {
        cy.reload()
        verifyClusiveUIPreferences();
        verifyReaderPreferences();
    })
  })
  