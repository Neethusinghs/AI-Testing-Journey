package com.salesforce.automation.tests;

import org.testng.Assert;
import org.testng.SkipException;
import org.testng.annotations.DataProvider;
import org.testng.annotations.Test;

import com.salesforce.automation.base.BaseTest;
import com.salesforce.automation.config.ConfigReader;
import com.salesforce.automation.exceptions.FrameworkException;
import com.salesforce.automation.pages.LoginPage;

public class ValidLoginTest extends BaseTest {

    @DataProvider(name = "validCredentials")
    public Object[][] validCredentials() {
        return new Object[][] {
                { ConfigReader.get("sf.username", ""), ConfigReader.get("sf.password", "") }
        };
    }

    @Test(dataProvider = "validCredentials", priority = 1,
            description = "Valid credentials must authenticate and leave the Salesforce login page")
    public void verifyValidCredentialsAuthenticate(String username, String password) {
        requireCredentials(username, password);
        try {
            LoginPage loginPage = loginPage().login(username, password);
            loginPage.waitForSuccessfulLogin();
            Assert.assertFalse(loginPage.isOnLoginPage(), "Valid credentials must leave the Salesforce login page");
        } catch (FrameworkException e) {
            Assert.fail("Valid login flow raised a framework error: " + e.getMessage(), e);
        }
    }

    @Test(priority = 2,
            description = "Remember me checkbox must reflect and persist its selection state")
    public void verifyRememberMeStateIsReflected() {
        try {
            LoginPage loginPage = loginPage().waitForLoginPageToLoad();
            loginPage.setRememberMe(true);
            Assert.assertTrue(loginPage.isRememberMeSelected(), "Remember me must report selected after being checked");
            loginPage.setRememberMe(false);
            Assert.assertFalse(loginPage.isRememberMeSelected(), "Remember me must report unselected after being unchecked");
        } catch (FrameworkException e) {
            Assert.fail("Remember me interaction raised a framework error: " + e.getMessage(), e);
        }
    }

    @Test(dataProvider = "validCredentials", priority = 3,
            description = "Valid credentials must authenticate when Remember me is selected")
    public void verifyValidCredentialsWithRememberMe(String username, String password) {
        requireCredentials(username, password);
        try {
            LoginPage loginPage = loginPage().waitForLoginPageToLoad().setRememberMe(true);
            Assert.assertTrue(loginPage.isRememberMeSelected(), "Remember me must stay selected before submitting");
            loginPage.login(username, password).waitForSuccessfulLogin();
            Assert.assertFalse(loginPage.isOnLoginPage(), "Valid credentials with Remember me must authenticate");
        } catch (FrameworkException e) {
            Assert.fail("Valid login with Remember me raised a framework error: " + e.getMessage(), e);
        }
    }

    private void requireCredentials(String username, String password) {
        if (username.isBlank() || password.isBlank()) {
            throw new SkipException("Supply sf.username and sf.password via -Dsf.username=... -Dsf.password=... "
                    + "or environment variables to run the valid login tests");
        }
    }
}
