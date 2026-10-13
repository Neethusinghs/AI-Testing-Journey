package com.salesforce.automation.driver;

import java.time.Duration;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;

import com.salesforce.automation.config.ConfigReader;
import com.salesforce.automation.exceptions.FrameworkException;

public final class DriverFactory {

    private static final ThreadLocal<WebDriver> DRIVER = new ThreadLocal<>();

    private DriverFactory() {
    }

    public static WebDriver initDriver() {
        WebDriver existing = DRIVER.get();
        if (existing != null) {
            return existing;
        }
        String browser = ConfigReader.get("browser", "chrome");
        if (!"chrome".equalsIgnoreCase(browser)) {
            throw new FrameworkException("Unsupported browser configured: " + browser);
        }
        try {
            WebDriver driver = new ChromeDriver(buildChromeOptions());
            driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(ConfigReader.getInt("implicit.wait")));
            DRIVER.set(driver);
            return driver;
        } catch (Exception e) {
            throw new FrameworkException("ChromeDriver could not be started", e);
        }
    }

    public static WebDriver getDriver() {
        WebDriver driver = DRIVER.get();
        if (driver == null) {
            throw new FrameworkException("WebDriver has not been initialised for this thread");
        }
        return driver;
    }

    public static WebDriver getDriverOrNull() {
        return DRIVER.get();
    }

    public static void quitDriver() {
        WebDriver driver = DRIVER.get();
        if (driver == null) {
            return;
        }
        try {
            driver.quit();
        } catch (Exception e) {
            throw new FrameworkException("WebDriver could not be closed cleanly", e);
        } finally {
            DRIVER.remove();
        }
    }

    private static ChromeOptions buildChromeOptions() {
        ChromeOptions options = new ChromeOptions();
        options.addArguments("--window-size=1920,1080");
        options.addArguments("--disable-notifications");
        options.addArguments("--remote-allow-origins=*");
        if (ConfigReader.getBoolean("headless")) {
            options.addArguments("--headless=new");
            options.addArguments("--no-sandbox");
            options.addArguments("--disable-dev-shm-usage");
        }
        return options;
    }
}
