describe('The home page', () => {
    it('Successfully loads', () => {
      cy.visit('http://localhost:8000')
    })
    it('Contains the Welcome to Clusive text', () => {
      cy.contains('Welcome to Clusive')
    })
    it('Contains the Guest Login text', () => {
        cy.contains('Try Clusive as a Guest')
    })
  })
  