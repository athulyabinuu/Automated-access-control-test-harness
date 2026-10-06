# SECUREHUB – Enterprise Security Portal

**SECUREHUB** is a complete, enterprise-grade web application built using Python, Flask, Flask-Login, and SQLite. Designed as a security portal, it features full authentication, role-based access control (RBAC), fine-grained resource ownership enforcement, and modern web UI standards.

---

## Features

- **User Authentication**: Secure session-based login and password hashing (`scrypt`/`PBKDF2` via Werkzeug).
- **Asynchronous POST Logout**: Modern JavaScript `fetch()` API logout clearing Flask-Login session and preventing duplicate logout requests.
- **Role-Based Access Control (RBAC)**:
  - `User`: Standard operational privileges for owned resources.
  - `Manager`: Extended departmental access to orders, documents, and tickets.
  - `Admin`: Full system administration, user provisioning, and telemetry access.
- **Resource Management**:
  - **Dashboard**: Real-time database metrics, recent orders, and security notifications.
  - **User Directory**: Search and view enterprise users (Admin management with user creation & role assignment).
  - **Departments**: Organizational structure and member tracking.
  - **Orders**: Procurement tracking with ownership checks.
  - **Documents**: Confidential repository with strict ownership enforcement (`/documents/<id>`).
  - **Tickets**: Security support incident management with priority levels and status transitions.
  - **Reports**: Audit and compliance scan reports.
  - **Notifications**: Personal user alert center with read status tracking.
  - **Settings**: Email updates and password change with current password verification.
  - **Admin Control Panel**: Restricted zone enforcing 403 Forbidden for non-admin accounts.
- **Custom Error Pages**: Professional handling of 403 Forbidden, 404 Not Found, and 500 Internal Server Errors.

---

## Technology Stack

- **Backend**: Python 3.10+, Flask 3.1, Flask-SQLAlchemy, Flask-Login, Werkzeug
- **Database**: SQLite 3 (SQLAlchemy ORM)
- **Frontend**: HTML5, CSS3 (Enterprise Dark Navy & Blue theme), Vanilla JavaScript (ES6+), Jinja2 Templates
- **Testing**: Pytest 9.1+

---

## Installation & Setup

### 1. Prerequisites
Ensure Python 3.10+ is installed on your system.

### 2. Virtual Environment Setup
Navigate to the project directory and create a virtual environment:

```bash
cd C:\Users\Hp\.gemini\antigravity\scratch\securehub
python -m venv .venv
```

Activate the virtual environment:
- **Windows (PowerShell)**:
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Database Initialization

The application automatically creates and seeds the database (`instance/securehub.db`) with 10 realistic demo accounts across 5 departments on initial launch.

---

## Running the Server

Start the application using:

```bash
python app.py
```

The server will start at: `http://127.0.0.1:5000/`

---

## Demo Test Credentials (10 Accounts)

Use these pre-seeded demo accounts for testing authentication and authorization levels:

| # | Username | Password | Role | Department | Access Scope |
| :- | :--- | :--- | :--- | :--- | :--- |
| 1 | `alice` | `alice123` | **User** | IT | Standard user (IT department) |
| 2 | `bob` | `bob123` | **Manager** | Finance | Department manager (Finance) |
| 3 | `admin` | `admin123` | **Admin** | IT | System Administrator (Full access & `/admin`) |
| 4 | `charlie` | `charlie123` | **User** | HR | Standard user (HR department) |
| 5 | `david` | `david123` | **User** | Sales | Standard user (Sales department) |
| 6 | `emma` | `emma123` | **Manager** | HR | Department manager (HR) |
| 7 | `frank` | `frank123` | **User** | Finance | Standard user (Finance department) |
| 8 | `grace` | `grace123` | **User** | Sales | Standard user (Sales department) |
| 9 | `henry` | `henry123` | **Manager** | IT | Department manager (IT) |
| 10 | `isla` | `isla123` | **User** | Operations | Standard user (Operations department) |

> ⚠️ *Note: Passwords are encrypted using Werkzeug secure password hashing (scrypt / PBKDF2).*

---

## Automated Testing

Run the automated test suite using `pytest`:

```bash
pytest -v
```

All tests cover:
- Valid and invalid login authentication
- POST `/api/auth/logout` endpoint, session clearing, and duplicate request safety
- Role-based authorization and Admin page protection (403 Forbidden)
- Document ownership restriction (`/documents/<id>`) and notification isolation
- Page rendering for all routes across all 10 users
