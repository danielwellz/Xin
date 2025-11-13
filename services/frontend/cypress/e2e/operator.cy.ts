/// <reference types="cypress" />

describe("Operator console", () => {
  it("covers onboarding flow in English", () => {
    cy.login("en", "/channels/wizard");
    cy.contains("Channel wizard");
    cy.contains("Preview").click();
    cy.contains("Save").click();
    cy.contains("Copy");
  });

  it("publishes a policy in Persian locale", () => {
    cy.login("fa", "/policies");
    cy.contains("ویرایشگر سیاست");
    cy.contains("انتشار").click();
  });
});
