describe('Following the guest login link', () => {
    it('creates a guest account and moves to the guest dashboard page', () => {
        cy.visit("http://localhost:8000/account/guest_login")
        cy.url()
        .should('include', '/dashboard')
    })
    it('shows the guest account tip', () => {
        cy.contains("Tip: As a guest, you cannot save settings or highlights, get recommendations, or explore the parent and teacher features of Clusive.")
    })
    it('shows the Clues to Clusive library item', () => {
        cy.contains("Clues to Clusive")
    })
})