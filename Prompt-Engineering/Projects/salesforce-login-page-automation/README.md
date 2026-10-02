# Salesforce Login Automation Framework

Enterprise-grade UI automation for `https://login.salesforce.com/?locale=in` built with **Selenium 4**, **Java 17**, **Maven** and **TestNG**.

## Stack

| Concern | Choice |
|---|---|
| Language | Java 17 (`maven.compiler.release`) |
| UI driver | Selenium Java 4.49.0 |
| Test runner | TestNG 7.12.0 |
| Driver binaries | Selenium Manager (bundled from Selenium 4.6+) — no `WebDriverManager` dependency |
| Locators | **XPath only** — no CSS selectors, `By.id`, `By.name` or any other strategy |
| Waits | Explicit `WebDriverWait` only — `Thread.sleep` is banned and `implicit.wait=0` |

## Layout

```
salesforce-automation/
├── pom.xml
├── testng.xml
└── src/
    ├── main/java/com/salesforce/automation/
    │   ├── config/ConfigReader.java        # config.properties + -D / env override
    │   ├── driver/DriverFactory.java       # ThreadLocal WebDriver lifecycle
    │   ├── pages/LoginPage.java            # Page Object (PageFactory)
    │   └── exceptions/FrameworkException.java
    └── test/
        ├── java/com/salesforce/automation/
        │   ├── base/BaseTest.java          # @BeforeTest / @BeforeMethod / @AfterMethod / @AfterTest
        │   ├── listeners/TestListener.java # failure screenshots + run summary
        │   ├── utils/ScreenshotUtil.java
        │   ├── tests/ValidLoginTest.java
        │   └── tests/InvalidLoginTest.java
        └── resources/config.properties
```

## Configuration

Values resolve in this order: **JVM system property → environment variable → `config.properties`**.

| Key | Env var | Default | Purpose |
|---|---|---|---|
| `base.url` | `BASE_URL` | `https://login.salesforce.com/?locale=in` | Application under test |
| `browser` | `BROWSER` | `chrome` | Browser to launch |
| `headless` | `HEADLESS` | `true` | Headless Chrome (`--headless=new`) |
| `implicit.wait` | `IMPLICIT_WAIT` | `0` | Intentionally zero — explicit waits only |
| `explicit.wait` | `EXPLICIT_WAIT` | `15` | `WebDriverWait` timeout in seconds |
| `sf.username` | `SF_USERNAME` | *(empty)* | Salesforce username |
| `sf.password` | `SF_PASSWORD` | *(empty)* | Salesforce password |
| `sf.expected.error` | `SF_EXPECTED_ERROR` | `Please check your username and password` | Expected invalid-login message |

Credentials are never committed. Supply them per run.

## Running

```bash
mvn clean test
```

Invalid-login tests need no credentials and run against the live site. Valid-login tests **skip** (not fail) until credentials are supplied:

```bash
mvn test -Dsf.username=you@example.com -Dsf.password=secret
```

Watch the browser:

```bash
mvn test -Dheadless=false
```

Reports land in `target/surefire-reports/`; failure screenshots in `target/screenshots/`.

## The login flow (verified against the live page)

`login.salesforce.com/?locale=in` **does not show a password field on load**. It is a two-step flow:

| Step | Action | DOM state |
|---|---|---|
| 1 | Load page | `#username`, `#Login`, `#rememberUn` present — **no password field** |
| 2 | Enter username → click Log In | page re-posts, URL becomes `https://login.salesforce.com/` |
| 3 | Password step | `input[type=password][id=password][name=pw]` now renders |
| 4 | Enter password → click Log In | success navigates away; failure renders `#error` |

Observed failure message: `Error: Please check your username and password. If you still can't log in, contact your Salesforce administrator.`

`LoginPage.login` models this directly and also tolerates the single-step variant (username + password on one screen): it probes for the password field with a short 2-second wait, clicks Log In only if it is absent, then waits for the password step. No `Thread.sleep` is needed at any point because every transition is an element-visibility condition.

## Design notes

**Every wait is condition-based.** `LoginPage` waits on `visibilityOf` / `elementToBeClickable` for each transition, including the step-1 → step-2 render of the password field. This is why `Thread.sleep` is banned here: the password field appears only after a server round-trip, so a fixed delay would be both slower and less reliable than waiting for the element itself.

**Locators verified against the live DOM.** Every `@FindBy` maps to an attribute confirmed on the real page: `username`, `password`, `Login`, `rememberUn`, `error`, `forgot_password_link`.

**`implicit.wait=0` on purpose.** Mixing implicit and explicit waits is the classic source of unpredictable timeouts; this framework uses explicit waits exclusively.

**Lazy PageFactory proxies.** `PageFactory.initElements` locates elements on first access, and `NoSuchElementException` extends `NotFoundException`, which `WebDriverWait` ignores by default — so waiting on a not-yet-rendered field retries until timeout instead of failing instantly.

**Empty-form submission is tested separately.** Clicking Log In with a blank form does not necessarily render the password field or the `#error` banner, so `verifyEmptyCredentialsAreRejected` asserts that *an* error state surfaces (error text or `aria-invalid`), keeping the test deterministic.

**Single point of maintenance.** If Salesforce redesigns the login page, only `LoginPage.java` changes.

## Not covered

Multi-factor authentication, Lightning/classic landing-page assertions beyond "left the login page", and cross-browser execution. Post-login assertions intentionally target leaving the login page because the landing surface depends on org configuration.
