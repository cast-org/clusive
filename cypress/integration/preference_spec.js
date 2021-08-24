// Relies on user accounts created by `python manage.py createrostersamples`

describe('Student user samstudent...', () => {    
    
    it('Visits the home page and logs in', () => {
        cy.visit('http://localhost:8000')        
        cy.get('a#djHideToolBarButton').click();        
        cy.get('input#id_username').type('samstudent')
        cy.get('input#id_password').type('samstudent_pass')
        cy.get('button').contains('Log in').click()
        cy.contains("Discover tools that make Clusive all your own.")
        
        
            // cy.get('span.icon-settings').first().click()        
            // cy.get('div#modalSettings').contains('Text size')
            // cy.get('div#modalSettings').contains('Line spacing')
            // cy.get('div#modalSettings').contains('Letter spacing')
            // cy.get('div#modalSettings').contains('Font')
            // cy.get('div#modalSettings').contains('Color')
            // cy.get('div#modalSettings').contains('Word lookup links')
            // cy.get('div#modalSettings').contains('Content navigation')        
        
        cy.visit('http://localhost:8000/reader/6/2')                                
        
        cy.frameLoaded('iframe[data-cy="reader-frame"]').find('h1').contains('Clues to Clusive')
      })     
  })
  