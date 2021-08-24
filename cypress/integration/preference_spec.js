// Relies on user accounts created by `python manage.py createrostersamples`

describe('Student user samstudent...', () => {    
    
    it('Visits the home page and logs in', () => {
        cy.visit('http://localhost:8000')        
        cy.get('a#djHideToolBarButton').click();        
        cy.get('input#id_username').type('samstudent')
        cy.get('input#id_password').type('samstudent_pass')
        cy.get('button').contains('Log in').click()
        cy.contains("Dive into the Library to find something to read.")
      })     

    it('Opens the settings panel', () => {
        cy.get('span.icon-settings').first().click()
        cy.get('div#modalSettings').contains('Display')
        .contains('Reading Tools')
        .contains('Text size')
        .contains('Line spacing')
        .contains('Letter spacing')
        .contains('Font')
        .contains('Color')
        .contains('Word lookup links')
        .contains('Content navigation')
    })        
  })
  