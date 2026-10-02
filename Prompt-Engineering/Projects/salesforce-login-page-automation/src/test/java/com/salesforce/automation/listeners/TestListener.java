package com.salesforce.automation.listeners;

import org.testng.ITestContext;
import org.testng.ITestListener;
import org.testng.ITestResult;

import com.salesforce.automation.driver.DriverFactory;
import com.salesforce.automation.utils.ScreenshotUtil;

public class TestListener implements ITestListener {

    @Override
    public void onTestFailure(ITestResult result) {
        String screenshotPath = ScreenshotUtil.capture(DriverFactory.getDriverOrNull(), result.getName());
        StringBuilder report = new StringBuilder("[FAILED] ").append(result.getName());
        if (result.getThrowable() != null) {
            report.append(" :: ").append(result.getThrowable().getMessage());
        }
        if (screenshotPath != null) {
            report.append(" :: screenshot=").append(screenshotPath);
        }
        System.out.println(report);
    }

    @Override
    public void onTestSkipped(ITestResult result) {
        String reason = result.getThrowable() == null ? "no reason supplied" : result.getThrowable().getMessage();
        System.out.println("[SKIPPED] " + result.getName() + " :: " + reason);
    }

    @Override
    public void onFinish(ITestContext context) {
        System.out.println("[SUITE] " + context.getName()
                + " passed=" + context.getPassedTests().size()
                + " failed=" + context.getFailedTests().size()
                + " skipped=" + context.getSkippedTests().size());
    }
}
