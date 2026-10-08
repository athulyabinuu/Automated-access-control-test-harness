from harness.authentication import AuthenticationManager
from harness.execution import ExecutionResult


class WebAccessControlExecutionEngine:
    """
    Execute web authorization tests using session authentication.

    This engine is intentionally separate from the API execution
    engine so the existing API workflow remains unchanged.
    """

    def __init__(
        self,
        target,
        accounts,
        timeout=5,
        verify_tls=True,
        allow_destructive=False,
    ):
        self.target = target
        self.accounts = accounts
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.allow_destructive = allow_destructive

        self.auth_manager = AuthenticationManager(
            target=target,
            timeout=timeout,
        )

        self.authentications = {}

    def authenticate_accounts(self):
        for role, account in self.accounts.items():
            authentication = self.auth_manager.login(
                account,
                authentication_config=(
                    self.target.web_authentication
                ),
            )

            self.authentications[role] = authentication

        return self.authentications

    def execute(self, test):
        if test.method.upper() == "DELETE" and not self.allow_destructive:
            return ExecutionResult(
                test_id=test.test_id,
                category=test.category,
                role=test.role,
                method=test.method,
                path=test.path,
                expected_statuses=test.expected_statuses,
                skipped=True,
                finding=(
                    "Destructive HTTP method blocked by default. "
                    "Use the explicit destructive-test option "
                    "when testing an authorized target."
                ),
                evidence=(
                    "DELETE request was not sent because "
                    "destructive testing is disabled."
                ),
            )

        authentication = self.authentications.get(
            test.role
        )

        if authentication is None:
            return ExecutionResult(
                test_id=test.test_id,
                category=test.category,
                role=test.role,
                method=test.method,
                path=test.path,
                expected_statuses=test.expected_statuses,
                skipped=True,
                error=(
                    f"No web authentication found "
                    f"for role '{test.role}'."
                ),
            )

        if not authentication.success:
            return ExecutionResult(
                test_id=test.test_id,
                category=test.category,
                role=test.role,
                method=test.method,
                path=test.path,
                expected_statuses=test.expected_statuses,
                skipped=True,
                error=(
                    f"Web authentication failed "
                    f"for role '{test.role}'."
                ),
            )

        session = self.auth_manager.create_session(
            authentication
        )

        url = f"{self.target.base_url}{test.path}"

        try:
            response = session.request(
                method=test.method,
                url=url,
                timeout=self.timeout,
                verify=self.verify_tls,
                allow_redirects=False,
            )

        except Exception as error:
            return ExecutionResult(
                test_id=test.test_id,
                category=test.category,
                role=test.role,
                method=test.method,
                path=test.path,
                expected_statuses=test.expected_statuses,
                request_url=url,
                error=str(error),
            )

        actual_status = response.status_code

        # HTTP 400 usually means the generated request is
        # missing required input or contains invalid input.
        # HTTP 5xx means the target application/server
        # encountered an error.
        # Neither response is sufficient to establish an
        # authorization vulnerability.
        inconclusive = (
            actual_status in {400, 402}
            or 500 <= actual_status <= 599
        )

        passed = (
            not inconclusive
            and actual_status
            in test.expected_statuses
        )

        finding = ""

        if actual_status == 400:
            finding = (
                "Inconclusive authorization result: "
                f"target returned HTTP 400 for "
                f"{test.method} {test.path}. "
                "The request may be missing required input "
                "or contain invalid input."
            )

        elif 500 <= actual_status <= 599:
            finding = (
                "Inconclusive authorization result: "
                f"target returned HTTP {actual_status} for "
                f"{test.method} {test.path}. "
                "The target application/server returned an "
                "error, so authorization could not be "
                "reliably evaluated."
            )

        elif not passed:
            if actual_status in [200, 201, 202, 204]:
                finding = (
                    f"Web authorization failure: "
                    f"role '{test.role}' accessed "
                    f"{test.method} {test.path} "
                    f"with HTTP {actual_status}, "
                    f"but access was expected to be denied."
                )
            else:
                finding = (
                    f"Unexpected web authorization response "
                    f"HTTP {actual_status}."
                )

        evidence = (
            f"Expected HTTP status: "
            f"{test.expected_statuses}; "
            f"Actual HTTP status: "
            f"{actual_status}"
        )

        return ExecutionResult(
            test_id=test.test_id,
            category=test.category,
            role=test.role,
            method=test.method,
            path=test.path,
            expected_statuses=test.expected_statuses,
            actual_status=actual_status,
            passed=passed,
            skipped=False,
            inconclusive=inconclusive,
            request_url=url,
            response_body=response.text,
            finding=finding,
            evidence=evidence,
        )

    def execute_all(self, tests):
        if not self.authentications:
            self.authenticate_accounts()

        return [
            self.execute(test)
            for test in tests
        ]
