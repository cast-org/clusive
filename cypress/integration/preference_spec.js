// Relies on user accounts created by `python manage.py createrostersamples`

describe('While logged in as user samstudent', () => {    

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

    var preferenceControls = {
        fontFamily: {            
            setAction: function (selector) {
                cy.get(selector).click({force: true})
            },
            options: {
                comic: 'input[value=comic]'
            }         
        },
        theme: {
            setAction: function (selector) {
                cy.get(selector).click({force: true})
            },
            options: {
                night: 'input[value=night]',
                sepia: 'input[value=sepia]'
            }            
        }
    }

var setPref = function (pref, value) {
    var selector = preferenceControls[pref].options[value];
    preferenceControls[pref].setAction(selector);
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
            },    
        },
        theme: {
            reader: {
                prop: '--USER__appearance',
                values: {
                    night: 'clusive-night',
                    sepia: 'clusive-sepia'
                }
            },
            ui: {
                values: {
                    night: 'clusive-theme-night',
                    sepia: 'clusive-theme-sepia'
                }
            }
        },        
    }

    var checkClusiveUIPreferenceClass = function(pref, expectedValue) {
        cy.get('body').should('have.class', preferenceExpects[pref].ui.values[expectedValue])   
    }

    var checkReaderPreferenceProp = function(pref, expectedValue) {
        cy.iframe(readerSelector).should('have.css', preferenceExpects[pref].reader.prop, preferenceExpects[pref].reader.values[expectedValue])        
    }

    var checkPref = function(pref, expectedValue) {
        checkClusiveUIPreferenceClass(pref, expectedValue);
        checkReaderPreferenceProp(pref, expectedValue);
    }

    // Logs in as the samstudent user
    before(() => {
        logIn('samstudent', 'samstudent_pass')
    })

    // Preserve the session cookie so we don't have to log in multiple times
    beforeEach(() => {        
        Cypress.Cookies.preserveOnce('sessionid')
        cy.restoreLocalStorage();
      })

    afterEach(() => {
        cy.saveLocalStorage();
    })

    // Clear the cookies and local storage at the end of the whole test suite
    after(() => {
        cy.clearCookies()
        cy.clearLocalStorage()
    })

    it('Visits the Clues to Clusive article, and sets the font to comic sans and the theme to dark', () => {   
        cy.visit('http://localhost:8000/reader/6/2')                                
        
        cy.frameLoaded(readerSelector)
        
        cy.iframe(readerSelector).contains('Clusive is a learning environment')

        openPanel();
        
        setPref('fontFamily', 'comic')        
        setPref('theme', 'night')

        checkPref('fontFamily', 'comic')
        checkPref('theme', 'night')        
    })              

    it('Reloads the page; the font is still set to comic sans, the page theme is still dark', () => {
        cy.reload()
        checkPref('fontFamily', 'comic')
        checkPref('theme', 'night')
    })

    it('Changes theme to sepia', () => {
        setPref('theme', 'sepia')
        checkPref('theme', 'sepia')
    })    

  })
  