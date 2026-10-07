# Access-Control Test Harness

A Python-based security testing framework for automated authentication and authorization testing of web applications and APIs.

The Access-Control Test Harness is designed to identify access-control weaknesses by testing different users, roles, resources, and authorization boundaries.

The project supports API and web authorization testing and generates HTML, PDF, and JSON security reports.

The repository also includes controlled target applications for reproducible security testing and demonstration.

---

## 1. Project Overview

Access-control vulnerabilities occur when an application does not correctly restrict what authenticated or unauthenticated users can access.

Examples include:

- Horizontal privilege escalation
- Vertical privilege escalation
- IDOR-style access-control weaknesses
- Missing authentication checks
- Invalid-token handling problems
- Incorrect role-based authorization
- Unauthorized resource modification
- Unauthorized resource deletion

The Access-Control Test Harness automates these checks against controlled applications.

The framework separates:

1. Discovery
2. Authentication
3. Resource discovery
4. Authorization policy
5. Test generation
6. Test execution
7. Finding generation
8. Report generation

This allows the same testing engine to work with different target applications.

---

## 2. Project Objectives

The main objectives of the project are:

- Automate authentication testing.
- Automate authorization testing.
- Discover API endpoints automatically.
- Support OpenAPI-based testing.
- Support passive HTML and JavaScript route discovery.
- Discover application resources and resource IDs.
- Test horizontal authorization boundaries.
- Test vertical authorization boundaries.
- Test anonymous and invalid-token access.
- Test role-based access control.
- Safely handle destructive operations.
- Generate detailed security reports.
- Provide reproducible results using controlled target applications.
- Keep the testing engine independent from a specific target application.

---

## 3. Key Features

### 3.1 API Discovery

The harness can discover API routes using:

- Local OpenAPI specifications
- Remote OpenAPI specifications
- HTML source
- JavaScript source
- Fetch calls
- Axios calls
- Explicit HTTP methods
- Common API route patterns

### 3.2 Authentication Testing

The framework supports:

- Session-based authentication
- JWT-based authentication
- Administrative users
- Normal users
- Anonymous requests
- Invalid-token testing
- Login success and failure testing

### 3.3 Authorization Testing

The framework tests:

- Authentication boundaries
- Horizontal authorization
- Vertical authorization
- Role-based access
- Ownership-based access
- Resource-level authorization

### 3.4 Resource Discovery

The framework can discover resource IDs from collection endpoints.

For example:

```text
GET /api/documents
GET /api/documents/{doc_id}
```

The collection endpoint can be used to discover valid document IDs before testing the item endpoint.

### 3.5 Reporting

The harness generates:

- HTML reports
- PDF reports
- JSON reports

Reports contain:

- Test ID
- Category
- HTTP method
- Request path
- Tested role
- Expected status
- Actual status
- Result
- Description
- Failure information

---

## 4. Architecture

The project follows a modular architecture.

```text
                         +----------------------+
                         |     Target App       |
                         |  API / Web App       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |      Discovery       |
                         | OpenAPI / HTML / JS  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Resource Discovery   |
                         | Resource IDs / Roles |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   Authentication     |
                         | Admin / User / JWT   |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |  Authorization       |
                         |       Policy         |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   Test Generator     |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |      Execution       |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Finding Generation   |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |      Reporting       |
                         | HTML / PDF / JSON    |
                         +----------------------+
```

The design keeps discovery, test generation, execution, and reporting separate so that the framework can be extended to additional target applications.

---

## 5. Discovery Modes

The harness supports multiple API discovery approaches.

### 5.1 OpenAPI Discovery

When an OpenAPI specification is available, the harness can use it as the primary source of API information.

The specification provides information such as:

- Endpoint paths
- HTTP methods
- Parameters
- Request bodies
- Authentication requirements
- Response information

Example:

```yaml
paths:
  /api/documents/{doc_id}:
    get:
      parameters:
        - name: doc_id
          in: path
          required: true
          schema:
            type: integer
```

The harness uses this information to generate access-control tests.

### 5.2 Local OpenAPI Discovery

A local OpenAPI file can be supplied directly.

Example:

```bash
python3 -m harness.orchestrator \
  --url https://example.com \
  --target-name "Example" \
  --openapi-file target/openapi.yaml
```

This is useful when the target application already provides an OpenAPI specification in the project repository.

### 5.3 Remote OpenAPI Discovery

The harness can also search common OpenAPI locations on the target.

Examples include:

```text
/openapi.json
/openapi.yaml
/swagger.json
/api/openapi.json
/v3/api-docs
```

If a valid OpenAPI document is found, it is used for API discovery.

### 5.4 Passive HTML and JavaScript Discovery

If OpenAPI is not available, the framework can inspect HTML and JavaScript source.

The discovery system looks for:

- API URLs
- API paths
- fetch()
- axios()
- API helper functions
- HTTP method declarations
- HTML form actions
- Links
- Script sources

Example:

```javascript
fetch("/api/auth/logout", {
    method: "POST"
});
```

The harness can identify:

```text
POST /api/auth/logout
```

### 5.5 Discovery Priority

The orchestrator follows this general priority:

```text
1. Explicit local OpenAPI specification
              |
              v
2. Automatic remote OpenAPI discovery
              |
              v
3. Passive HTML / JavaScript discovery
```

This allows the framework to use the most structured information available while still supporting applications without OpenAPI documentation.

---

## 6. Authentication

Authentication is required before authorization testing can be performed correctly.

The harness supports different authentication mechanisms.

### 6.1 Session Authentication

Session-based applications can be tested using:

```text
Username
Password
Session Cookie
```

The framework logs in and stores the resulting authentication state.

### 6.2 JWT Authentication

JWT-based APIs can be tested using:

```text
Username
Password
JWT Token
Authorization Header
```

Example:

```http
Authorization: Bearer <token>
```

### 6.3 Multiple User Roles

The framework can test different users.

Typical roles include:

```text
Admin
Manager
User
Anonymous
```

The actual roles depend on the target application's authorization policy.

### 6.4 Anonymous Testing

Anonymous requests are important because protected endpoints should normally reject unauthenticated access.

Expected responses may include:

```text
401 Unauthorized
403 Forbidden
302 Redirect
```

The expected behavior is defined by the target's authorization policy.

---

## 7. Resource Discovery

Authorization testing often requires valid resource IDs.

For example:

```text
GET /api/documents
```

may return:

```json
{
  "documents": [
    {"id": 8},
    {"id": 9}
  ]
}
```

The framework can use these IDs when testing:

```text
GET /api/documents/8
GET /api/documents/9
```

### 7.1 Resource Ownership

The harness separates resources into logical categories such as:

```text
own
other
another
```

Example:

```text
admin:
    own: 1
    other: 2
    another: 3
```

This allows the test generator to test different ownership boundaries.

### 7.2 Resource Type Inference

Resource names can be inferred from path parameters.

Example:

```text
doc_id
```

can be interpreted as:

```text
doc
```

This allows resource discovery to remain independent from a specific target application.

---

## 8. Authorization Policy

Authorization rules define which users should be allowed to access specific resources.

A policy may contain rules such as:

```text
Anonymous:
    protected endpoint -> denied

User:
    own resource -> allowed
    another user's resource -> denied

Admin:
    protected resource -> allowed
```

The exact policy depends on the target application.

The test generator uses these rules to determine expected responses.

---

## 9. Test Generation

The test generator creates candidate tests from:

- Discovered routes
- HTTP methods
- Authentication state
- User roles
- Resource IDs
- Authorization policy
- Path parameters

Each generated test contains information such as:

```text
Test ID
Category
HTTP Method
Path
Role
Expected Status Codes
Parameter Overrides
Description
```

Example:

```text
AC-0001
Category: authentication
Method: GET
Path: /api/documents
Role: anonymous
Expected: 401 / 403 / 302
```

---

## 10. Web Authorization Testing

The framework can test web application authorization boundaries.

Examples include:

```text
GET /profile
GET /documents
GET /documents/{id}
POST /documents
DELETE /documents/{id}
```

The harness checks whether users receive the expected authorization response.

---

## 11. Horizontal Privilege Escalation Testing

Horizontal privilege escalation occurs when one user can access another user's resources without the required permission.

Example:

```text
User A owns document 8.

User B attempts:

GET /api/documents/8
```

If the application incorrectly allows User B to access the resource, the test can be reported as a failure.

The harness uses discovered resource IDs to perform these tests automatically.

---

## 12. Vertical Privilege Escalation Testing

Vertical privilege escalation occurs when a lower-privileged user can access functionality intended for a higher-privileged role.

Example:

```text
Admin:
    DELETE /api/users/{id}

Normal User:
    attempts the same operation
```

The expected result should normally be an authorization denial unless the application's policy explicitly permits the operation.

---

## 13. Authentication Boundary Testing

The harness also tests requests without valid authentication.

Examples include:

```text
Anonymous request
Invalid session
Invalid JWT
Missing authentication
```

The expected result depends on the application's security policy.

Typical protected-endpoint responses are:

```text
401
403
302
```

---

## 14. Destructive-Test Safety

Some authorization tests can modify or delete data.

Examples:

```text
DELETE
PUT
PATCH
POST
```

To prevent accidental destructive actions, the harness supports an explicit safety option.

Example:

```bash
--allow-destructive
```

Destructive tests should only be enabled when the target application is controlled and safe to modify.

Example:

```bash
python3 -m harness.orchestrator \
  configs/target.target1.yaml \
  --allow-destructive
```

Never run destructive tests against systems without authorization.

---

## 15. Finding Generation

After executing a test, the framework compares:

```text
Expected Status
        vs
Actual Status
```

The result is classified as:

```text
PASS
FAIL
ERROR
```

### PASS

PASS means the application returned a response that matches the expected authorization behavior.

Example:

```text
Expected: 403
Actual:   403

Result: PASS
```

### FAIL

FAIL means the application returned behavior that does not match the expected security policy.

Example:

```text
Expected: 403
Actual:   200

Result: FAIL
```

A FAIL can represent an authorization weakness or another unexpected security behavior.

### ERROR

ERROR means the test could not be executed correctly because of a testing or configuration problem.

Examples:

```text
Missing authentication data
Missing resource ID
Invalid test configuration
Connection failure
```

ERROR should not be treated as PASS or FAIL.

---

## 16. Controlled Target Applications

The repository contains controlled applications for security testing.

### 16.1 Target 1

Target 1 is a controlled secure application used to verify that the harness correctly identifies expected secure behavior.

The final demonstration result is:

```text
40 PASS
0 FAIL
0 ERROR
40 TOTAL
```

Overall result:

```text
PASS
```

### 16.2 SECUREHUB

SECUREHUB is a controlled intentionally vulnerable demonstration application created for the project.

It is used to demonstrate that the harness can identify unexpected authorization behavior.

The final demonstration result is:

```text
30 PASS
2 FAIL
0 ERROR
32 TOTAL
```

Overall result:

```text
FAIL
```

The two FAIL results are retained because the application intentionally demonstrates behavior that does not match the expected authorization policy.

The harness should report the actual result rather than artificially converting vulnerabilities into PASS results.

### 16.3 Other Supported Targets

The project structure can also support additional controlled applications such as:

```text
Target 2
WebGoat
Juice Shop
Other approved local or test environments
```

These targets can be used for development and future testing.

---

## 17. Final Demonstration Results

### Target 1

```text
Target: Target 1

PASS   : 40
FAIL   : 0
ERROR  : 0
TOTAL  : 40

Overall: PASS
```

### SECUREHUB

```text
Target: SECUREHUB

PASS   : 30
FAIL   : 2
ERROR  : 0
TOTAL  : 32

Overall: FAIL
```

The difference demonstrates two important capabilities of the framework:

1. It can verify secure authorization behavior.
2. It can identify authorization behavior that does not match the expected security policy.

---

## 18. Reports

The final demonstration reports are stored in:

```text
reports/
```

### Target 1 Reports

```text
reports/Target_1_access_control_report.html
reports/Target_1_access_control_report.json
reports/Target_1_access_control_report.pdf
```

### SECUREHUB Reports

```text
reports/SECUREHUB_access_control_report.html
reports/SECUREHUB_access_control_report.json
reports/SECUREHUB_access_control_report.pdf
```

### HTML Report

The HTML report provides a browser-friendly view of the test results.

### PDF Report

The PDF report provides a shareable security assessment document.

### JSON Report

The JSON report provides machine-readable test results that can be processed by other tools.

---

## 19. Project Structure

```text
access-control-test-harness/
│
├── configs/
│   ├── target.target1.yaml
│   ├── target.target2.yaml
│   ├── target.target2.baseline_policy.json
│   └── target.securehub.yaml
│
├── harness/
│   ├── api_route_discovery.py
│   ├── authentication.py
│   ├── discovery.py
│   ├── execution.py
│   ├── orchestrator.py
│   ├── reporting.py
│   ├── resource_discovery.py
│   └── test_generator.py
│
├── target1-app/
│   ├── app.py
│   ├── openapi.yaml
│   └── ...
│
├── securehub/
│   ├── app.py
│   ├── openapi.yaml
│   ├── routes/
│   ├── models/
│   ├── templates/
│   ├── static/
│   └── ...
│
├── reports/
│   ├── Target_1_access_control_report.html
│   ├── Target_1_access_control_report.json
│   ├── Target_1_access_control_report.pdf
│   ├── SECUREHUB_access_control_report.html
│   ├── SECUREHUB_access_control_report.json
│   └── SECUREHUB_access_control_report.pdf
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 20. Important Modules

### `harness/orchestrator.py`

Responsible for:

- Loading target configuration
- Selecting discovery mode
- Loading authorization policy
- Running authentication
- Generating tests
- Executing tests
- Producing reports

### `harness/discovery.py`

Responsible for:

- OpenAPI discovery
- Remote OpenAPI discovery
- HTML discovery
- JavaScript discovery

### `harness/api_route_discovery.py`

Responsible for:

- Discovering API routes from source code
- Detecting fetch calls
- Detecting Axios calls
- Detecting explicit HTTP methods

### `harness/resource_discovery.py`

Responsible for:

- Discovering resources
- Extracting resource IDs
- Determining resource ownership
- Building role-based resource data

### `harness/authentication.py`

Responsible for:

- Login
- Session authentication
- JWT authentication
- Authentication state

### `harness/test_generator.py`

Responsible for:

- Generating authorization tests
- Generating authentication tests
- Creating horizontal authorization tests
- Creating vertical authorization tests
- Creating invalid-token tests

### `harness/execution.py`

Responsible for:

- Sending HTTP requests
- Applying authentication
- Applying cookies and tokens
- Resolving resource placeholders
- Comparing actual and expected responses

### `harness/reporting.py`

Responsible for:

- HTML report generation
- PDF report generation
- JSON report generation
- Summary statistics

---

## 21. Installation

Clone the repository:

```bash
git clone <repository-url>
cd access-control-test-harness
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Verify Python compilation:

```bash
python3 -m py_compile harness/*.py
```

---

## 22. Configure Credentials

Credentials should not be committed to the repository.

For Target 1, credentials can be provided through environment variables.

Example:

```bash
export ADMIN_USERNAME='admin'
export ADMIN_PASSWORD='your-admin-password'
export USER_USERNAME='user1'
export USER_PASSWORD='your-user-password'
```

Use the actual credentials configured in the controlled target environment.

Do not place real passwords, API keys, tokens, or secrets in:

```text
README.md
Git commits
GitHub issues
Screenshots
Public documentation
```

---

## 23. Running Target 1

Start the Target 1 application in the target environment.

Then configure credentials:

```bash
export ADMIN_USERNAME='admin'
export ADMIN_PASSWORD='your-admin-password'
export USER_USERNAME='user1'
export USER_PASSWORD='your-user-password'
```

Run:

```bash
python3 -m harness.orchestrator \
  configs/target.target1.yaml \
  --allow-destructive
```

Expected final result:

```text
40 PASS
0 FAIL
0 ERROR
40 TOTAL
```

---

## 24. Running SECUREHUB

SECUREHUB can be tested against the approved deployed demonstration environment or another controlled deployment.

Example:

```bash
python3 -m harness.orchestrator \
  --url https://securehub-di8a.onrender.com \
  --target-name "SECUREHUB" \
  --openapi-file securehub/openapi.yaml \
  --admin-user 'admin' \
  --admin-pass 'your-admin-password' \
  --user-user 'charlie' \
  --user-pass 'your-user-password' \
  --login-path '/api/auth/login' \
  --username-field 'username' \
  --password-field 'password' \
  --auth-type session
```

The command uses the local OpenAPI specification from:

```text
securehub/openapi.yaml
```

The final controlled demonstration result is:

```text
30 PASS
2 FAIL
0 ERROR
32 TOTAL
```

The FAIL results should remain visible because they demonstrate behavior that does not match the expected authorization policy.

---

## 25. Policy Learning

The project can use a baseline authorization policy to define expected behavior.

A policy can describe:

```text
Role
Resource
Operation
Expected Access
```

Example:

```json
{
  "role": "user",
  "resource": "document",
  "operation": "read",
  "access": "own"
}
```

Policy learning allows the framework to generate tests according to the expected access-control model.

The policy should represent the intended security behavior of the target application.

---

## 26. Git Collaboration Workflow

The project uses a shared `main` branch for collaboration.

Each team member works on their assigned modules and commits their genuine work using their own GitHub-linked account.

Before starting work:

```bash
git checkout main
git pull origin main
```

Make the assigned changes.

Check the changes:

```bash
git status
git diff
```

Stage only the files belonging to the work:

```bash
git add <file>
```

Commit:

```bash
git commit -m "Describe the change"
```

Push:

```bash
git push origin main
```

If another team member has pushed changes before you:

```bash
git pull --rebase origin main
git push origin main
```

Do not force-push to the shared `main` branch.

---

## 27. Team Members and Responsibilities

### Athulya Binu

**Core Execution**

Responsible for:

```text
harness/orchestrator.py
harness/execution.py
```

Main responsibilities:

- Test execution
- Target orchestration
- Authentication state handling during execution
- Request execution
- Expected vs actual result comparison
- Integration of the complete testing pipeline

### Abishiha S

**API & Resource Discovery**

Responsible for:

```text
harness/discovery.py
harness/api_route_discovery.py
harness/resource_discovery.py
```

Main responsibilities:

- OpenAPI discovery
- Remote API discovery
- HTML/JavaScript discovery
- API route detection
- Resource discovery
- Resource ID extraction
- Resource ownership discovery

### Jyothykrishna C V

**Authentication & Test Generation**

Responsible for:

```text
harness/authentication.py
harness/test_generator.py
```

Main responsibilities:

- Authentication
- Session handling
- JWT handling
- Authentication test generation
- Authorization test generation
- Horizontal authorization tests
- Vertical authorization tests
- Invalid-token testing

### Adithya A S

**Reporting & Target Applications**

Responsible for:

```text
harness/reporting.py
target1-app/
securehub/
```

Main responsibilities:

- HTML reports
- PDF reports
- JSON reports
- Target application maintenance
- Target 1 controlled application
- SECUREHUB controlled demonstration application

---

## 28. Testing Recommendations

Testing should be performed only against:

- Local applications
- Authorized test environments
- Applications specifically provided for security testing
- Controlled vulnerable applications

Recommended workflow:

```text
1. Start the target application
2. Verify the target is reachable
3. Verify authentication credentials
4. Run discovery
5. Verify discovered endpoints
6. Run resource discovery
7. Generate tests
8. Execute tests
9. Review PASS / FAIL / ERROR
10. Review generated reports
```

For destructive tests:

```text
Use --allow-destructive only when appropriate.
```

---

## 29. Limitations

The framework has some limitations.

### Application-Specific Behavior

Different applications may use different:

- Authentication mechanisms
- Authorization rules
- Response codes
- Resource structures

Therefore, configuration and policies may need to be adjusted for each target.

### Resource Discovery

Resource discovery depends on the application exposing usable collection endpoints or discoverable resource information.

### Dynamic Applications

Some dynamically generated routes may not be visible through passive source-code discovery.

### Authentication

Applications using complex multi-step authentication, MFA, CAPTCHA, or browser-only authentication may require additional integration.

### Authorization Policy

The framework requires an expected authorization model to determine whether an observed response is correct.

---

## 30. Security and Ethical Use

This project is intended for authorized security testing and education.

Do not use the framework against systems without permission.

The framework can send requests that test authentication and authorization boundaries. Some tests can also be destructive when explicitly enabled.

Always ensure that:

```text
You own the target
OR
You have explicit permission to test the target
```

Use controlled environments whenever possible.

---

## 31. Verification

Before committing changes, verify Python syntax:

```bash
python3 -m py_compile harness/*.py
```

Check repository status:

```bash
git status
```

Check changed files:

```bash
git diff
```

Check untracked files:

```bash
git status --short --untracked-files=all
```

Run the final Target 1 test:

```bash
python3 -m harness.orchestrator \
  configs/target.target1.yaml \
  --allow-destructive
```

Run the final SECUREHUB test:

```bash
python3 -m harness.orchestrator \
  --url https://securehub-di8a.onrender.com \
  --target-name "SECUREHUB" \
  --openapi-file securehub/openapi.yaml \
  --admin-user 'admin' \
  --admin-pass 'your-admin-password' \
  --user-user 'charlie' \
  --user-pass 'your-user-password' \
  --login-path '/api/auth/login' \
  --username-field 'username' \
  --password-field 'password' \
  --auth-type session
```

Verify that the final reports exist:

```bash
ls -lh reports/
```

Expected report files:

```text
Target_1_access_control_report.html
Target_1_access_control_report.json
Target_1_access_control_report.pdf
SECUREHUB_access_control_report.html
SECUREHUB_access_control_report.json
SECUREHUB_access_control_report.pdf
```

---

## 32. Final Project Outcome

The completed project demonstrates an automated access-control testing workflow.

The framework can:

```text
Discover APIs
     ↓
Authenticate users
     ↓
Discover resources
     ↓
Build authorization policy
     ↓
Generate security tests
     ↓
Execute requests
     ↓
Compare expected and actual behavior
     ↓
Identify PASS / FAIL / ERROR
     ↓
Generate HTML / PDF / JSON reports
```

The final demonstration verifies both secure and intentionally vulnerable behavior.

### Target 1

```text
40 PASS
0 FAIL
0 ERROR
40 TOTAL
```

This demonstrates expected secure authorization behavior.

### SECUREHUB

```text
30 PASS
2 FAIL
0 ERROR
32 TOTAL
```

This demonstrates that the framework can identify behavior that violates the expected authorization policy.

The project therefore demonstrates automated access-control testing rather than simply sending individual manual requests.

---

## 33. Repository

The project is maintained as a collaborative Git repository.

The repository contains:

```text
Harness source code
Target applications
Configuration files
Authorization policies
Test reports
Documentation
```

Team members should commit only their own genuine work and use their own GitHub-linked accounts so that contributions are correctly attributed.

---

## 34. Project Goal

The main goal of the Access-Control Test Harness is to provide a reusable and target-independent framework for testing authentication and authorization controls.

The project demonstrates how automated security testing can help identify:

- Missing authentication
- Incorrect authorization
- Horizontal privilege escalation
- Vertical privilege escalation
- Resource-level access-control weaknesses
- Unexpected authentication behavior

The framework is designed to be extended with additional discovery methods, authentication mechanisms, authorization policies, target applications, and security tests.

---

## 35. Responsible Use

This project is intended for:

- Cybersecurity education
- Security testing in controlled environments
- Authorized penetration testing
- Application security research
- Demonstration of access-control concepts

Only test systems for which you have explicit authorization.

Never use this framework to access, modify, or delete data belonging to another person or organization without permission.

---

## License

This project is developed for educational and authorized security-testing purposes.

Use responsibly and only within permitted environments.

---

## Contributors

- Athulya Binu
- Adithya A S
- Jyothykrishna C V
- Abishiha
