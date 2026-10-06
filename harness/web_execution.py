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
    ):
        self.target = target
        self.accounts = accounts
        self.timeout = timeout
        self.verify_tls = verify_tls

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

        passed = (
            response.status_code
            in test.expected_statuses
        )

        finding = ""

        if not passed:
            if response.status_code in [200, 201, 202, 204]:
                finding = (
                    f"Web authorization failure: "
                    f"role '{test.role}' accessed "
                    f"{test.method} {test.path} "
                    f"with HTTP {response.status_code}, "
                    f"but access was expected to be denied."
                )
            else:
                finding = (
                    f"Unexpected web authorization response "
                    f"HTTP {response.status_code}."
                )

        evidence = (
            f"Expected HTTP status: "
            f"{test.expected_statuses}; "
            f"Actual HTTP status: "
            f"{response.status_code}"
        )

        return ExecutionResult(
            test_id=test.test_id,
            category=test.category,
            role=test.role,
            method=test.method,
            path=test.path,
            expected_statuses=test.expected_statuses,
            actual_status=response.status_code,
            passed=passed,
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
