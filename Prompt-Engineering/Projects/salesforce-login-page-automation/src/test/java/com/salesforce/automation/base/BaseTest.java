package com.salesforce.automation.base;

import org.testng.ITestResult;
import org.testng.annotations.AfterMethod;
import org.testng.annotations.AfterTest;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.BeforeTest;
import org.testng.annotations.Listeners;

import com.salesforce.automation.config.ConfigReader;
import com.salesforce.automation.driver.DriverFactory;
import com.salesforce.automation.listeners.TestListener;
import com.salesforce.automation.pages.LoginPage;

@Listeners(TestListener.class)
public abstract class BaseTest {

    protected LoginPage loginPage() {
        return new LoginPage(DriverFactory.getDriver());
    }

    @BeforeTest(alwaysRun = true)
    public void setUpDriver() {
        ConfigReader.load();
        DriverFactory.initDriver();
    }

    @BeforeMethod(alwaysRun = true)
    public void openApplication() {
        DriverFactory.getDriver().get(ConfigReader.get("base.url"));
    }

    @AfterMethod(alwaysRun = true)
    public void resetSession(ITestResult result) {
        if (!result.isSuccess()) {
            DriverFactory.getDriver().manage().deleteAllCookies();
        }
    }

    @AfterTest(alwaysRun = true)
    public void tearDownDriver() {
        DriverFactory.quitDriver();
    }
}
