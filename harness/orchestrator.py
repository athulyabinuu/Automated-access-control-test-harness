import argparse
import json
import os
import tempfile
from pathlib import Path

# Professional terminal colours
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
WHITE = "\033[97m"


import yaml

from harness.config import (
    TargetConfig,
    TestAccount,
    REQUEST_TIMEOUT,
)
from harness.discovery import EndpointDiscovery, discover_remote_openapi
from harness.api_route_discovery import APIRouteDiscovery
from harness.authentication import AuthenticationManager
from harness.resource_discovery import ResourceDiscovery
from harness.authorization_discovery import AuthorizationDiscovery
from harness.policy_model import policy_from_discovery
from harness.test_generator import AccessControlTestGenerator
from harness.execution import AccessControlExecutionEngine
from harness.web_discovery import WebRouteDiscovery
from harness.web_test_generator import WebAccessControlTestGenerator
from harness.web_execution import WebAccessControlExecutionEngine
from harness.reporting import (
    generate_html_report,
    generate_json_report,
    generate_pdf_report,
)


def load_target_config(config_file):
    """
    Load a target configuration YAML file and convert it
    into the objects used by the target-independent harness.
    """

    config_path = Path(config_file).resolve()

    if not config_path.exists():
        raise FileNotFoundError(
            f"Target configuration not found: {config_path}"
        )

    with open(
        config_path,
        "r",
        encoding="utf-8",
    ) as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "Target configuration must contain a YAML mapping."
        )

    required = [
        "name",
        "base_url",
    ]

    missing = [
        field
        for field in required
        if field not in data
    ]

    if missing:
        raise ValueError(
            "Missing required configuration fields: "
            + ", ".join(missing)
        )

    base_dir = config_path.parent.parent

    openapi_file = data.get("openapi_file")

    if openapi_file:
        openapi_file = Path(openapi_file)

        if not openapi_file.is_absolute():
            openapi_file = (
                base_dir / openapi_file
            )

    role_matrix_file = data.get(
        "role_matrix_file"
    )

    if role_matrix_file:
        role_matrix_file = Path(
            role_matrix_file
        )

        if not role_matrix_file.is_absolute():
            role_matrix_file = (
                base_dir / role_matrix_file
            )

    target = TargetConfig(
        name=data["name"],
        base_url=data["base_url"],
        openapi_file=openapi_file,
        role_matrix_file=role_matrix_file,
        authentication=data.get(
            "authentication",
            {},
        ),
        web_authentication=data.get(
            "web_authentication",
            {},
        ),
        accounts=data.get(
            "accounts",
            {},
        ),
        resources=data.get(
            "resources",
            {},
        ),
    )

    return target, data


def load_accounts(config_data):
    """
    Load test accounts from environment variables
    described by the target configuration.
    """

    accounts = {}

    for account in config_data.get(
        "accounts",
        [],
    ):

        name = account.get("name")

        if not name:
            continue

        role = account.get(
            "role",
            name,
        )

        username_env = account.get(
            "username_env"
        )

        password_env = account.get(
            "password_env"
        )

        import os

        username = (
            os.getenv(username_env)
            if username_env
            else account.get("username")
        )

        password = (
            os.getenv(password_env)
            if password_env
            else account.get("password")
        )

        if not username or not password:
            print(
                f"[WARN] Account '{name}' "
                "does not have credentials."
            )
            continue

        accounts[role] = TestAccount(
            name=name,
            username=username,
            password=password,
            role=role,
        )

    return accounts


def print_results(results):
    """Print professional, colour-coded access-control test results."""

    def banner(title):
        width = 80
        print()
        print(f"{BLUE}{BOLD}{'=' * width}{RESET}")
        print(f"{BLUE}{BOLD}{title.center(width)}{RESET}")
        print(f"{BLUE}{BOLD}{'=' * width}{RESET}")

    def section(title):
        print()
        print(f"{BLUE}{BOLD}{title}{RESET}")
        print(f"{DIM}{'-' * 80}{RESET}")

    # --------------------------------------------------------------
    # Determine result status
    # --------------------------------------------------------------
    passed = 0
    failed = 0
    skipped = 0
    errors = 0
    inconclusive = 0

    statuses = []

    for result in results:
        # Use the execution result flags as the single source
        # of truth for console classification.
        error_text = getattr(result, "error", None)
        result_skipped = bool(
            getattr(result, "skipped", False)
        )
        result_inconclusive = bool(
            getattr(result, "inconclusive", False)
        )
        result_passed = bool(
            getattr(result, "passed", False)
        )

        if error_text:
            status = "ERROR"
        elif result_skipped:
            status = "SKIP"
        elif result_inconclusive:
            status = "INCONCLUSIVE"
        elif result_passed:
            status = "PASS"
        else:
            status = "FAIL"

        if status == "PASS":
            passed += 1
        elif status == "FAIL":
            failed += 1
        elif status == "SKIP":
            skipped += 1
        elif status == "INCONCLUSIVE":
            inconclusive += 1
        else:
            errors += 1

        statuses.append((result, status))

    total = len(results)

    # --------------------------------------------------------------
    # Main heading
    # --------------------------------------------------------------
    banner("TARGET-INDEPENDENT ACCESS CONTROL TEST HARNESS")

    # --------------------------------------------------------------
    # Test results
    # --------------------------------------------------------------
    banner("ACCESS CONTROL TEST RESULTS")

    for result, status in statuses:
        status_colour = {
            "PASS": GREEN,
            "FAIL": RED,
            "SKIP": YELLOW,
            "INCONCLUSIVE": YELLOW,
            "ERROR": RED,
        }.get(status, WHITE)

        test_id = getattr(result, "test_id", "")
        category = getattr(result, "category", "")
        role = getattr(result, "role", "")
        method = getattr(result, "method", "")
        endpoint = getattr(result, "path", "")

        print(
            f"{WHITE}{test_id:<13}{RESET}"
            f"{status_colour}{BOLD}{status:<7}{RESET}"
            f"{CYAN}{str(category):<23}{RESET}"
            f"{WHITE}{str(role):<16}{RESET}"
            f"{CYAN}{str(method):<7}{RESET}"
            f"{WHITE}{endpoint}{RESET}"
        )

        actual = getattr(result, "actual_status", None)
        expected = getattr(result, "expected_statuses", None)
        error_text = getattr(result, "error", None)

        if actual is not None:
            print(
                f"         {DIM}expected={expected} "
                f"actual={actual}{RESET}"
            )
        elif error_text:
            print(
                f"         {YELLOW}error: {error_text}{RESET}"
            )

    # --------------------------------------------------------------
    # Summary
    # --------------------------------------------------------------
    banner("TEST SUMMARY")

    print(
        f"  {GREEN}{BOLD}Passed : {passed:<4}{RESET}"
        f"  {RED}{BOLD}Failed : {failed:<4}{RESET}"
        f"  {YELLOW}{BOLD}Skipped: {skipped:<4}{RESET}"
        f"  {YELLOW}{BOLD}Inconclusive: {inconclusive:<4}{RESET}"
        f"  {RED}{BOLD}Errors : {errors:<4}{RESET}"
        f"  {CYAN}{BOLD}Total  : {total:<4}{RESET}"
    )

    # --------------------------------------------------------------
    # Overall result
    # --------------------------------------------------------------
    if failed or errors:
        overall = f"{RED}{BOLD}FAIL{RESET}"
    elif inconclusive:
        overall = f"{YELLOW}{BOLD}INCONCLUSIVE{RESET}"
    else:
        overall = f"{GREEN}{BOLD}PASS{RESET}"

    section("OVERALL SECURITY RESULT")
    print(f"  {overall}")

    print()

def run(
    config_file,
    allow_destructive=None,
    policy_file=None,
    learn_policy=False,
):
    """
    Run the complete target-independent flow.
    """

    print()
    print(f"{BLUE}{BOLD}{'=' * 80}{RESET}")
    print(
        f"{BLUE}{BOLD}"
        f"{'TARGET-INDEPENDENT ACCESS CONTROL TEST HARNESS'.center(80)}"
        f"{RESET}"
    )
    print(f"{BLUE}{BOLD}{'=' * 80}{RESET}")

    # --------------------------------------------------------
    # Configuration
    # --------------------------------------------------------

    target, config_data = load_target_config(
        config_file
    )

    web_role_matrix_file = config_data.get(
        "web_role_matrix_file"
    )

    if web_role_matrix_file:
        web_role_matrix_file = Path(
            web_role_matrix_file
        )

        if not web_role_matrix_file.is_absolute():
            web_role_matrix_file = (
                Path(config_file).resolve().parent
                / web_role_matrix_file
            )

    if allow_destructive is None:
        allow_destructive = bool(
            config_data.get(
                "allow_destructive",
                False,
            )
        )

    print()
    print(f"{BLUE}{BOLD}Target{RESET}")
    print(f"{BLUE}{"-" * 80}{RESET}")
    print(
        f"Name : {target.name}"
    )
    print(
        f"URL  : {target.base_url}"
    )
    print(
        f"OpenAPI: {target.openapi_file}"
    )

    # --------------------------------------------------------
    # Accounts
    # --------------------------------------------------------

    accounts = load_accounts(
        config_data
    )

    print()
    print(f"{BLUE}{BOLD}Accounts{RESET}")
    print(f"{BLUE}{"-" * 80}{RESET}")

    if accounts:

        for role, account in accounts.items():
            print(
                f"{role}: {account.name}"
            )

    else:
        print(
            "No usable test accounts configured."
        )

    # --------------------------------------------------------
    # OpenAPI discovery
    # --------------------------------------------------------

    print()
    print(f"{BLUE}{BOLD}Discovery{RESET}")
    print(f"{BLUE}{"-" * 80}{RESET}")

    # Explicit local OpenAPI file has highest priority.
    if target.openapi_file and target.openapi_file.exists():
        print("Discovery mode: OpenAPI (local specification)")

        discovery = EndpointDiscovery(
            str(target.openapi_file)
        )

        endpoints = discovery.endpoints()

    else:
        # No local specification was provided.
        # Try to discover a public OpenAPI/Swagger specification
        # from the target automatically.
        print(
            "Checking target for an automatic OpenAPI specification..."
        )

        remote_openapi = discover_remote_openapi(
            target.base_url
        )

        if remote_openapi:
            print(
                f"{GREEN}Automatic OpenAPI found:{RESET} "
                f"{remote_openapi['url']}"
            )

            import tempfile

            suffix = ".json"

            content_type = (
                remote_openapi.get("content", "")
                .lstrip()
            )

            # YAML specifications may not start with "{"
            if not content_type.startswith("{"):
                suffix = ".yaml"

            temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=suffix,
                prefix="access_control_openapi_",
                delete=False,
            )

            temp_file.write(
                remote_openapi["content"]
            )
            temp_file.close()

            target.openapi_file = Path(
                temp_file.name
            )

            discovery = EndpointDiscovery(
                str(target.openapi_file)
            )

            endpoints = discovery.endpoints()

        else:
            print(
                f"{YELLOW}"
                "No public OpenAPI/Swagger specification found."
                f"{RESET}"
            )
            print(
                "Discovery mode: "
                "Passive HTML/JavaScript API discovery"
            )

            discovery = None
            endpoints = []

    if discovery is not None:
        print(
            f"Discovered {len(endpoints)} endpoints."
        )

    # --------------------------------------------------------
    # Authentication
    # --------------------------------------------------------

    print()
    print(f"{BLUE}{BOLD}Authentication{RESET}")
    print(f"{BLUE}{"-" * 80}{RESET}")

    authentication_manager = AuthenticationManager(
        target=target,
        timeout=REQUEST_TIMEOUT,
    )

    authentications = {}

    for role, account in accounts.items():

        print(
            f"Logging in: {role}"
        )

        authentication = (
            authentication_manager.login(
                account
            )
        )

        authentications[role] = authentication

        print(
            f"  success={authentication.success} "
            f"status={authentication.response_status}"
        )

    if not (target.openapi_file and target.openapi_file.exists()):
        authenticated_session = None

        for authentication in authentications.values():
            if authentication.success and authentication.session:
                authenticated_session = authentication.session
                break

        if authenticated_session:
            discovery = APIRouteDiscovery(
                base_url=target.base_url,
                session=authenticated_session,
            )

            endpoints = discovery.discover()

        print(
            f"Discovered {len(endpoints)} endpoints."
        )

    # --------------------------------------------------------
    # Automatic resource discovery
    # --------------------------------------------------------

    print()
    print(f"{BLUE}{BOLD}Resource Discovery{RESET}")
    print(f"{BLUE}{"-" * 80}{RESET}")

    resource_discovery = ResourceDiscovery(
        target=target,
        accounts=accounts,
        authentications=authentications,
        endpoints=endpoints,
        timeout=REQUEST_TIMEOUT,
    )

    discovered_resources = resource_discovery.discover()

    ownership_evidence = (
        getattr(
            resource_discovery,
            "ownership_evidence",
            {},
        )
        or {}
    )

    if discovered_resources:
        configured_resources = getattr(
            target,
            "resources",
            {},
        ) or {}

        merged_resources = dict(
            configured_resources
        )
        merged_resources.update(
            discovered_resources
        )

        target.resources = merged_resources

        print(
            f"Discovered resources: {discovered_resources}"
        )
    else:
        print(
            "No resources discovered automatically."
        )

    # --------------------------------------------------------
    # Authorization policy
    # --------------------------------------------------------

    print()
    print(f"{BLUE}{BOLD}Authorization Policy{RESET}")
    print(f"{BLUE}{"-" * 80}{RESET}")

    if policy_file:
        policy_path = Path(policy_file)

        if not policy_path.is_absolute():
            policy_path = Path.cwd() / policy_path

        if not policy_path.exists():
            raise FileNotFoundError(
                f"Policy file not found: {policy_path}"
            )

        with open(
            policy_path,
            "r",
            encoding="utf-8",
        ) as file:
            policy_data = json.load(file)

        policy = policy_from_discovery(
            policy_data
        )

        print(
            f"Loaded baseline policy: {policy_path}"
        )

    else:
        authorization_discovery = AuthorizationDiscovery(
            target=target,
            accounts=accounts,
            authentications=authentications,
            endpoints=endpoints,
            timeout=REQUEST_TIMEOUT,
        )

        discovered_policy = (
            authorization_discovery.discover()
        )

        policy = policy_from_discovery(
            discovered_policy
        )

        print(
            "Policy generated by automatic "
            "authorization discovery."
        )

        if learn_policy:
            config_path = Path(config_file)

            baseline_path = (
                config_path.parent
                / f"{config_path.stem}.baseline_policy.json"
            )

            with open(
                baseline_path,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    policy.as_dict(),
                    file,
                    indent=2,
                )

            print()
            print(
                f"Saved baseline policy: {baseline_path}"
            )

            print(
                "Policy learning complete."
            )

            return

    print(
        f"Authorization rules: {len(policy.rules)}"
    )

    for role in policy.roles():

        print()
        print(
            f"{BOLD}[{role}]{RESET}"
        )

        for rule in policy.rules:

            if rule.role != role:
                continue

            print(
                f"  {rule.method:<6} "
                f"{rule.path:<35} "
                f"-> {rule.access}"
            )

    # --------------------------------------------------------
    # Web authorization policy
    # --------------------------------------------------------

    web_policy = None

    if web_role_matrix_file:
        if not web_role_matrix_file.exists():
            raise FileNotFoundError(
                f"Web role matrix file not found: "
                f"{web_role_matrix_file}"
            )

        with open(
            web_role_matrix_file,
            "r",
            encoding="utf-8",
        ) as file:
            web_policy_data = yaml.safe_load(file)

        web_policy = policy_from_discovery(
            web_policy_data
        )

        print()
        print(
            f"{BLUE}{BOLD}"
            "Web Authorization Policy"
            f"{RESET}"
        )
        print(
            f"{BLUE}{"-" * 80}{RESET}"
        )
        print(
            f"Loaded web policy: "
            f"{web_role_matrix_file}"
        )
        print(
            f"Web authorization rules: "
            f"{len(web_policy.rules)}"
        )

    # --------------------------------------------------------
    # Test generation
    # --------------------------------------------------------

    print()
    print(f"{BLUE}{BOLD}Test Generation{RESET}")
    print(f"{BLUE}{"-" * 80}{RESET}")

    generator = AccessControlTestGenerator(
        endpoints=endpoints,
        policy=policy,
        authentication_type=(
            target.authentication.get(
                "type",
                "jwt",
            )
        ),
        ownership_evidence=ownership_evidence,
    )

    tests = generator.generate()

    print(
        f"Generated {len(tests)} candidate tests."
    )

    # --------------------------------------------------------
    # Web discovery and test generation
    # --------------------------------------------------------

    web_tests = []

    if web_policy and target.web_authentication:
        print()
        print(
            f"{BLUE}{BOLD}"
            "Web Discovery"
            f"{RESET}"
        )
        print(
            f"{BLUE}{"-" * 80}{RESET}"
        )

        web_authentication_manager = (
            AuthenticationManager(
                target=target,
                timeout=REQUEST_TIMEOUT,
            )
        )

        web_admin_account = None

        for account in accounts.values():
            if account.role == "admin":
                web_admin_account = account
                break

        if web_admin_account is None:
            raise ValueError(
                "Web discovery requires an admin account."
            )

        web_authentication = (
            web_authentication_manager.login(
                web_admin_account,
                authentication_config=(
                    target.web_authentication
                ),
            )
        )

        if not web_authentication.success:
            print()
            print(
                f"{YELLOW}Web authentication unavailable: "
                f"{web_authentication.error}{RESET}"
            )
            print(
                "Skipping web authorization tests and "
                "continuing with API authorization tests."
            )
            web_tests = []
        else:
            web_session = (
                web_authentication_manager.create_session(
                    web_authentication
                )
            )

            web_discovery = WebRouteDiscovery(
                target=target,
                session=web_session,
                start_paths=["/dashboard"],
                timeout=REQUEST_TIMEOUT,
            )

            web_routes = web_discovery.discover()

            print(
                f"Discovered {len(web_routes)} web routes."
            )

            web_generator = WebAccessControlTestGenerator(
                routes=web_routes,
                policy=web_policy,
            )

            web_tests = web_generator.generate()

            print(
                f"Generated {len(web_tests)} web candidate tests."
            )

    # --------------------------------------------------------
    # Execution
    # --------------------------------------------------------

    print()
    print(f"{BLUE}{BOLD}Execution{RESET}")
    print(f"{BLUE}{"-" * 80}{RESET}")

    engine = AccessControlExecutionEngine(
        target=target,
        accounts=accounts,
        timeout=REQUEST_TIMEOUT,
        allow_destructive=allow_destructive,
    )

    api_results = engine.execute_all(
        tests
    )

    web_results = []

    if web_tests:
        print()
        print(
            f"{BLUE}{BOLD}"
            "Web Execution"
            f"{RESET}"
        )
        print(
            f"{BLUE}{"-" * 80}{RESET}"
        )

        web_engine = WebAccessControlExecutionEngine(
            target=target,
            accounts=accounts,
            timeout=REQUEST_TIMEOUT,
            allow_destructive=allow_destructive,
        )

        web_results = web_engine.execute_all(
            web_tests
        )

        print(
            f"Executed {len(web_results)} web authorization tests."
        )

    results = api_results + web_results

    # --------------------------------------------------------
    # Results
    # --------------------------------------------------------

    print_results(
        results
    )

    # --------------------------------------------------------
    # Reports
    # --------------------------------------------------------

    reports_dir = Path("reports")
    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_target_name = "".join(
        character
        if character.isalnum() or character in "-_"
        else "_"
        for character in target.name
    ).strip("_") or "target"

    html_report = (
        reports_dir
        / f"{safe_target_name}_access_control_report.html"
    )

    pdf_report = (
        reports_dir
        / f"{safe_target_name}_access_control_report.pdf"
    )

    json_report = (
        reports_dir
        / f"{safe_target_name}_access_control_report.json"
    )

    generate_html_report(
        results=results,
        target=target,
        output_file=html_report,
    )

    generate_pdf_report(
        results=results,
        target=target,
        output_file=pdf_report,
    )

    generate_json_report(
        results=results,
        target=target,
        output_file=json_report,
    )

    print()
    print(f"{BLUE}{BOLD}{'=' * 80}{RESET}")
    print(f"{BLUE}{BOLD}{'REPORTS'.center(80)}{RESET}")
    print(f"{BLUE}{BOLD}{'=' * 80}{RESET}")
    print(f"HTML: {html_report}")
    print(f"PDF : {pdf_report}")
    print(f"JSON: {json_report}")
    print(f"{BLUE}{BOLD}{'=' * 80}{RESET}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Target-independent access-control "
            "testing harness."
        )
    )

    parser.add_argument(
        "config",
        nargs="?",
        help=(
            "Path to the target configuration YAML file."
        ),
    )

    parser.add_argument(
        "--url",
        help=(
            "Target URL for direct one-command testing."
        ),
    )

    parser.add_argument(
        "--target-name",
        default="Target Application",
        help="Display name for the target in generated reports.",
    )

    parser.add_argument(
        "--openapi-file",
        default=None,
        help=(
            "Path to an OpenAPI specification for direct testing."
        ),
    )

    parser.add_argument(
        "--admin-user",
        help="Administrator username.",
    )

    parser.add_argument(
        "--admin-pass",
        help="Administrator password.",
    )

    parser.add_argument(
        "--user-user",
        help="Normal user username.",
    )

    parser.add_argument(
        "--user-pass",
        help="Normal user password.",
    )

    parser.add_argument(
        "--login-path",
        default="/api/login",
        help=(
            "Login endpoint path for direct testing. "
            "Default: /api/login"
        ),
    )

    parser.add_argument(
        "--username-field",
        default="username",
        help=(
            "Username/email field used by the login endpoint. "
            "Default: username"
        ),
    )

    parser.add_argument(
        "--password-field",
        default="password",
        help=(
            "Password field used by the login endpoint. "
            "Default: password"
        ),
    )

    parser.add_argument(
        "--token-field",
        default=None,
        help=(
            "JWT response field. Supports nested fields "
            "such as authentication.token."
        ),
    )

    parser.add_argument(
        "--auth-type",
        choices=["jwt", "session", "cookie"],
        default="jwt",
        help=(
            "Authentication type for direct testing. "
            "Default: jwt"
        ),
    )

    policy_group = parser.add_mutually_exclusive_group()

    policy_group.add_argument(
        "--policy-file",
        help=(
            "Load a previously generated authorization "
            "baseline policy instead of discovering a new one."
        ),
    )

    policy_group.add_argument(
        "--learn-policy",
        action="store_true",
        help=(
            "Automatically discover authorization behaviour "
            "and save it as the target baseline policy."
        ),
    )

    parser.add_argument(
        "--allow-destructive",
        action="store_true",
        default=None,
        help=(
            "Allow destructive HTTP methods such as DELETE "
            "against the explicitly authorized target."
        ),
    )

    args = parser.parse_args()

    direct_mode = any(
        value is not None
        for value in (
            args.url,
            args.admin_user,
            args.admin_pass,
            args.user_user,
            args.user_pass,
        )
    )

    required_direct_values = {
        "--url": args.url,
        "--admin-user": args.admin_user,
        "--admin-pass": args.admin_pass,
        "--user-user": args.user_user,
        "--user-pass": args.user_pass,
    }

    try:
        # ----------------------------------------------------
        # Direct URL + credentials mode
        # ----------------------------------------------------

        if direct_mode:
            if args.config:
                raise ValueError(
                    "Do not use a configuration file together "
                    "with direct URL/credential options."
                )

            missing = [
                option
                for option, value in required_direct_values.items()
                if not value
            ]

            if missing:
                raise ValueError(
                    "Direct testing requires: "
                    + ", ".join(missing)
                )

            if not args.url.startswith(
                ("http://", "https://")
            ):
                raise ValueError(
                    "--url must start with http:// or https://"
                )

            print()
            print(
                f"{CYAN}{BOLD}"
                "Direct target mode enabled."
                f"{RESET}"
            )
            print(
                f"{DIM}"
                "Creating temporary target configuration..."
                f"{RESET}"
            )

            openapi_file = None
            if args.openapi_file:
                openapi_file = str(
                    Path(args.openapi_file).expanduser().resolve()
                )

            direct_config = {
                "name": args.target_name,
                "base_url": args.url.rstrip("/"),
                "openapi_file": openapi_file,
                "authentication": {
                    "type": args.auth_type,
                    "login": {
                        "method": "POST",
                        "path": args.login_path,
                        "username_field": args.username_field,
                        "password_field": args.password_field,
                        "token_field": args.token_field,
                    },
                },
                "accounts": [
                    {
                        "name": "admin",
                        "role": "admin",
                        "username": args.admin_user,
                        "password": args.admin_pass,
                    },
                    {
                        "name": "user",
                        "role": "user",
                        "username": args.user_user,
                        "password": args.user_pass,
                    },
                ],
                "resources": {},
                "allow_destructive": bool(
                    args.allow_destructive
                ),
            }

            temp_path = None

            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    suffix=".yaml",
                    prefix="access_control_cli_",
                    delete=False,
                    encoding="utf-8",
                ) as temp_file:
                    yaml.safe_dump(
                        direct_config,
                        temp_file,
                        sort_keys=False,
                    )
                    temp_path = temp_file.name

                run(
                    config_file=temp_path,
                    allow_destructive=args.allow_destructive,
                    policy_file=args.policy_file,
                    learn_policy=args.learn_policy,
                )

            finally:
                if temp_path:
                    try:
                        Path(temp_path).unlink()
                    except FileNotFoundError:
                        pass

            return

        # ----------------------------------------------------
        # Existing YAML configuration mode
        # ----------------------------------------------------

        if not args.config:
            parser.error(
                "Provide either a configuration file or "
                "--url with administrator and user credentials."
            )

        run(
            config_file=args.config,
            allow_destructive=args.allow_destructive,
            policy_file=args.policy_file,
            learn_policy=args.learn_policy,
        )

    except KeyboardInterrupt:
        print()
        print("Test run interrupted.")

    except Exception as error:
        print()
        print(
            f"ERROR: {error}"
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
