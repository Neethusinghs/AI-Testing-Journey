package com.salesforce.automation.pages;

import java.time.Duration;

import org.openqa.selenium.NoSuchElementException;
import org.openqa.selenium.StaleElementReferenceException;
import org.openqa.selenium.TimeoutException;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.FindBy;
import org.openqa.selenium.support.PageFactory;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import com.salesforce.automation.config.ConfigReader;
import com.salesforce.automation.exceptions.FrameworkException;

public class LoginPage {

    private static final String LOGIN_HOST = "login.salesforce.com";
    private static final Duration SINGLE_STEP_PROBE = Duration.ofSeconds(2);

    private final WebDriver driver;
    private final WebDriverWait wait;

    @FindBy(xpath = "//input[@id='username']")
    private WebElement usernameField;

    @FindBy(xpath = "//input[@id='password']")
    private WebElement passwordField;

    @FindBy(xpath = "//input[@id='Login']")
    private WebElement loginButton;

    @FindBy(xpath = "//input[@id='rememberUn']")
    private WebElement rememberMeCheckbox;

    @FindBy(xpath = "//div[@id='error']")
    private WebElement errorBanner;

    @FindBy(xpath = "//div[contains(@class,'loginError') and normalize-space(text())!='']")
    private WebElement genericErrorBanner;

    @FindBy(xpath = "//a[@id='forgot_password_link']")
    private WebElement forgotPasswordLink;

    @FindBy(xpath = "//input[@id='username' and @aria-invalid='true']")
    private WebElement usernameInvalidState;

    @FindBy(xpath = "//input[@id='password' and @aria-invalid='true']")
    private WebElement passwordInvalidState;

    public LoginPage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(ConfigReader.getInt("explicit.wait")));
        PageFactory.initElements(driver, this);
    }

    public LoginPage waitForLoginPageToLoad() {
        try {
            wait.until(ExpectedConditions.visibilityOf(usernameField));
            wait.until(ExpectedConditions.elementToBeClickable(loginButton));
            return this;
        } catch (TimeoutException | NoSuchElementException e) {
            throw new FrameworkException("Login page did not load: username field or Log In button was not interactive", e);
        }
    }

    public LoginPage enterUsername(String username) {
        try {
            WebElement field = wait.until(ExpectedConditions.elementToBeClickable(usernameField));
            field.clear();
            field.sendKeys(username);
            return this;
        } catch (TimeoutException | NoSuchElementException e) {
            throw new FrameworkException("Unable to enter the username", e);
        }
    }

    public LoginPage clickLogin() {
        try {
            wait.until(ExpectedConditions.elementToBeClickable(loginButton)).click();
            return this;
        } catch (TimeoutException | NoSuchElementException e) {
            throw new FrameworkException("Unable to click the Log In button", e);
        }
    }

    public LoginPage waitForPasswordStep() {
        try {
            wait.until(ExpectedConditions.visibilityOf(passwordField));
            return this;
        } catch (TimeoutException | NoSuchElementException e) {
            throw new FrameworkException("The password step did not render after submitting the username", e);
        }
    }

    public LoginPage enterPassword(String password) {
        try {
            WebElement field = wait.until(ExpectedConditions.visibilityOf(passwordField));
            field.clear();
            field.sendKeys(password);
            return this;
        } catch (TimeoutException | NoSuchElementException e) {
            throw new FrameworkException("Unable to enter the password: the field was not rendered", e);
        }
    }

    public LoginPage login(String username, String password) {
        waitForLoginPageToLoad().enterUsername(username);
        if (!isPasswordFieldPresent(SINGLE_STEP_PROBE)) {
            clickLogin();
        }
        return waitForPasswordStep().enterPassword(password).clickLogin();
    }

    public LoginPage setRememberMe(boolean selected) {
        try {
            WebElement checkbox = wait.until(ExpectedConditions.elementToBeClickable(rememberMeCheckbox));
            if (checkbox.isSelected() != selected) {
                checkbox.click();
            }
            return this;
        } catch (TimeoutException | NoSuchElementException e) {
            throw new FrameworkException("Unable to set the Remember me checkbox to " + selected, e);
        }
    }

    public boolean isRememberMeSelected() {
        try {
            return wait.until(ExpectedConditions.visibilityOf(rememberMeCheckbox)).isSelected();
        } catch (TimeoutException | NoSuchElementException e) {
            throw new FrameworkException("The Remember me checkbox is not available", e);
        }
    }

    public boolean isUsernameDisplayed() {
        return isElementDisplayed(usernameField);
    }

    public boolean isPasswordFieldPresent(Duration timeout) {
        try {
            wait.withTimeout(timeout).until(ExpectedConditions.visibilityOf(passwordField));
            return true;
        } catch (TimeoutException | NoSuchElementException e) {
            return false;
        }
    }

    public boolean isForgotPasswordLinkDisplayed() {
        return isElementDisplayed(forgotPasswordLink);
    }

    public boolean isErrorMessageDisplayed() {
        return !readBannerText(errorBanner).isEmpty();
    }

    public String getErrorMessage() {
        String message = readBannerText(errorBanner);
        if (!message.isEmpty()) {
            return message;
        }
        try {
            return genericErrorBanner.getText().trim();
        } catch (NoSuchElementException | StaleElementReferenceException e) {
            throw new FrameworkException("No login error message was rendered by the page", e);
        }
    }

    public boolean isUsernameMarkedInvalid() {
        return isElementDisplayed(usernameInvalidState);
    }

    public boolean isPasswordMarkedInvalid() {
        return isElementDisplayed(passwordInvalidState);
    }

    public boolean isOnLoginPage() {
        return driver.getCurrentUrl().contains(LOGIN_HOST);
    }

    public String getCurrentUrl() {
        return driver.getCurrentUrl();
    }

    public void waitForSuccessfulLogin() {
        try {
            wait.until(ExpectedConditions.not(ExpectedConditions.urlContains(LOGIN_HOST)));
        } catch (TimeoutException e) {
            throw new FrameworkException("Login was not successful, still on " + driver.getCurrentUrl(), e);
        }
    }

    private boolean isElementDisplayed(WebElement element) {
        try {
            return element.isDisplayed();
        } catch (NoSuchElementException | StaleElementReferenceException e) {
            return false;
        }
    }

    private String readBannerText(WebElement banner) {
        try {
            return wait.until(ExpectedConditions.visibilityOf(banner)).getText().trim();
        } catch (TimeoutException | NoSuchElementException e) {
            return "";
        }
    }
}
