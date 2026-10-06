from pathlib import Path


# ============================================================
# Professional terminal colours
# Terminal colours are kept separate from HTML/PDF colours.
# ============================================================

TERM_RESET = "\033[0m"
TERM_BOLD = "\033[1m"
TERM_DIM = "\033[2m"

TERM_CYAN = "\033[96m"       # Section headings / important information
TERM_BLUE = "\033[38;5;39m"       # Major headings / separator lines
TERM_GREEN = "\033[92m"      # PASS / successful operations
TERM_RED = "\033[91m"        # FAIL
TERM_GOLD = "\033[93m"       # Warnings / state checks
TERM_WHITE = "\033[97m"      # Normal test details
TERM_GRAY = "\033[90m"       # Secondary details

import argparse
import os
import sys
from datetime import datetime
from html import escape

import requests
import yaml
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)


# ============================================================
# TARGET CONFIGURATION
# ============================================================
TARGETS = {
    "1": {
        "name": "Website Target 1",
        "url": "http://website-target-1"
    },
    "2": {
        "name": "Website Target 2",
        "url": "http://website-target-2"
    },
    "4": {
        "name": "Live Website",
        "url": "http://127.0.0.1:3000"
    }
}
# ============================================================
# TARGET SELECTION
# ============================================================

def select_target():

    terminal_banner("AUTOMATED ACCESS CONTROL TEST HARNESS")

    print()
    print("Available targets:")
    print()

    for key, target in TARGETS.items():
        print(f"  {key}. {target['name']}")

    print()

    while True:

        choice = input(
            "Select target [1/2/4]: "
        ).strip()

        if choice in TARGETS:

            target = TARGETS[choice]

            print()
            print(
                f"Selected target : {target['name']}"
            )

            print(
                f"Target URL      : {target['url']}"
            )

            print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)

            return (
                target["url"],
                target["name"]
            )

        print()
        print("Invalid choice.")
        print("Please enter 1, 2, or 4.")
        print()

# ============================================================
# RUNTIME CONFIGURATION
#
# These are intentionally initialized without selecting a target.
# The target is selected by run_tests(), either from CLI arguments
# or from the interactive menu.
# ============================================================

BASE_URL = None
TARGET_NAME = None

# ============================================================
# GENERAL CONFIGURATION
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ROLE_MATRICES = {
    "Website Target 1": os.path.join(
        BASE_DIR,
        "role_matrix_target1.yaml"
    ),
    "Website Target 2": os.path.join(
        BASE_DIR,
        "role_matrix_target2.yaml"
    ),
}

ROLE_MATRIX = os.path.join(
    BASE_DIR,
    "role_matrix.yaml"
)


REPORT_DIR = os.path.join(
    BASE_DIR,
    "reports"
)

# Report paths are initialized after CLI target selection.
SAFE_TARGET_NAME = "target"
HTML_REPORT = None
PDF_REPORT = None

REQUEST_TIMEOUT = 5


# ============================================================
# TEST USERS
#
# Credentials can be overridden with environment variables.
# ============================================================

USERS = {
    "admin": {
        "username": os.getenv(
            "ADMIN_USERNAME",
            "admin"
        ),
        "password": os.getenv(
            "ADMIN_PASSWORD",
            "admin123"
        ),
    },

    "user": {
        "username": os.getenv(
            "USER_USERNAME",
            "user1"
        ),
        "password": os.getenv(
            "USER_PASSWORD",
            "user123"
        ),
    },
}

# ============================================================
# ACTIVE TEST USERS
# ============================================================

ACTIVE_USERS = USERS

# ============================================================
# TEST RESOURCE IDs
# ============================================================

RESOURCE_IDS = {}

# ============================================================
# COLOURS
# ============================================================

NAVY = "#172554"
BLUE = "#2563EB"
BLUE_DARK = "#1D4ED8"

# ============================================================
# TERMINAL COLOURS
# ============================================================

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_BLUE = "\033[94m"
ANSI_CYAN = "\033[96m"
ANSI_GREEN = "\033[92m"
ANSI_RED = "\033[91m"
ANSI_YELLOW = "\033[93m"
ANSI_WHITE = "\033[97m"
ANSI_DIM = "\033[2m"


def terminal_banner(title, width=60):
    print()
    print(f"{ANSI_BLUE}{ANSI_BOLD}{'=' * width}{ANSI_RESET}")
    print(
        f"{ANSI_BLUE}{ANSI_BOLD}"
        f"{title.center(width)}"
        f"{ANSI_RESET}"
    )
    print(f"{ANSI_BLUE}{ANSI_BOLD}{'=' * width}{ANSI_RESET}")


def terminal_heading(title, width=60):
    print()
    print(f"{ANSI_BLUE}{ANSI_BOLD}{title}{ANSI_RESET}")
    print(f"{ANSI_BLUE}{'-' * width}{ANSI_RESET}")


def status_colour(status):
    return {
        "PASS": ANSI_GREEN,
        "FAIL": ANSI_RED,
        "SKIP": ANSI_YELLOW,
    }.get(status, ANSI_WHITE)


GREEN = "#16A34A"
GREEN_DARK = "#166534"
LIGHT_GREEN = "#DCFCE7"

RED = "#DC2626"
RED_DARK = "#991B1B"
LIGHT_RED = "#FEE2E2"

LIGHT_BLUE = "#EFF6FF"
LIGHTER_BLUE = "#F8FAFC"

PURPLE = "#7C3AED"
LIGHT_PURPLE = "#EDE9FE"

ORANGE = "#EA580C"
LIGHT_ORANGE = "#FFEDD5"

DARK = "#0F172A"
SLATE = "#64748B"
BORDER = "#CBD5E1"
WHITE = "#FFFFFF"



# ============================================================
# LOAD ROLE MATRIX
def load_role_matrix():

    matrix_file = ROLE_MATRIX

    try:

        with open(
            matrix_file,
            "r",
            encoding="utf-8"
        ) as file:

            data = yaml.safe_load(file)

        if not data or "roles" not in data:

            raise ValueError(
                f"{os.path.basename(matrix_file)} "
                "does not contain a 'roles' section."
            )

        return data

    except FileNotFoundError:

        print()
        print(
            f"ERROR: {os.path.basename(matrix_file)} not found."
        )
        print(
            f"Expected location: "
            f"{os.path.abspath(matrix_file)}"
        )
        print()

        sys.exit(1)

    except yaml.YAMLError as error:

        print()
        print(
            f"ERROR: Invalid YAML in "
            f"{os.path.basename(matrix_file)}."
        )
        print(error)
        print()

        sys.exit(1)
# ============================================================
# TARGET CHECK
# ============================================================

def check_target():

    print()
    print("Checking target server...")
    print("-" * 60)

    try:

        response = requests.get(
            BASE_URL,
            timeout=REQUEST_TIMEOUT
        )

        print(
            f"Target response: HTTP {response.status_code}"
        )

        print(
            f"Target URL     : {BASE_URL}"
        )

        print("-" * 60)

        return True

    except requests.RequestException as error:

        print()
        print("ERROR: Target server is not reachable.")
        print()
        print(f"URL: {BASE_URL}")
        print()
        print(
            "Make sure the selected target application "
            "is running before starting the harness."
        )
        print()
        print(f"Details: {error}")
        print("-" * 60)
        return False




# ============================================================
# LOGIN
# ============================================================

# ============================================================
# TOKEN TEST
# ============================================================

def get_invalid_token():

    return "invalid.jwt.token"

# ============================================================
# REQUEST DATA
# ============================================================

def request_data(
    method,
    path,
    role=None
):

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    if method == "POST" and path == "/api/login":

        users = USERS

        if role in users:
            return {
                "username": users[role]["username"],
                "password": users[role]["password"],
            }

        return {
            "username": users["user"]["username"],
            "password": users["user"]["password"],
        }

    # --------------------------------------------------------
    # PATCH
    # --------------------------------------------------------

    if method == "PATCH":

        return {
            "email": "updated@example.com"
        }

    # --------------------------------------------------------
    # Create user
    # --------------------------------------------------------

    if method == "POST" and path == "/api/users":

        return {
            "email": "newuser@example.com",
            "password": "newpass123",
            "role": "user"
        }

    # --------------------------------------------------------
    # Other PUT requests
    # --------------------------------------------------------

    if method == "PUT":

        return {
            "email": "updated@example.com"
        }

    return None

# ============================================================
# RESOURCE STATE VALIDATION
# ============================================================

def get_resource_state(path, token):
    try:
        state_path = path

        # Admin DELETE endpoint does not support GET.
        # Resolve it to the corresponding user resource
        # so we can verify that a forbidden DELETE did not
        # actually change the resource.
        if state_path.startswith("/api/admin/users/"):
            user_id = state_path.rsplit("/", 1)[-1]
            state_path = f"/api/users/{user_id}"

        response = requests.get(
            f"{BASE_URL}{state_path}",
            headers={
                "Authorization": f"Bearer {token}"
            },
            timeout=REQUEST_TIMEOUT,
        )

        try:
            return response.json()
        except ValueError:
            return response.text

    except requests.RequestException:
        return None


# ============================================================
# REQUEST ENDPOINT
# ============================================================

def request_endpoint(
    method,
    path,
    token=None,
    invalid_token=False,
    role=None
):

    headers = {}

    if invalid_token:

        headers["Authorization"] = (
            f"Bearer {get_invalid_token()}"
        )

    elif token:

        headers["Authorization"] = (
            f"Bearer {token}"
        )

    data = request_data(
        method,
        path,
        role=role
    )

    try:

        response = requests.request(
            method,
            f"{BASE_URL}{path}",
            headers=headers,
            json=data,
            timeout=REQUEST_TIMEOUT,
        )

        try:
            response_body = response.json()
        except ValueError:
            response_body = response.text

        return {
            "status": response.status_code,
            "body": response_body,
            "error": None,
        }

    except requests.Timeout:

        return {
            "status": 0,
            "error": "Request timeout",
        }

    except requests.ConnectionError:

        return {
            "status": 0,
            "error": "Connection error",
        }

    except requests.RequestException as error:

        return {
            "status": 0,
            "error": str(error),
        }

# ============================================================
# EXPECTED STATUS
# ============================================================

def expected_status(
    access,
    authenticated=True,
    method=None,
    path=None
):

    if not authenticated:

        return 401

    if access == "deny":

        return 403

    # Successful resource creation
    if (
        access in {"allow", "any"}
        and method == "POST"
        and path == "/api/users"
    ):

        return 201

    return 200

# ============================================================
# CLASSIFY TEST
# ============================================================

def classify_test(
    role,
    method,
    path,
    access,
    category=None
):

    if category:

        return category

    if not role:

        return "Unknown"

    if "/admin/" in path:

        return "Vertical Authorization"

    if (
        "{id}" in path
        or "/users/" in path
        or "/orders/" in path
    ):

        return "Horizontal Authorization / IDOR"

    if path == "/api/login":

        return "Authentication"

    return "Authorization"

# ============================================================
# BUILD MATRIX TESTS
# ============================================================

def build_tests():

    role_matrix = load_role_matrix()

    tests = []

    for role, endpoints in role_matrix["roles"].items():

        for endpoint, rule in endpoints.items():

            parts = endpoint.split(" ", 1)

            if len(parts) != 2:
                continue

            method, path = parts

            access = rule.get(
                "access",
                "allow"
            )

            # ------------------------------------------------
            # Basic resource replacement
            # ------------------------------------------------

            if "{id}" in path:

                if "/orders/" in path:

                    path = path.replace(
                        "{id}",
                        RESOURCE_IDS["own_order"]
                    )

                else:

                    path = path.replace(
                        "{id}",
                        RESOURCE_IDS["own_user"]
                    )

            tests.append(
                {
                    "role": role,
                    "method": method,
                    "path": path,
                    "access": access,
                    "category": classify_test(
                        role,
                        method,
                        path,
                        access
                    ),
                }
            )

    return tests

# ============================================================
# BUILD ADDITIONAL SECURITY TESTS
# ============================================================

def build_security_tests():

    tests = []

    # ========================================================
    # TARGET 1 / TARGET 2
    # ========================================================

    protected_endpoints = [

        (
            "GET",
            "/api/me",
            "Authentication"
        ),

        (
            "GET",
            "/api/admin/users",
            "Authentication"
        ),

        (
            "GET",
            "/api/admin/stats",
            "Authentication"
        ),

        (
            "GET",
            "/api/users/2",
            "Authentication"
        ),

        (
            "GET",
            "/api/orders/101",
            "Authentication"
        ),
    ]

    for method, path, category in protected_endpoints:

        tests.append(
            {
                "role": "guest",
                "method": method,
                "path": path,
                "access": "unauthenticated",
                "category": category,
                "authentication": False,
                "invalid_token": False,
                "validation": (
                    "admin_stats_protection"
                    if path == "/api/admin/stats"
                    else None
                ),
            }
        )

    # --------------------------------------------------------
    # Invalid JWT - Target 1 / Target 2
    # --------------------------------------------------------

    invalid_token_endpoints = [

        ("GET", "/api/me"),

        ("GET", "/api/admin/users"),

        ("GET", "/api/admin/stats"),
    ]

    for method, path in invalid_token_endpoints:

        tests.append(
            {
                "role": "user",
                "method": method,
                "path": path,
                "access": "invalid_token",
                "category": "JWT Validation",
                "authentication": False,
                "invalid_token": True,
            }
        )

    # --------------------------------------------------------
    # IDOR - Target 1 / Target 2
    # --------------------------------------------------------

    tests.extend(
        [

            {
                "role": "user",
                "method": "GET",
                "path": (
                    f"/api/users/"
                    f"{RESOURCE_IDS['other_user']}"
                ),
                "access": "deny",
                "category": "Horizontal Authorization / IDOR",
                "authentication": True,
                "invalid_token": False,
                "idor": True,
                "validation": "forbidden_read",
            },

            {
                "role": "user",
                "method": "PATCH",
                "path": (
                    f"/api/users/"
                    f"{RESOURCE_IDS['other_user']}"
                ),
                "access": "deny",
                "category": "Horizontal Authorization / IDOR",
                "authentication": True,
                "invalid_token": False,
                "idor": True,
                "validation": "forbidden_modify",
            },

            {
                "role": "user",
                "method": "GET",
                "path": (
                    f"/api/orders/"
                    f"{RESOURCE_IDS['other_order']}"
                ),
                "access": "deny",
                "category": "Horizontal Authorization / IDOR",
                "authentication": True,
                "invalid_token": False,
                "idor": True,
                "validation": "forbidden_read",
            },
        ]
    )

    return tests




# ============================================================
# COMBINE TESTS
# ============================================================

def generate_all_tests():

    tests = build_tests()

    security_tests = build_security_tests()

    return tests + security_tests



def resolve_path_parameters(path, test):
    """
    Replace OpenAPI path parameters such as {id} with test values.
    """

    if "{id}" in path:

        if test.get("idor"):
            return path.replace(
                "{id}",
                str(RESOURCE_IDS["other_user"])
            )

        return path.replace(
            "{id}",
            str(RESOURCE_IDS["own_user"])
        )

    return path


# ============================================================
# TEST EXECUTION
# ============================================================

def execute_test(
    test,
    tokens
):

    role = test["role"]

    authentication = test.get(
        "authentication",
        True
    )

    invalid_token = test.get(
        "invalid_token",
        False
    )
    access = test["access"]

    if access == "unauthenticated":

        expected = 401
        token = None

    elif access == "invalid_token":

        expected = 401
        token = None

    else:

        expected = expected_status(
            access,
            authentication,
            method=test["method"],
            path=test["path"]
        )

        token = tokens.get(role)

        # An authenticated test cannot be evaluated when the
        # corresponding role failed to authenticate.
        if (
            role != "guest"
            and authentication
            and not invalid_token
            and not token
        ):
            return {
                "id": test.get("id", ""),
                "role": role,
                "method": test["method"],
                "path": test["path"],
                "access": access,
                "category": test.get(
                    "category",
                    "Authorization"
                ),
                "expected": expected,
                "actual": None,
                "passed": None,
                "error": (
                    f"{role} authentication failed; "
                    "authenticated authorization test "
                    "cannot be evaluated"
                ),
                "idor": test.get("idor", False),
                "status": "SKIP",
            }

    request_path = resolve_path_parameters(
        test["path"],
        test
    )

    # --------------------------------------------------------
    # RESOURCE STATE BEFORE REQUEST
    # --------------------------------------------------------

    state_before = None
    state_after = None

    modifying_methods = {
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    }

    is_modifying_request = (
        test["method"].upper()
        in modifying_methods
    )

    if is_modifying_request:

        admin_token = tokens.get("admin")

        if admin_token:

            state_before = get_resource_state(
                request_path,
                admin_token
            )

    response = request_endpoint(
        test["method"],
        request_path,
        token=token,
        invalid_token=invalid_token,
        role=role
    )

    actual = response["status"]
    body = response.get("body")
    validation = test.get("validation")
    validation_error = None

    # --------------------------------------------------------
    # RESPONSE CONTENT VALIDATION
    # --------------------------------------------------------

    if actual == expected and validation == "admin_stats_protection":

        body_text = str(body)

        leaked_fields = [
            "total_users",
            "total_orders",
            "total_products",
        ]

        leaked = [
            field
            for field in leaked_fields
            if field in body_text
        ]

        if leaked:
            validation_error = (
                "Admin statistics data exposed in "
                f"forbidden response: {', '.join(leaked)}"
            )

    # --------------------------------------------------------
    # FORBIDDEN READ VALIDATION
    # --------------------------------------------------------

    elif actual == expected and validation == "forbidden_read":

        body_text = str(body)

        if actual == 403:
            sensitive_fields = [
                "username",
                "email",
                "total_users",
                "total_orders",
                "total_products",
            ]

            leaked = [
                field
                for field in sensitive_fields
                if field in body_text
            ]

            if leaked:
                validation_error = (
                    "Forbidden resource data exposed: "
                    f"{', '.join(leaked)}"
                )

    # --------------------------------------------------------
    # RESOURCE STATE AFTER REQUEST
    # --------------------------------------------------------

    if is_modifying_request:

        admin_token = tokens.get("admin")

        if admin_token:

            state_after = get_resource_state(
                request_path,
                admin_token
            )

    # --------------------------------------------------------
    # FORBIDDEN MODIFY VALIDATION
    # --------------------------------------------------------

    if validation == "forbidden_modify":

        if actual != 403:

            validation_error = (
                "Forbidden modification returned unexpected "
                f"HTTP status {actual}; expected 403"
            )

        elif admin_token is None:

            validation_error = (
                "Unable to validate resource state: "
                "admin authentication token unavailable"
            )

        elif state_before != state_after:

            validation_error = (
                "Forbidden modification changed "
                "the protected resource"
            )

    passed = (
        actual == expected
        and validation_error is None
    )

    final_error = (
        validation_error
        if validation_error
        else response["error"]
    )

    # --------------------------------------------------------
    # SHOW RESOURCE STATE VALIDATION
    # --------------------------------------------------------

    if is_modifying_request:

        print(
            f"STATE CHECK | {test.get('id', '')} | "
            f"before={state_before} | "
            f"after={state_after}"
        )

    else:

        print(
            f"STATE CHECK | {test.get('id', '')} | "
            "read-only request; no state mutation expected"
        )

    return {
        "id": test.get(
            "id",
            ""
        ),
        "role": role,
        "method": test["method"],
        "path": test["path"],
        "access": access,
        "category": test.get(
            "category",
            "Authorization"
        ),
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "error": final_error,
        "state_before": state_before,
        "state_after": state_after,
        "idor": test.get(
            "idor",
            False
        ),
    }

# ============================================================
# ADD TEST IDs
# ============================================================

def assign_test_ids(tests):

    for index, test in enumerate(
        tests,
        start=1
    ):

        test["id"] = (
            f"AC-{index:03d}"
        )

    return tests



def load_openapi_tests(openapi_file):
    """
    Load security tests generated from an OpenAPI specification
    and convert them to the format expected by execute_test().
    """

    try:
        # Package execution:
        # python3 -m harness
        from .openapi_test_generator import generate_security_tests
    except ImportError:
        # Direct script execution:
        # python3 harness/test_runner.py
        from openapi_test_generator import generate_security_tests

    test_data = generate_security_tests(openapi_file)

    tests = []

    for test in test_data["tests"]:

        category = test.get(
            "category",
            "Authorization"
        )

        access = test.get(
            "access",
            "allow"
        )

        tests.append({
            "id": test.get("id", ""),
            "role": test.get("role", "user"),
            "category": category,
            "method": test["method"],
            "path": test["path"],
            "access": access,

            "authentication": (
                category == "Authentication"
                or test.get("role") != "guest"
            ),

            "invalid_token": False,

            "idor": (
                "IDOR" in category
                or "Horizontal" in category
            ),

            "operation_id": test.get(
                "operation_id"
            ),

            "summary": test.get(
                "summary",
                ""
            ),
        })

    return tests


# ============================================================
# HTML REPORT
# ============================================================

def generate_html_report(
    results,
    passed,
    failed,
    generated_time
):

    os.makedirs(
        REPORT_DIR,
        exist_ok=True
    )

    total = len(results)

    if failed == 0:

        overall_text = "✓ PASS"
        overall_class = "success"

    else:

        overall_text = "✗ FAIL"
        overall_class = "danger"

    category_counts = {}

    for result in results:

        category = result["category"]

        if category not in category_counts:

            category_counts[category] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
            }

        category_counts[category]["total"] += 1

        if result.get("status") == "SKIP":

            result_text = "SKIP"

        elif result["passed"]:

            category_counts[category]["passed"] += 1

        else:

            category_counts[category]["failed"] += 1

    rows = ""

    for result in results:

        if result["passed"]:

            status_text = "✓ PASS"
            status_class = "pass"

        else:

            status_text = "✗ FAIL"
            status_class = "fail"

        error_text = (
            result["error"]
            if result["error"]
            else ""
        )

        rows += f"""
        <tr>

            <td>
                {escape(result["id"])}
            </td>

            <td>
                <span class="role {escape(result["role"])}">
                    {escape(result["role"].upper())}
                </span>
            </td>

            <td>
                <span class="category">
                    {escape(result["category"])}
                </span>
            </td>

            <td>
                <span class="method">
                    {escape(result["method"])}
                </span>
            </td>

            <td class="endpoint">
                {escape(result["path"])}
            </td>

            <td>
                <span class="rule">
                    {escape(result["access"])}
                </span>
            </td>

            <td class="code">
                {result["expected"]}
            </td>

            <td class="code">
                {result["actual"]}
            </td>

            <td>
                <span class="result {status_class}">
                    {status_text}
                </span>
            </td>

            <td>
                {escape(error_text)}
            </td>

            <td>
                {escape(
                    "BEFORE: " + str(result.get("state_before"))
                    + " | AFTER: " + str(result.get("state_after"))
                ) if result.get("state_before") is not None else ""}
            </td>

        </tr>
        """

    category_rows = ""

    for category, values in category_counts.items():

        category_rows += f"""
        <tr>
            <td>{escape(category)}</td>
            <td>{values["total"]}</td>
            <td>{values["passed"]}</td>
            <td>{values["failed"]}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>
Access Control Security Report
</title>

<style>

* {{
    box-sizing: border-box;
}}

body {{

    margin: 0;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background:
        linear-gradient(
            135deg,
            #eef2ff,
            #f8fafc
        );

    color: {DARK};
}}

.container {{

    width: 94%;

    max-width: 1500px;

    margin: 35px auto;
}}

.header {{

    background:
        linear-gradient(
            135deg,
            {NAVY},
            {BLUE}
        );

    color: white;

    padding: 40px;

    border-radius: 22px;

    box-shadow:
        0 18px 40px
        rgba(37, 99, 235, 0.25);

    margin-bottom: 25px;
}}

.header h1 {{

    margin: 0;

    font-size: 34px;

    letter-spacing: 1px;
}}

.header h2 {{

    margin: 10px 0;

    font-size: 20px;

    font-weight: normal;
}}

.header p {{

    line-height: 1.6;
}}

.target-badge {{

    display: inline-block;

    padding: 8px 14px;

    background:
        rgba(255,255,255,0.15);

    border-radius: 20px;
}}

.summary {{

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 18px;

    margin-bottom: 25px;
}}

.card {{

    background: white;

    padding: 25px;

    border-radius: 17px;

    box-shadow:
        0 8px 25px
        rgba(15, 23, 42, 0.08);

    text-align: center;

    border-top: 5px solid {BLUE};
}}

.card.passed {{
    border-top-color: {GREEN};
}}

.card.failed {{
    border-top-color: {RED};
}}

.card.overall {{
    border-top-color:
        {GREEN if failed == 0 else RED};
}}

.card h3 {{

    font-size: 12px;

    color: {SLATE};
}}

.number {{

    font-size: 36px;

    font-weight: bold;
}}

.blue {{
    color: {BLUE};
}}

.green {{
    color: {GREEN};
}}

.red {{
    color: {RED};
}}

.section {{

    background: white;

    border-radius: 17px;

    padding: 25px;

    margin-bottom: 25px;

    box-shadow:
        0 8px 25px
        rgba(15, 23, 42, 0.08);
}}

.section-title {{

    font-size: 21px;

    font-weight: bold;

    color: {NAVY};

    margin-bottom: 20px;
}}

table {{

    width: 100%;

    border-collapse: collapse;

    font-size: 13px;
}}

thead {{

    background:
        linear-gradient(
            90deg,
            {NAVY},
            {BLUE}
        );

    color: white;
}}

th {{

    padding: 12px;

    text-align: left;
}}

td {{

    padding: 11px;

    border-bottom:
        1px solid #e2e8f0;
}}

tbody tr:hover {{

    background: {LIGHT_BLUE};
}}

.endpoint {{

    font-family:
        "Courier New",
        monospace;

    color: #1e3a8a;
}}

.code {{

    text-align: center;

    font-weight: bold;
}}

.role,
.category,
.method,
.rule,
.result {{

    display: inline-block;

    padding: 5px 9px;

    border-radius: 8px;

    font-size: 10px;

    font-weight: bold;
}}

.role.admin {{

    background: #fee2e2;

    color: #991b1b;
}}

.role.user {{

    background: #dbeafe;

    color: #1d4ed8;
}}

.role.guest {{

    background: #f1f5f9;

    color: #475569;
}}

.category {{

    background: #ede9fe;

    color: #6d28d9;
}}

.method {{

    background: #e0e7ff;

    color: #3730a3;
}}

.rule {{

    background: #f1f5f9;

    color: #334155;
}}

.result.pass {{

    background: {LIGHT_GREEN};

    color: #166534;
}}

.result.fail {{

    background: {LIGHT_RED};

    color: #991b1b;
}}

.conclusion {{

    padding: 25px;

    border-radius: 15px;

    background:
        {LIGHT_GREEN if failed == 0 else LIGHT_RED};

    border:
        1px solid
        {GREEN if failed == 0 else RED};

    color:
        {GREEN_DARK if failed == 0 else RED_DARK};
}}

.footer {{

    text-align: center;

    color: {SLATE};

    font-size: 13px;

    padding: 20px;
}}

@media (max-width: 1000px) {{

    .summary {{

        grid-template-columns:
            repeat(2, 1fr);
    }}

}}

@media (max-width: 600px) {{

    .summary {{

        grid-template-columns:
            1fr;
    }}

}}

</style>

</head>

<body>

<div class="container">

<div class="header">

<h1>
🔐 AUTOMATED ACCESS CONTROL
</h1>

<h2>
SECURITY TEST REPORT
</h2>

<p>
Role-Based Authorization
• JWT Authentication
• Vertical Authorization
• Horizontal Authorization / IDOR
• Invalid JWT Testing
</p>

<div class="target-badge">

Testing:
{escape(TARGET_NAME)}

&nbsp; • &nbsp;

{escape(BASE_URL)}

</div>

<p>
<strong>Generated:</strong>
{escape(generated_time)}
</p>

</div>


<div class="summary">

<div class="card">

<h3>TOTAL TESTS</h3>

<div class="number blue">
{total}
</div>

</div>

<div class="card passed">

<h3>PASSED</h3>

<div class="number green">
{passed}
</div>

</div>

<div class="card failed">

<h3>FAILED</h3>

<div class="number red">
{failed}
</div>

</div>

<div class="card overall">

<h3>OVERALL STATUS</h3>

<div class="number
{'green' if failed == 0 else 'red'}">

{overall_text}

</div>

</div>

</div>


<div class="section">

<div class="section-title">
SECURITY TEST CATEGORIES
</div>

<table>

<thead>

<tr>

<th>Category</th>
<th>Total</th>
<th>Passed</th>
<th>Failed</th>

</tr>

</thead>

<tbody>

{category_rows}

</tbody>

</table>

</div>


<div class="section">

<div class="section-title">
DETAILED TEST RESULTS
</div>

<div style="overflow-x:auto">

<table>

<thead>

<tr>

<th>ID</th>
<th>ROLE</th>
<th>CATEGORY</th>
<th>METHOD</th>
<th>ENDPOINT</th>
<th>RULE</th>
<th>EXPECTED</th>
<th>ACTUAL</th>
<th>RESULT</th>
<th>ERROR</th>
            <th>STATE CHECK</th>

</tr>

</thead>

<tbody>

{rows}

</tbody>

</table>

</div>

</div>


<div class="conclusion">

<h2>

{
'✓ Security Test Passed'
if failed == 0
else
'✗ Security Test Failed'
}

</h2>

<p>

<strong>{total}</strong>
automated security tests were executed.

<strong>{passed}</strong>
tests passed and

<strong>{failed}</strong>
tests failed.

</p>

<p>

The harness tested authentication,
vertical authorization,
horizontal authorization / IDOR,
JWT validation, and the configured
role-permission matrix.

</p>

</div>


<div class="footer">

Automated Access Control Test Harness

<br>

{escape(TARGET_NAME)}
•
Role-Based Access Control
•
JWT
•
IDOR Testing

</div>

</div>

</body>

</html>
"""

    with open(
        HTML_REPORT,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(html)

    print()
    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)
    print(TERM_BLUE + TERM_BOLD + "HTML REPORT CREATED" + TERM_RESET)
    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)

    print(
        f"Report: {HTML_REPORT}"
    )

    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)


# ============================================================
# PDF HELPERS
# ============================================================

def pdf_color(hex_color):

    return colors.HexColor(
        hex_color
    )


def create_badge(
    text,
    background,
    foreground,
    font_size=6.5
):

    style = ParagraphStyle(
        "BadgeStyle",
        fontName="Helvetica-Bold",
        fontSize=font_size,
        leading=font_size + 2,
        textColor=pdf_color(foreground),
        alignment=TA_CENTER,
    )

    badge = Table(
        [[
            Paragraph(
                escape(str(text)),
                style
            )
        ]],
        colWidths=[20 * mm]
    )

    badge.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    pdf_color(background)
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    pdf_color(background)
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
            ]
        )
    )

    return badge


def role_badge(role):

    role = role.lower()

    if role == "admin":

        return create_badge(
            "ADMIN",
            "#FEE2E2",
            "#991B1B",
            6.2
        )

    if role == "user":

        return create_badge(
            "USER",
            "#DBEAFE",
            "#1D4ED8",
            6.2
        )

    return create_badge(
        "GUEST",
        "#F1F5F9",
        "#475569",
        6.2
    )


def method_badge(method):

    return create_badge(
        method,
        "#E0E7FF",
        "#3730A3",
        6.2
    )


def rule_badge(rule):

    if rule in {
        "deny",
        "unauthenticated",
        "invalid_token"
    }:

        return create_badge(
            rule,
            "#FEE2E2",
            "#991B1B",
            6.2
        )

    if rule == "own":

        return create_badge(
            "own",
            "#EDE9FE",
            "#6D28D9",
            6.2
        )

    if rule == "any":

        return create_badge(
            "any",
            "#FFEDD5",
            "#C2410C",
            6.2
        )

    return create_badge(
        "allow",
        "#DCFCE7",
        "#166534",
        6.2
    )


def result_badge(passed):

    if passed:

        return create_badge(
            "✓ PASS",
            "#DCFCE7",
            "#166534",
            6.2
        )

    return create_badge(
        "✗ FAIL",
        "#FEE2E2",
        "#991B1B",
        6.2
    )


# ============================================================
# PDF REPORT
# ============================================================

def generate_pdf_report(
    results,
    passed,
    failed,
    generated_time
):

    os.makedirs(
        REPORT_DIR,
        exist_ok=True
    )

    total = len(results)

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "PDFTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=23,
        textColor=colors.white,
        alignment=TA_LEFT,
    )

    subtitle_style = ParagraphStyle(
        "PDFSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#DBEAFE"),
    )

    section_style = ParagraphStyle(
        "PDFSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=pdf_color(NAVY),
        spaceBefore=5,
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "PDFBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=pdf_color(DARK),
    )

    endpoint_style = ParagraphStyle(
        "PDFEndpoint",
        parent=styles["BodyText"],
        fontName="Courier",
        fontSize=5.7,
        leading=7,
        textColor=colors.HexColor("#1E3A8A"),
    )

    table_header_style = ParagraphStyle(
        "PDFTableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=5.5,
        leading=6.5,
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    table_text_style = ParagraphStyle(
        "PDFTableText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=5.5,
        leading=6.5,
        textColor=pdf_color(DARK),
        alignment=TA_CENTER,
    )

    conclusion_style = ParagraphStyle(
        "PDFConclusion",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=pdf_color(
            GREEN_DARK
            if failed == 0
            else RED_DARK
        ),
    )

    small_style = ParagraphStyle(
        "PDFSmall",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=8,
        textColor=pdf_color(SLATE),
    )

    doc = SimpleDocTemplate(
        PDF_REPORT,
        pagesize=A4,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=18 * mm,
    )

    story = []

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    header = Table(
        [
            [
                Paragraph(
                    "AUTOMATED ACCESS CONTROL",
                    title_style
                )
            ],
            [
                Paragraph(
                    "SECURITY TEST REPORT",
                    title_style
                )
            ],
            [
                Paragraph(
                    f"Target: <b>{escape(TARGET_NAME)}</b>"
                    f" &nbsp;•&nbsp; "
                    f"{escape(BASE_URL)}",
                    subtitle_style
                )
            ],
            [
                Paragraph(
                    "RBAC • JWT • Vertical Authorization "
                    "• Horizontal Authorization / IDOR "
                    "• JWT Validation",
                    subtitle_style
                )
            ],
            [
                Paragraph(
                    f"<b>Generated:</b> "
                    f"{escape(generated_time)}",
                    subtitle_style
                )
            ],
        ],
        colWidths=[190 * mm],
    )

    header.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    pdf_color(NAVY)
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    12
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    12
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    10
                ),
                (
                    "BOTTOMPADDING",
                    (0, 4),
                    (-1, 4),
                    10
                ),
            ]
        )
    )

    story.append(header)

    story.append(
        Spacer(1, 8)
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary_header_style = ParagraphStyle(
        "SummaryHeader",
        fontName="Helvetica-Bold",
        fontSize=6,
        leading=7,
        textColor=pdf_color(SLATE),
        alignment=TA_CENTER,
    )

    summary_number_style = ParagraphStyle(
        "SummaryNumber",
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=19,
        alignment=TA_CENTER,
    )

    summary = Table(
        [
            [
                Paragraph(
                    "TOTAL",
                    summary_header_style
                ),
                Paragraph(
                    "PASSED",
                    summary_header_style
                ),
                Paragraph(
                    "FAILED",
                    summary_header_style
                ),
                Paragraph(
                    "STATUS",
                    summary_header_style
                ),
            ],
            [
                Paragraph(
                    str(total),
                    ParagraphStyle(
                        "BlueNumber",
                        parent=summary_number_style,
                        textColor=pdf_color(BLUE),
                    )
                ),
                Paragraph(
                    str(passed),
                    ParagraphStyle(
                        "GreenNumber",
                        parent=summary_number_style,
                        textColor=pdf_color(GREEN),
                    )
                ),
                Paragraph(
                    str(failed),
                    ParagraphStyle(
                        "RedNumber",
                        parent=summary_number_style,
                        textColor=pdf_color(RED),
                    )
                ),
                Paragraph(
                    "✓ PASS"
                    if failed == 0
                    else "✗ FAIL",
                    ParagraphStyle(
                        "OverallNumber",
                        parent=summary_number_style,
                        textColor=pdf_color(
                            GREEN
                            if failed == 0
                            else RED
                        ),
                    )
                ),
            ],
        ],
        colWidths=[
            47.5 * mm,
            47.5 * mm,
            47.5 * mm,
            47.5 * mm,
        ],
    )

    summary.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    pdf_color(LIGHT_BLUE)
                ),
                (
                    "BACKGROUND",
                    (1, 1),
                    (1, 1),
                    pdf_color(LIGHT_GREEN)
                ),
                (
                    "BACKGROUND",
                    (2, 1),
                    (2, 1),
                    pdf_color(LIGHT_RED)
                ),
                (
                    "BACKGROUND",
                    (3, 1),
                    (3, 1),
                    pdf_color(
                        LIGHT_GREEN
                        if failed == 0
                        else LIGHT_RED
                    )
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    pdf_color(BORDER)
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    pdf_color(BORDER)
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
            ]
        )
    )

    story.append(summary)

    story.append(
        Spacer(1, 10)
    )

    # --------------------------------------------------------
    # SECURITY TEST CATEGORIES
    # --------------------------------------------------------

    category_stats = {}

    for result in results:

        category = result.get(
            "category",
            "Authorization"
        )

        if category not in category_stats:
            category_stats[category] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
            }

        category_stats[category]["total"] += 1

        if result.get("passed"):
            category_stats[category]["passed"] += 1
        else:
            category_stats[category]["failed"] += 1

    story.append(
        Paragraph(
            "SECURITY TEST CATEGORIES",
            section_style
        )
    )

    category_table_data = [
        [
            Paragraph("CATEGORY", table_header_style),
            Paragraph("TOTAL", table_header_style),
            Paragraph("PASSED", table_header_style),
            Paragraph("FAILED", table_header_style),
        ]
    ]

    category_order = [
        "Authentication",
        "Authorization",
        "Horizontal Authorization / IDOR",
    ]

    for category in category_order:

        if category not in category_stats:
            continue

        stats = category_stats[category]

        category_table_data.append(
            [
                Paragraph(
                    escape(category),
                    table_text_style
                ),
                Paragraph(
                    str(stats["total"]),
                    table_text_style
                ),
                Paragraph(
                    str(stats["passed"]),
                    table_text_style
                ),
                Paragraph(
                    str(stats["failed"]),
                    table_text_style
                ),
            ]
        )

    category_table = Table(
        category_table_data,
        colWidths=[
            280,
            70,
            70,
            70,
        ],
        repeatRows=1,
    )

    category_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    pdf_color(NAVY)
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    pdf_color(WHITE)
                ),
                (
                    "BACKGROUND",
                    (1, 1),
                    (1, -1),
                    pdf_color(LIGHT_BLUE)
                ),
                (
                    "BACKGROUND",
                    (2, 1),
                    (2, -1),
                    pdf_color(LIGHT_GREEN)
                ),
                (
                    "BACKGROUND",
                    (3, 1),
                    (3, -1),
                    pdf_color(LIGHT_RED)
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    pdf_color(BORDER)
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    pdf_color(BORDER)
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
            ]
        )
    )

    story.append(category_table)

    story.append(
        Spacer(1, 14)
    )

    # --------------------------------------------------------
    # DETAILED RESULTS
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "DETAILED SECURITY TEST RESULTS",
            section_style
        )
    )

    table_data = [
        [
            Paragraph("ID", table_header_style),
            Paragraph("ROLE", table_header_style),
            Paragraph("CATEGORY", table_header_style),
            Paragraph("METHOD", table_header_style),
            Paragraph("ENDPOINT", table_header_style),
            Paragraph("RULE", table_header_style),
            Paragraph("EXP.", table_header_style),
            Paragraph("ACT.", table_header_style),
            Paragraph("RESULT", table_header_style),
            Paragraph("ERROR", table_header_style),
            Paragraph("STATE CHECK", table_header_style),
        ]
    ]

    for result in results:

        error_text = result.get("error") or ""

        state_before = result.get("state_before")
        state_after = result.get("state_after")

        if state_before is not None and state_after is not None:
            if state_before == state_after:
                state_check = "UNCHANGED"
            else:
                state_check = "CHANGED"
        else:
            state_check = ""

        table_data.append(
            [
                Paragraph(
                    escape(result["id"]),
                    table_text_style
                ),

                role_badge(
                    result["role"]
                ),

                Paragraph(
                    escape(result["category"]),
                    table_text_style
                ),

                method_badge(
                    result["method"]
                ),

                Paragraph(
                    escape(result["path"]),
                    endpoint_style
                ),

                rule_badge(
                    result["access"]
                ),

                Paragraph(
                    str(result["expected"]),
                    table_text_style
                ),

                Paragraph(
                    str(result["actual"]),
                    table_text_style
                ),

                result_badge(
                    result["passed"]
                ),

                Paragraph(
                    escape(error_text),
                    table_text_style
                ),

                Paragraph(
                    escape(state_check),
                    table_text_style
                ),
            ]
        )

    result_table = Table(
        table_data,
        colWidths=[
            12 * mm,
            17 * mm,
            28 * mm,
            14 * mm,
            37 * mm,
            17 * mm,
            9 * mm,
            9 * mm,
            18 * mm,
            29 * mm,
        ],
        repeatRows=1,
        hAlign="CENTER",
    )

    result_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    pdf_color(NAVY)
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    pdf_color(BORDER)
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        pdf_color(LIGHTER_BLUE)
                    ]
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    2
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3
                ),
            ]
        )
    )

    story.append(
        result_table
    )

    story.append(
        Spacer(1, 10)
    )

    # --------------------------------------------------------
    # CONCLUSION
    # --------------------------------------------------------

    if failed == 0:

        conclusion_title = (
            "<font color='#166534'>"
            "✓ OVERALL SECURITY RESULT: PASS"
            "</font>"
        )

        conclusion_text = (
            f"<b>{total}</b> automated security tests "
            f"were executed. "
            f"<b>{passed}</b> passed and "
            f"<b>{failed}</b> failed."
        )

        conclusion_bg = LIGHT_GREEN
        conclusion_border = GREEN

    else:

        conclusion_title = (
            "<font color='#991B1B'>"
            "✗ OVERALL SECURITY RESULT: FAIL"
            "</font>"
        )

        conclusion_text = (
            f"<b>{total}</b> automated security tests "
            f"were executed. "
            f"<b>{passed}</b> passed and "
            f"<b>{failed}</b> failed.<br/><br/>"
            "Review the failed authorization, "
            "authentication, JWT, or IDOR tests."
        )

        conclusion_bg = LIGHT_RED
        conclusion_border = RED

    conclusion_title_style = ParagraphStyle(
        "ConclusionTitle",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=pdf_color(
            GREEN_DARK
            if failed == 0
            else RED_DARK
        ),
    )

    conclusion = Table(
        [
            [
                Paragraph(
                    conclusion_title,
                    conclusion_title_style
                )
            ],
            [
                Paragraph(
                    conclusion_text,
                    conclusion_style
                )
            ],
        ],
        colWidths=[190 * mm],
    )

    conclusion.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    pdf_color(conclusion_bg)
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.9,
                    pdf_color(conclusion_border)
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    9
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    9
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),
            ]
        )
    )

    story.append(
        KeepTogether(conclusion)
    )

    story.append(
        Spacer(1, 8)
    )

    story.append(
        Paragraph(
            f"Target: {escape(TARGET_NAME)} "
            f"• URL: {escape(BASE_URL)} "
            f"• Generated: {escape(generated_time)}",
            small_style
        )
    )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    def footer(canvas, doc):

        canvas.saveState()

        canvas.setStrokeColor(
            pdf_color(BORDER)
        )

        canvas.setLineWidth(
            0.5
        )

        canvas.line(
            10 * mm,
            10 * mm,
            200 * mm,
            10 * mm
        )

        canvas.setFont(
            "Helvetica",
            6.5
        )

        canvas.setFillColor(
            pdf_color(SLATE)
        )

        canvas.drawString(
            10 * mm,
            6 * mm,
            "Automated Access Control Test Harness"
        )

        canvas.drawRightString(
            200 * mm,
            6 * mm,
            f"Page {doc.page}"
        )

        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=footer,
        onLaterPages=footer
    )

    print()
    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)
    print(TERM_BLUE + TERM_BOLD + "PDF REPORT CREATED" + TERM_RESET)
    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)

    print(
        f"Report: {PDF_REPORT}"
    )

    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)


# ============================================================
# PRINT FINDINGS
# ============================================================

def print_findings(results):

    findings = [
        result
        for result in results
        if not result["passed"]
    ]

    if not findings:

        print()
        print("No failed security tests detected.")
        return

    print()
    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)
    print("SECURITY FINDINGS")
    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)

    for result in findings:

        print()
        print(
            f"{result['id']} | "
            f"{result['category']}"
        )

        print(
            f"Role     : {result['role']}"
        )

        print(
            f"Request  : "
            f"{result['method']} "
            f"{result['path']}"
        )

        print(
            f"Expected : HTTP {result['expected']}"
        )

        print(
            f"Actual   : HTTP {result['actual']}"
        )

        if result["error"]:

            print(
                f"Error    : {result['error']}"
            )

    print()
    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)


# ============================================================
# LOGIN
# ============================================================

def login(identifier, password):

    try:

        payload = {
            "username": identifier,
            "password": password,
        }

        response = requests.post(
            f"{BASE_URL}/api/login",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        if response.status_code != 200:
            return None

        try:
            body = response.json()
        except ValueError:
            return None

        return body.get("token")

    except requests.RequestException:
        return None



# ============================================================
# COMMAND-LINE INTERFACE
# ============================================================

def parse_cli_args():
    parser = argparse.ArgumentParser(
        prog="access-control-harness",
        description=(
            "Automated access-control and authorization "
            "security test harness."
        ),
    )

    parser.add_argument(
        "--url",
        help="Target base URL, e.g. http://127.0.0.1:5002",
    )

    parser.add_argument(
        "--target",
        choices=sorted(TARGETS.keys()),
        help="Use a configured target instead of the interactive menu.",
    )

    parser.add_argument(
        "--role-matrix",
        help="Path to the role-matrix YAML file.",
    )

    parser.add_argument(
        "--openapi",
        help="Path to an OpenAPI YAML/JSON specification.",
    )

    parser.add_argument(
        "--report",
        choices=("html", "pdf", "all", "none"),
        default="all",
        help="Report formats to generate (default: all).",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=REQUEST_TIMEOUT,
        help=f"HTTP request timeout in seconds (default: {REQUEST_TIMEOUT}).",
    )

    return parser.parse_args()


# ============================================================
# RUN TESTS
# ============================================================

def run_tests():
    global RESOURCE_IDS
    global ACTIVE_USERS

    global BASE_URL
    global TARGET_NAME
    global ROLE_MATRIX
    global REQUEST_TIMEOUT
    global HTML_REPORT
    global PDF_REPORT

    args = parse_cli_args()

    # --------------------------------------------------------
    # TARGET SELECTION
    # --------------------------------------------------------

    if args.url:
        BASE_URL = args.url.rstrip("/")

        # Prefer an explicitly supplied target name.
        if args.target:
            TARGET_NAME = TARGETS[args.target]["name"]

        else:
            TARGET_NAME = "Custom Target"

    elif args.target:
        target = TARGETS[args.target]

        BASE_URL = target["url"].rstrip("/")
        TARGET_NAME = target["name"]

        print()
        print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)
        print("       AUTOMATED ACCESS CONTROL TEST HARNESS")
        print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)
        print()
        print(f"Selected target : {TARGET_NAME}")
        print(f"Target URL      : {BASE_URL}")
        print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)

    else:
        # Interactive target selection.
        BASE_URL, TARGET_NAME = select_target()

    # --------------------------------------------------------
    # RUNTIME TARGET CONFIGURATION
    # --------------------------------------------------------
    # Resolve target-dependent configuration only after the
    # target has been selected. This keeps module imports safe.

    ACTIVE_USERS = USERS

    # Load resource identifiers from the target configuration.
    config_path = Path("configs/target.example.yaml")

    if config_path.exists():
        import yaml

        with config_path.open("r", encoding="utf-8") as file:
            target_config_data = yaml.safe_load(file) or {}

        configured_resources = target_config_data.get(
            "resources",
            {},
        )

        RESOURCE_IDS = {
            "own_user": str(
                configured_resources.get(
                    "user",
                    {},
                ).get("own", "")
            ),
            "other_user": str(
                configured_resources.get(
                    "user",
                    {},
                ).get("other", "")
            ),
            "own_order": str(
                configured_resources.get(
                    "order",
                    {},
                ).get("own", "")
            ),
            "other_order": str(
                configured_resources.get(
                    "order",
                    {},
                ).get("other", "")
            ),
        }

    else:
        RESOURCE_IDS = {}

    if not RESOURCE_IDS:
        print()
        print(
            "ERROR: no resource-ID configuration found."
        )
        return

    # --------------------------------------------------------
    # RUNTIME PATHS
    # --------------------------------------------------------

    safe_name = (
        TARGET_NAME.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("\\", "-")
    )

    SAFE_TARGET_NAME = safe_name

    REPORT_DIR = os.path.join(
        BASE_DIR,
        "reports"
    )

    os.makedirs(
        REPORT_DIR,
        exist_ok=True
    )

    HTML_REPORT = os.path.join(
        REPORT_DIR,
        f"{SAFE_TARGET_NAME}_access_control_report.html"
    )

    PDF_REPORT = os.path.join(
        REPORT_DIR,
        f"{SAFE_TARGET_NAME}_access_control_report.pdf"
    )

    if args.role_matrix:
        role_matrix_path = os.path.abspath(args.role_matrix)

        if not os.path.isfile(role_matrix_path):
            print()
            print(f"ERROR: role matrix not found: {role_matrix_path}")
            return

        ROLE_MATRIX = role_matrix_path

    # Select the role matrix automatically for configured targets.
    if not args.role_matrix:
        ROLE_MATRIX = ROLE_MATRICES.get(
            TARGET_NAME,
            ROLE_MATRIX
        )

    REQUEST_TIMEOUT = args.timeout

    safe_name = (
        TARGET_NAME.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace(":", "")
    )

    HTML_REPORT = os.path.join(
        REPORT_DIR,
        f"{safe_name}_access_control_report.html",
    )

    PDF_REPORT = os.path.join(
        REPORT_DIR,
        f"{safe_name}_access_control_report.pdf",
    )

    print()
    print("Loading role matrix...")
    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)

    # --------------------------------------------------------
    # OPENAPI MODE
    # --------------------------------------------------------

    openapi_file = args.openapi

    if openapi_file:

        openapi_file = os.path.abspath(openapi_file)

        if not os.path.isfile(openapi_file):
            print()
            print(f"ERROR: OpenAPI specification not found: {openapi_file}")
            return

        print()
        print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)
        print("OPENAPI SECURITY TEST MODE")
        print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)
        print(f"Specification : {openapi_file}")

        try:

            tests = load_openapi_tests(
                openapi_file
            )

        except Exception as error:

            print(
                f"OpenAPI parsing failed: {error}"
            )

            return

        print(
            f"Generated OpenAPI tests: {len(tests)}"
        )

        print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)

        for test in tests:

            print(
                f"{test['id']:7} | "
                f"{test['role']:5} | "
                f"{test['category']:35} | "
                f"{test['method']:6} | "
                f"{test['path']}"
            )

    else:

        # ----------------------------------------------------
        # NORMAL ROLE-MATRIX MODE
        # ----------------------------------------------------

        tests = generate_all_tests()

        tests = assign_test_ids(
            tests
        )

        print(
            f"Generated tests: {len(tests)}"
        )

        print()
        print("Test categories:")
        print(
            "  • Role-based authorization"
        )
        print(
            "  • Vertical authorization"
        )
        print(
            "  • Horizontal authorization / IDOR"
        )
        print(
            "  • Authentication"
        )
        print(
            "  • Invalid JWT"
        )

    # --------------------------------------------------------
    # CHECK SERVER
    # --------------------------------------------------------

    if not check_target():

        return

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    terminal_banner("LOGGING IN TEST USERS")

    tokens = {}

    for role, credentials in ACTIVE_USERS.items():

        token = login(
            credentials["username"],
            credentials["password"]
        )

        tokens[role] = token

        if token:

            print(
                f"{role}: login successful"
            )

        else:

            print(
                f"{role}: login failed"
            )

    # --------------------------------------------------------
    # TESTS
    # --------------------------------------------------------

    terminal_banner(
        f"RUNNING SECURITY TESTS AGAINST {TARGET_NAME}"
    )
    passed = 0
    failed = 0

    results = []

    for test in tests:

        result = execute_test(
            test,
            tokens
        )

        if result.get("status") == "SKIP":

            result_text = "SKIP"

        elif result["passed"]:

            result_text = "PASS"

            passed += 1

        else:

            result_text = "FAIL"

            failed += 1

        results.append(
            result
        )

        colour = status_colour(result_text)

        print(
            f"{colour}{ANSI_BOLD}{result_text:5}{ANSI_RESET} | "
            f"{result['id']:7} | "
            f"{result['role']:5} | "
            f"{result['method']:6} | "
            f"{result['path']:35} | "
            f"expected={result['expected']} "
            f"actual={result['actual']}"
        )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)

    print(
        f"Target:  {TARGET_NAME}"
    )

    print(
        f"Passed:  {passed}"
    )

    print(
        f"Failed:  {failed}"
    )

    print(
        f"Total:   {len(results)}"
    )

    # --------------------------------------------------------
    # FINDINGS
    # --------------------------------------------------------

    print_findings(
        results
    )

    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    generated_time = datetime.now().strftime(
        "%d %B %Y, %H:%M:%S"
    )

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    if args.report in ("html", "all"):

        generate_html_report(
            results,
            passed,
            failed,
            generated_time
        )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    if args.report in ("pdf", "all"):

        generate_pdf_report(
            results,
            passed,
            failed,
            generated_time
        )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    terminal_banner("REPORT GENERATION COMPLETE")

    print(f"{ANSI_CYAN}Target : {TARGET_NAME}{ANSI_RESET}")

    print(f"{ANSI_CYAN}URL    : {BASE_URL}{ANSI_RESET}")

    if args.report in ("html", "all"):
        print(
            f"HTML   : {HTML_REPORT}"
        )

    if args.report in ("pdf", "all"):
        print(
            f"PDF    : {PDF_REPORT}"
        )

    print(TERM_BLUE + TERM_BOLD + "=" * 60 + TERM_RESET)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_tests()
