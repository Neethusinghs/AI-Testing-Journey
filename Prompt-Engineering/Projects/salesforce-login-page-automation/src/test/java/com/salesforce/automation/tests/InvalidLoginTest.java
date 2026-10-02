package com.salesforce.automation.tests;

import org.testng.Assert;
import org.testng.annotations.DataProvider;
import org.testng.annotations.Test;

import com.salesforce.automation.base.BaseTest;
import com.salesforce.automation.config.ConfigReader;
import com.salesforce.automation.exceptions.FrameworkException;
import com.salesforce.automation.pages.LoginPage;

public class InvalidLoginTest extends BaseTest {

    @DataProvider(name = "mismatchedCredentials")
    public Object[][] mismatchedCredentials() {
        return new Object[][] {
                { "invalid.user.one@example.com", "InvalidPass!123" },
                { "invalid.user.two@example.com", "AnotherPass!456" },
                { "not.a.real.user@example.com", "admin" }
        };
    }

    @Test(dataProvider = "mismatchedCredentials",
            description = "Mismatched credentials must never authenticate and must show a credential error")
    public void verifyMismatchedCredentialsAreRejected(String username, String password) {
        try {
            LoginPage loginPage = loginPage().login(username, password);
            Assert.assertTrue(loginPage.isOnLoginPage(), "Invalid credentials must not leave the login page");
            Assert.assertTrue(loginPage.isErrorMessageDisplayed(),
                    "A credential error must be displayed for invalid credentials");
            String expectedError = ConfigReader.get("sf.expected.error");
            Assert.assertTrue(loginPage.getErrorMessage().contains(expectedError),
                    "Unexpected error message for invalid credentials");
        } catch (FrameworkException e) {
            Assert.fail("Invalid login flow raised a framework error: " + e.getMessage(), e);
        }
    }

    @Test(description = "Submitting the form with empty credentials must be rejected and surface an error")
    public void verifyEmptyCredentialsAreRejected() {
        try {
            LoginPage loginPage = loginPage().waitForLoginPageToLoad();
            loginPage.clickLogin();
            Assert.assertTrue(loginPage.isOnLoginPage(), "Empty credentials must not leave the login page");
            boolean errorSurfaced = loginPage.isErrorMessageDisplayed()
                    || loginPage.isUsernameMarkedInvalid()
                    || loginPage.isPasswordMarkedInvalid();
            Assert.assertTrue(errorSurfaced, "An error state must be surfaced when the form is submitted empty");
        } catch (FrameworkException e) {
            Assert.fail("Empty login flow raised a framework error: " + e.getMessage(), e);
        }
    }
}
