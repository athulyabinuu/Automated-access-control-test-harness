# Automated Access-Control Test Harness

A Python-based security testing framework for automated authentication and authorization testing of web applications and APIs.

The **Automated Access-Control Test Harness** is designed to identify access-control weaknesses by testing different users, roles, resources, ownership boundaries, and authorization rules.

The framework supports API and web authorization testing and generates **HTML, PDF, and JSON security reports**.

The repository also includes controlled target applications and approved vulnerable applications for reproducible security testing and demonstration.

---

## 1. Project Overview

Access-control vulnerabilities occur when an application does not correctly restrict what authenticated or unauthenticated users can access.

Examples include:

* Horizontal privilege escalation
* Vertical privilege escalation
* IDOR/BOLA vulnerabilities
* Missing authentication checks
* Invalid-token handling problems
* Incorrect role-based authorization
* Unauthorized resource modification
* Unauthorized resource deletion

The Access-Control Test Harness automates these checks against controlled or authorized applications.

The framework separates:

1. API and endpoint discovery
2. Authentication
3. Resource discovery
4. Ownership evidence discovery
5. Authorization policy
6. Test generation
7. Test execution
8. Finding classification
9. Report generation

This separation allows the testing engine to work with different target applications.

---

## 2. Project Objectives

The main objectives are:

* Automate authentication testing.
* Automate authorization testing.
* Discover API endpoints automatically.
* Support OpenAPI-based testing.
* Support passive HTML and JavaScript route discovery.
* Discover application resources and resource IDs.
* Test horizontal authorization boundaries.
* Test vertical authorization boundaries.
* Test anonymous and invalid-token access.
* Test role-based access control.
* Test resource ownership boundaries.
* Detect BOLA/IDOR-style access-control weaknesses.
* Use JWT claims as independent ownership evidence when available.
* Reduce false positives during ownership testing.
* Safely handle destructive operations.
* Generate HTML, PDF, and JSON security reports.
* Provide reproducible results.
* Keep the testing engine independent from a specific target application.

---

## 3. Key Features

### 3.1 API Discovery

The harness can discover API routes using:

* Local OpenAPI specifications
* Remote OpenAPI specifications
* HTML source
* JavaScript source
* Fetch calls
* Axios calls
* Explicit HTTP methods
* Common API route patterns

### 3.2 Authentication Testing

The framework supports:

* Session-based authentication
* JWT-based authentication
* Administrative users
* Normal users
* Anonymous requests
* Invalid-token testing
* Login success and failure testing

### 3.3 Authorization Testing

The framework tests:

* Authentication boundaries
* Horizontal authorization
* Vertical authorization
* Role-based authorization
* Ownership-based authorization
* Resource-level authorization
* Own-resource access
* Other-resource access

### 3.4 Resource Discovery

The framework can discover resource IDs from collection endpoints.

Example:

```text
GET /api/documents
GET /api/documents/{doc_id}
```

The collection endpoint can be used to discover valid document IDs before testing item-level endpoints.

### 3.5 BOLA / IDOR Detection

The harness can test whether a user can access a resource belonging to another user.

The ownership-testing flow is:

```text
Authenticated User
       ↓
JWT Ownership Evidence
       ↓
Identify Own Resource
       ↓
Identify Other Resource
       ↓
Request Other Resource
       ↓
Compare With Expected Policy
       ↓
PASS / FAIL / INCONCLUSIVE
```

This provides stronger evidence than simply changing an ID and checking whether the server returns HTTP 200.

### 3.6 JWT Ownership Evidence

For JWT-authenticated applications, the framework can decode JWT claims and use relevant ownership information as independent evidence.

For example:

```json
{
  "sub": "2",
  "email": "user@example.com"
}
```

If a resource contains an owner/user identifier that can be reliably mapped to the authenticated JWT subject, the framework can establish ownership.

The ownership evidence is then used during test generation.

Conceptually:

```text
Resource
   ↓
Ownership Evidence
   ↓
Authorization Policy
   ↓
Expected Result
```

### 3.7 False-Positive Prevention

The framework avoids treating ambiguous identifiers as ownership evidence.

For example, a path parameter such as:

```text
bid
```

may represent a basket identifier in one endpoint but may not represent ownership in another endpoint.

The framework therefore uses explicit resource mappings where required and avoids unsafe assumptions.

It also protects against ambiguous multi-parameter paths where more than one parameter could represent a resource identifier.

### 3.8 Inconclusive Results

Not every authorization test can reliably determine whether a resource belongs to the current user.

Instead of incorrectly reporting such cases as vulnerabilities, the framework supports a fourth result state:

```text
PASS
FAIL
SKIPPED
INCONCLUSIVE
```

`INCONCLUSIVE` means that the test executed or was considered, but reliable ownership or expected authorization evidence was not available.

This helps reduce false-positive security findings.

### 3.9 Reporting

The harness generates:

* HTML reports
* PDF reports
* JSON reports

Reports contain information such as:

* Test ID
* Category
* HTTP method
* Request path
* Tested role
* Expected status
* Actual status
* Result
* Description
* Failure information

---

## 4. Architecture

The current architecture is:

```text
                    Target Application
                           |
                           v
                    Endpoint Discovery
                           |
                           v
                    Resource Discovery
                           |
                           v
                  Ownership Evidence
                           |
                           v
                  Authentication
                           |
                           v
                 Authorization Policy
                           |
                           v
                    Test Generation
                           |
                           v
                     Test Execution
                           |
                           v
                  Finding Classification
                           |
                           v
                       Reporting
```

The ownership-aware authorization model is:

```text
Resource
   ↓
Ownership Evidence
   ↓
Policy
   ↓
Expected Result
   ↓
Test
   ↓
Observed Response
   ↓
PASS / FAIL / SKIPPED / INCONCLUSIVE
```

The design keeps discovery, ownership analysis, test generation, execution, and reporting separate so the framework can be extended to additional targets.

---

## 5. Discovery Modes

### 5.1 OpenAPI Discovery

OpenAPI is the preferred structured discovery source when available.

It provides information such as:

* API paths
* HTTP methods
* Parameters
* Request bodies
* Authentication requirements
* Response information

Example:

```yaml
paths:
  /api/documents:
    get:
      responses:
        "200":
          description: Success
```

### 5.2 Local OpenAPI Discovery

Example:

```bash
python3 -m harness.orchestrator \
  --url https://example.com \
  --target-name "Example" \
  --openapi-file target/openapi.yaml
```

### 5.3 Remote OpenAPI Discovery

The framework can check common locations such as:

```text
/openapi.json
/openapi.yaml
/swagger.json
/api/openapi.json
/v3/api-docs
```

### 5.4 Passive HTML and JavaScript Discovery

When OpenAPI is unavailable, the framework can inspect application source code.

It can identify:

* API URLs
* API paths
* Fetch calls
* Axios calls
* Angular HttpClient calls
* HTTP method declarations
* HTML form actions
* Links
* Script sources
* Common API route patterns

Example:

```javascript
fetch("/api/auth/logout", {
    method: "POST"
})
```

can be identified as:

```text
POST /api/auth/logout
```

### 5.5 Discovery Priority

The preferred discovery order is:

```text
1. Explicit local OpenAPI
2. Automatic remote OpenAPI
3. Passive HTML / JavaScript discovery
```

---

## 6. Authentication

Authentication is required before most authorization tests can be performed.

### 6.1 Session Authentication

Session-based applications can use:

```text
Username
Password
Session Cookie
```

The framework logs in and maintains the authentication state for subsequent requests.

### 6.2 JWT Authentication

JWT-based APIs can be tested using:

```text
Username
Password
JWT Token
Authorization Header
```

Example:

```text
Authorization: Bearer <token>
```

### 6.3 Multiple User Roles

The framework can support roles such as:

```text
Admin
Manager
User
Anonymous
```

The actual roles depend on the target application's policy.

### 6.4 Anonymous Testing

Protected endpoints can be tested without authentication.

Expected responses may include:

```text
401 Unauthorized
403 Forbidden
302 Redirect
```

depending on the application's policy.

### 6.5 Invalid Token Testing

The framework can also test behavior when an invalid or unusable authentication token is supplied.

---

## 7. Resource Discovery

Resource discovery identifies valid resources that can be used during authorization testing.

Example:

```text
GET /api/documents
```

may return:

```json
[
  {
    "id": 8
  },
  {
    "id": 9
  }
]
```

The discovered IDs can then be tested against:

```text
GET /api/documents/8
GET /api/documents/9
```

### 7.1 Resource Ownership

Resources can be categorized as:

```text
own
other
another
```

Example:

```yaml
admin:
  own: 1
  other: 2
  another: 3
```

This allows the test generator to create ownership-boundary tests.

### 7.2 Resource Type Inference

The framework can infer resource types from route parameters.

For example:

```text
/api/documents/{doc_id}
```

can identify:

```text
doc_id → document resource
```

The goal is to keep resource discovery as target-independent as possible.

---

## 8. Ownership Evidence

Ownership evidence is used to determine whether a resource belongs to the authenticated user.

Possible evidence sources include:

* JWT claims
* Resource owner identifiers
* Authenticated user identity
* Explicit target-specific mappings

For JWT-based applications, relevant claims can be decoded and compared with resource ownership information.

Example:

```text
JWT subject = 2
Resource owner = 2

→ Own resource
```

If the values do not match:

```text
JWT subject = 2
Resource owner = 5

→ Other user's resource
```

The framework only creates strict ownership tests when the ownership relationship can be established with sufficient confidence.

---

## 9. BOLA / IDOR Testing

**BOLA** stands for Broken Object Level Authorization.

It occurs when a user can access another user's object by changing an object identifier or otherwise manipulating the request.

Example:

```text
User A
   |
   +---- owns resource 8

User B
   |
   +---- owns resource 9
```

A BOLA test attempts:

```text
User B → GET /api/resource/8
```

If the application allows unauthorized access:

```text
Expected: 403
Actual:   200
Result:   FAIL
```

### 9.1 Own-Resource Testing

The framework first verifies access to the authenticated user's own resource.

Example:

```text
User B → Resource 9
Expected: ALLOW
```

### 9.2 Other-Resource Testing

The framework then attempts to access a resource associated with another user.

Example:

```text
User B → Resource 8
Expected: DENY
```

### 9.3 Ownership Evidence

Ownership testing is based on independent ownership evidence where possible.

The framework does not assume that every numeric path parameter represents an owner-controlled resource.

### 9.4 Ambiguous Ownership

When ownership cannot be established reliably, the framework reports:

```text
INCONCLUSIVE
```

rather than incorrectly reporting:

```text
FAIL
```

This is especially important for APIs containing multiple identifiers or application-specific relationships.

---

## 10. Authorization Policy

The authorization policy defines the expected security behavior of the target application.

Example:

```json
{
  "role": "user",
  "resource": "document",
  "operation": "read",
  "access": "own"
}
```

Example expected behavior:

```text
Anonymous protected endpoint → DENY
User own resource           → ALLOW
User other resource         → DENY
Admin protected resource    → ALLOW
```

The test generator uses the policy to determine expected responses.

---

## 11. Test Generation

Tests are generated from:

* Discovered routes
* HTTP methods
* Authentication state
* User roles
* Resource IDs
* Ownership evidence
* Authorization policy
* Path parameters

Generated tests contain information such as:

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
Category: Authentication
Method: GET
Path: /api/documents
Role: anonymous
Expected: 401/403/302
```

Ownership-aware tests may contain:

```text
Category: Horizontal Authorization
Resource: document
Ownership: other
Expected: DENY
```

---

## 12. Web Authorization Testing

The framework can test web endpoints such as:

```text
GET /profile
GET /documents
GET /documents/{id}
POST /documents
DELETE /documents/{id}
```

The observed response is compared with the expected authorization policy.

---

## 13. Horizontal Privilege Escalation

Horizontal authorization testing checks whether one user can access another user's resources.

Example:

```text
User A owns document 8
User B owns document 9
```

The harness tests:

```text
User B → GET /api/documents/8
```

Expected:

```text
DENY
```

If the application incorrectly allows access:

```text
Expected: DENY
Actual:   ALLOW
Result:   FAIL
```

This is a key mechanism used for BOLA/IDOR detection.

---

## 14. Vertical Privilege Escalation

Vertical authorization testing checks whether a lower-privileged user can perform operations intended for a higher-privileged role.

Example:

```text
Admin → DELETE /api/users/{id}
User  → DELETE /api/users/{id}
```

Expected:

```text
Admin → ALLOW
User  → DENY
```

Unexpected access is reported as a failure.

---

## 15. Authentication Boundary Testing

The framework can test:

```text
Anonymous request
Invalid session
Invalid JWT
Missing authentication
Expired or unusable authentication state
```

Expected behavior depends on the target policy.

---

## 16. Result Classification

The framework supports four result states:

### PASS

The observed behavior matches the expected security policy.

### FAIL

The observed behavior violates the expected security policy.

Example:

```text
Expected: 403
Actual:   200
Result:   FAIL
```

### SKIPPED

The test was not executed because the required conditions were unavailable or the test was intentionally excluded.

### INCONCLUSIVE

The test could not establish a sufficiently reliable security conclusion.

For example:

```text
Resource ownership cannot be reliably established
```

The framework uses `INCONCLUSIVE` to avoid treating uncertain ownership relationships as confirmed vulnerabilities.

### ERROR

`ERROR` represents a testing or configuration problem such as:

* Missing configuration
* Connection failure
* Invalid test setup
* Missing required authentication state
* Unexpected execution exception

`ERROR` is different from a security `FAIL`.

---

## 17. Destructive-Test Safety

Some HTTP methods can modify application state.

Examples:

```text
POST
PUT
PATCH
DELETE
```

Destructive testing must be explicitly enabled.

Example:

```bash
python3 -m harness.orchestrator \
  configs/target.target1.yaml \
  --allow-destructive
```

Never run destructive tests against systems without authorization.

---

## 18. Controlled and Tested Applications

The repository contains controlled applications for reproducible security testing.

The framework can also be used against approved vulnerable applications and authorized testing environments.

### 18.1 Target 1

Target 1 is a controlled application used to verify expected secure behavior.

The latest demonstration result is:

```text
35 PASS
0 FAIL
5 SKIPPED
0 INCONCLUSIVE
0 ERROR
40 TOTAL
```

Overall:

```text
PASS
```

### 18.2 SECUREHUB

SECUREHUB is a controlled intentionally vulnerable demonstration application created for the project.

It is used to demonstrate that the harness can identify unexpected authorization behavior.

The demonstration result is:

```text
30 PASS
2 FAIL
0 ERROR
32 TOTAL
```

The two FAIL results are retained because the application intentionally demonstrates behavior that does not match the expected authorization policy.

### 18.3 OWASP Juice Shop

The harness was also tested against **OWASP Juice Shop** as an additional vulnerable target.

The current test execution generated:

```text
102 TOTAL
```

Results:

```text
74 PASS
4 FAIL
4 SKIPPED
20 INCONCLUSIVE
0 ERROR
```

The four FAIL results correspond to identified BOLA/IDOR authorization findings.

The INCONCLUSIVE results represent cases where ownership could not be established with sufficient confidence.

This demonstrates the benefit of separating confirmed authorization failures from uncertain ownership cases.

### 18.4 Other Supported Targets

The project structure can support additional controlled or authorized applications such as:

```text
Target 2
WebGoat
OWASP Juice Shop
Other approved local or test environments
```

---

## 19. Final Demonstration Results

### Target 1

```text
Target: Target 1

PASS         : 35
FAIL         : 0
SKIPPED      : 5
INCONCLUSIVE : 0
ERROR        : 0
TOTAL        : 40

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

### OWASP Juice Shop

```text
Target: OWASP Juice Shop

PASS         : 74
FAIL         : 4
SKIPPED      : 4
INCONCLUSIVE : 20
ERROR        : 0
TOTAL        : 102
```

The Juice Shop results demonstrate that the framework can:

1. Identify confirmed authorization failures.
2. Test own-resource and other-resource access.
3. Use JWT ownership evidence.
4. Avoid unsupported ownership assumptions.
5. Classify uncertain cases as INCONCLUSIVE.

---

## 20. Reports

The generated security assessment reports are stored in:

```text
reports/
```

Available report formats:

* HTML
* PDF
* JSON

### HTML Report

Provides a browser-friendly view of the test results.

### PDF Report

Provides a shareable security assessment document.

### JSON Report

Provides machine-readable test results that can be processed by other tools.

### Generated Report Files

**Target 1**

* `reports/Target_1_access_control_report.html`
* `reports/Target_1_access_control_report.pdf`
* `reports/Target_1_access_control_report.json`

**SECUREHUB**

* `reports/SECUREHUB_access_control_report.html`
* `reports/SECUREHUB_access_control_report.pdf`
* `reports/SECUREHUB_access_control_report.json`

**OWASP Juice Shop**

* `reports/OWASP_Juice_Shop_access_control_report.html`
* `reports/OWASP_Juice_Shop_access_control_report.pdf`
* `reports/OWASP_Juice_Shop_access_control_report.json`

### OWASP Juice Shop Assessment Summary

The recorded assessment contains 102 test results:

| Result       |   Count |
| ------------ | ------: |
| PASS         |      74 |
| FAIL         |       4 |
| SKIPPED      |       4 |
| INCONCLUSIVE |      20 |
| ERROR        |       0 |
| **TOTAL**    | **102** |

The four FAIL results were recorded as potential access-control findings requiring review against the expected authorization policy. INCONCLUSIVE results indicate that the available evidence was insufficient to make a reliable authorization determination.

These results describe the recorded test execution; they do not independently establish that every finding has been manually confirmed.


## 21. Project Structure

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
│   ├── test_generator.py
│   └── web_execution.py
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
│   ├── SECUREHUB_access_control_report.pdf
│   ├── OWASP_Juice_Shop_access_control_report.html
│   ├── OWASP_Juice_Shop_access_control_report.json
│   └── OWASP_Juice_Shop_access_control_report.pdf
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 22. Important Modules

### `harness/orchestrator.py`

Responsible for:

* Loading target configuration
* Selecting discovery mode
* Loading authorization policy
* Running authentication
* Generating tests
* Executing tests
* Classifying results
* Producing reports

### `harness/discovery.py`

Responsible for:

* OpenAPI discovery
* Remote OpenAPI discovery
* HTML discovery
* JavaScript discovery

### `harness/api_route_discovery.py`

Responsible for:

* Source-code API discovery
* Fetch detection
* Axios detection
* Angular HttpClient detection
* HTTP method detection
* Common API route detection

### `harness/resource_discovery.py`

Responsible for:

* Discovering resources
* Extracting resource IDs
* Determining resource ownership
* JWT ownership evidence
* Building role-based resource data
* Applying target-specific ownership mappings where necessary

### `harness/authentication.py`

Responsible for:

* Login
* Session authentication
* JWT authentication
* Authentication state

### `harness/test_generator.py`

Responsible for:

* Authentication test generation
* Authorization test generation
* Horizontal authorization tests
* Vertical authorization tests
* Invalid-token tests
* Ownership-aware BOLA/IDOR tests
* Inconclusive ownership handling

### `harness/execution.py`

Responsible for:

* Sending HTTP requests
* Applying authentication
* Applying cookies and tokens
* Resolving resource placeholders
* Comparing actual and expected responses

### `harness/web_execution.py`

Responsible for:

* Web authorization request execution
* Session handling
* Web-specific response processing

### `harness/reporting.py`

Responsible for:

* HTML report generation
* PDF report generation
* JSON report generation
* Result summaries
* PASS / FAIL / SKIPPED / INCONCLUSIVE / ERROR reporting

---

## 23. Installation

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

## 24. Configure Credentials

Credentials should not be committed to the repository.

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

## 25. Running Target 1

Start the Target 1 application in the target environment.

Configure credentials:

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

The latest demonstration produced:

```text
35 PASS
0 FAIL
5 SKIPPED
0 INCONCLUSIVE
0 ERROR
40 TOTAL
```

---

## 26. Running SECUREHUB

SECUREHUB can be tested against an approved controlled deployment.

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

The command uses:

```text
securehub/openapi.yaml
```

The demonstration result is:

```text
30 PASS
2 FAIL
0 ERROR
32 TOTAL
```

The FAIL results should remain visible because they demonstrate behavior that does not match the expected authorization policy.

---

## 27. Policy Learning

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

## 28. Git Collaboration Workflow

The project uses Git for collaborative development.

Each team member works on assigned modules and commits their genuine work using their own GitHub-linked account.

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

If another team member has pushed changes:

```bash
git pull --rebase origin main
git push origin main
```

Do not force-push to the shared `main` branch.

---

## 29. Team Members and Responsibilities

### Athulya Binu

**Core Execution**

Responsible for:

```text
harness/orchestrator.py
harness/execution.py
```

Main responsibilities:

* Test execution
* Target orchestration
* Authentication state handling during execution
* Request execution
* Expected vs actual result comparison
* Integration of the complete testing pipeline

### Abishiha S

**API & Resource Discovery**

Responsible for:

```text
harness/discovery.py
harness/api_route_discovery.py
harness/resource_discovery.py
```

Main responsibilities:

* OpenAPI discovery
* Remote API discovery
* HTML/JavaScript discovery
* API route detection
* Resource discovery
* Resource ID extraction
* Resource ownership discovery

### Jyothykrishna C V

**Authentication & Test Generation**

Responsible for:

```text
harness/authentication.py
harness/test_generator.py
```

Main responsibilities:

* Authentication
* Session handling
* JWT handling
* Authentication test generation
* Authorization test generation
* Horizontal authorization tests
* Vertical authorization tests
* Invalid-token testing
* Ownership-aware authorization test generation

### Adithya A S

**Reporting & Target Applications**

Responsible for:

```text
harness/reporting.py
target1-app/
securehub/
```

Main responsibilities:

* HTML reports
* PDF reports
* JSON reports
* Target application maintenance
* Target 1 controlled application
* SECUREHUB controlled demonstration application

---

## 30. Testing Recommendations

Testing should be performed only against:

* Local applications
* Authorized test environments
* Applications specifically provided for security testing
* Controlled vulnerable applications

Recommended workflow:

```text
1. Start the target application
2. Verify the target is reachable
3. Verify authentication credentials
4. Run endpoint discovery
5. Verify discovered endpoints
6. Run resource discovery
7. Establish ownership evidence where possible
8. Load or infer authorization policy
9. Generate tests
10. Execute tests
11. Review PASS / FAIL / SKIPPED / INCONCLUSIVE / ERROR
12. Review generated reports
```

For destructive tests:

```text
Use --allow-destructive only when appropriate.
```

---

## 31. Limitations

### Application-Specific Behavior

Different applications may use different:

* Authentication mechanisms
* Authorization rules
* Response codes
* Resource structures
* Ownership models

Configuration and policies may therefore need to be adjusted for each target.

### Resource Discovery

Resource discovery depends on the application exposing usable collection endpoints or discoverable resource information.

### Ownership Discovery

Ownership testing requires reliable evidence connecting an authenticated user to a resource.

JWT claims can provide useful evidence, but not every application exposes ownership information in its token.

### Dynamic Applications

Some dynamically generated routes may not be visible through passive source-code discovery.

### Authentication

Applications using complex multi-step authentication, MFA, CAPTCHA, or browser-only authentication may require additional integration.

### Authorization Policy

The framework requires an expected authorization model to determine whether an observed response is correct.

### Inconclusive Cases

Some tests may not provide enough evidence to confirm either secure or insecure ownership behavior.

These cases are reported as:

```text
INCONCLUSIVE
```

instead of being treated as confirmed vulnerabilities.

---

## 32. Security and Ethical Use

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

## 33. Verification

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

Run the Target 1 test:

```bash
python3 -m harness.orchestrator \
  configs/target.target1.yaml \
  --allow-destructive
```

Verify generated reports:

```bash
ls -lh reports/
```

---

## 34. Final Project Outcome

The completed project demonstrates an automated access-control testing workflow.

The overall process is:

```text
Discover APIs
     ↓
Authenticate Users
     ↓
Discover Resources
     ↓
Establish Ownership Evidence
     ↓
Build Authorization Policy
     ↓
Generate Security Tests
     ↓
Execute Requests
     ↓
Compare Expected and Actual Behavior
     ↓
Classify Results
     ↓
Generate HTML / PDF / JSON Reports
```

The framework supports:

```text
Authentication Testing
Authorization Testing
Horizontal Authorization Testing
Vertical Authorization Testing
Resource-Level Authorization
BOLA / IDOR Testing
JWT Ownership Evidence
False-Positive Prevention
Inconclusive Classification
Automated Reporting
```

### Target 1

```text
35 PASS
0 FAIL
5 SKIPPED
0 INCONCLUSIVE
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

### OWASP Juice Shop

```text
74 PASS
4 FAIL
4 SKIPPED
20 INCONCLUSIVE
0 ERROR
102 TOTAL
```

This demonstrates the framework's BOLA/IDOR testing capability using ownership evidence and its ability to distinguish confirmed findings from uncertain ownership cases.

The project therefore demonstrates automated access-control testing rather than simply sending individual manual requests.

---

## 35. Repository

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

## 36. Project Goal

The main goal of the Automated Access-Control Test Harness is to provide a reusable and target-independent framework for testing authentication and authorization controls.

The project demonstrates how automated security testing can help identify:

* Missing authentication
* Incorrect authorization
* Horizontal privilege escalation
* Vertical privilege escalation
* BOLA / IDOR vulnerabilities
* Resource-level access-control weaknesses
* Unexpected authentication behavior
* Ownership-related authorization failures

The addition of independent ownership evidence and the `INCONCLUSIVE` result state helps the framework make more reliable authorization decisions while reducing false-positive BOLA/IDOR findings.
