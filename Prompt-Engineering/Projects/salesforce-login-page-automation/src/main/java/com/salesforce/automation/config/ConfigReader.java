package com.salesforce.automation.config;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

import com.salesforce.automation.exceptions.FrameworkException;

public final class ConfigReader {

    private static final String CONFIG_FILE = "config.properties";
    private static final Properties PROPERTIES = new Properties();

    private ConfigReader() {
    }

    public static synchronized void load() {
        if (!PROPERTIES.isEmpty()) {
            return;
        }
        try (InputStream stream = ConfigReader.class.getClassLoader().getResourceAsStream(CONFIG_FILE)) {
            if (stream == null) {
                throw new FrameworkException(CONFIG_FILE + " was not found on the classpath");
            }
            PROPERTIES.load(stream);
        } catch (IOException e) {
            throw new FrameworkException("Failed to read " + CONFIG_FILE, e);
        }
    }

    public static String get(String key) {
        String value = resolve(key);
        if (value == null) {
            throw new FrameworkException("Missing mandatory configuration key: " + key);
        }
        return value.trim();
    }

    public static String get(String key, String defaultValue) {
        String value = resolve(key);
        return value == null ? defaultValue : value.trim();
    }

    public static int getInt(String key) {
        String value = get(key);
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            throw new FrameworkException("Configuration key " + key + " is not numeric: " + value, e);
        }
    }

    public static boolean getBoolean(String key) {
        return Boolean.parseBoolean(get(key, "false"));
    }

    private static String resolve(String key) {
        load();
        String systemValue = System.getProperty(key);
        if (systemValue != null && !systemValue.isBlank()) {
            return systemValue;
        }
        String environmentValue = System.getenv(toEnvironmentKey(key));
        if (environmentValue != null && !environmentValue.isBlank()) {
            return environmentValue;
        }
        return PROPERTIES.getProperty(key);
    }

    private static String toEnvironmentKey(String key) {
        return key.toUpperCase().replace('.', '_').replace('-', '_');
    }
}
