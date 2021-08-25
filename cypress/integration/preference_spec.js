// Relies on user accounts created by `python manage.py createrostersamples`

describe('Preferences', () => {    

    var readerSelector = 'iframe[data-cy="reader-frame"]'

    var openPanel = function() {
        cy.get('a#djHideToolBarButton').click();                
        cy.get('span.icon-settings').first().click()   
    }

    var logIn = function() {
        cy.visit('http://localhost:8000')                
        cy.get('input#id_username').type('samstudent')
        cy.get('input#id_password').type('samstudent_pass')
        cy.get('button').contains('Log in').click()        
    }

    before(() => {
        logIn()
    })

    beforeEach(() => {
        // Preserve the session cookie so we don't have to log in multiple times
        Cypress.Cookies.preserveOnce('sessionid')
      })

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
        cy.get('body').should('have.class', 'fl-font-comic-sans')        
        cy.get('body').should('have.class', 'clusive-theme-night')        
        cy.iframe(readerSelector).should('have.css', '--USER__fontFamily', 'Comic Sans MS, sans-serif')        
        cy.iframe(readerSelector).should('have.css', '--USER__appearance', 'clusive-night')                
    })              

    it('Reloads the page; the font is still set to comic sans, the page theme is still dark', () => {
        cy.reload()
        cy.get('body').should('have.class', 'fl-font-comic-sans')        
        cy.get('body').should('have.class', 'clusive-theme-night')
        cy.iframe(readerSelector).should('have.css', '--USER__fontFamily', 'Comic Sans MS, sans-serif')   
        cy.iframe(readerSelector).should('have.css', '--USER__appearance', 'clusive-night')                     
    })
  })
  