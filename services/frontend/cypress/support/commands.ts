const TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9." +
  "eyJzdWIiOiJkZXZvcHMiLCJyb2xlcyI6WyJwbGF0Zm9ybV9hZG1pbiJdLCJleHAiOjQxMDI0NDQ4MDB9." +
  "signature";

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Cypress {
    interface Chainable {
      login(locale?: "en" | "fa", path?: string): Chainable<void>;
    }
  }
}

Cypress.Commands.add("login", (locale: "en" | "fa" = "en", path = "/") => {
  cy.visit(path, {
    onBeforeLoad(win) {
      win.localStorage.setItem("xin-operator-token", TOKEN);
      win.localStorage.setItem("xin-operator-locale", locale);
    }
  });
});
