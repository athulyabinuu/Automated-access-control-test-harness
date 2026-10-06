from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import requests

from harness.authentication import (
    AuthenticationManager,
    AuthenticationResult,
)
from harness.config import TargetConfig, TestAccount
from harness.test_generator import CandidateTest


@dataclass
class ExecutionResult:
    test_id: str
    category: str
    role: str
    method: str
    path: str

    expected_statuses: list[int] = field(default_factory=list)
    actual_status: Optional[int] = None

    passed: bool = False
    skipped: bool = False

    request_url: str = ""
    response_body: Any = None

    finding: str = ""
    evidence: str = ""
    error: Optional[str] = None


class AccessControlExecutionEngine:
    """
    Execute generated access-control candidates against an
    explicitly supplied authorized target.

    This class contains no target-specific URLs, user IDs,
    order IDs, usernames, or application assumptions.
    """

    def __init__(
        self,
        target: TargetConfig,
        accounts: Dict[str, TestAccount],
        timeout: int = 5,
        allow_destructive: bool = False,
        verify_tls: bool = True,
    ):
        self.target = target
        self.accounts = accounts
        self.timeout = timeout
        self.allow_destructive = allow_destructive
        self.verify_tls = verify_tls

        self.auth_manager = AuthenticationManager(
            target=target,
            timeout=timeout,
        )

        self.authentications: Dict[
            str,
            AuthenticationResult,
        ] = {}

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    def authenticate_accounts(self):
        """
        Authenticate all configured test accounts.

        Failed accounts are retained as failed authentication
        results rather than crashing the complete test run.
        """

        for role, account in self.accounts.items():
            result = self.auth_manager.login(account)
            self.authentications[role] = result

        return self.authentications

    # ========================================================
    # PUBLIC EXECUTION API
    # ========================================================

    def execute_all(self, tests):
        """
        Execute all generated candidates.
        """

        if not self.authentications:
            self.authenticate_accounts()

        results = []

        for test in tests:
            result = self.execute(test)
            results.append(result)

        return results

    def execute(self, test: CandidateTest):
        """
        Execute one candidate test.
        """

        method = test.method.upper()

        if method in {"DELETE"} and not self.allow_destructive:
            return ExecutionResult(
                test_id=test.test_id,
                category=test.category,
                role=test.role,
                method=method,
                path=test.path,
                expected_statuses=test.expected_statuses,
                skipped=True,
                finding="",
                evidence=(
                    "Destructive HTTP method blocked by default. "
                    "Use the explicit destructive-test option "
                    "when testing an authorized target."
                ),
            )

        authentication = self._authentication_for_test(test)

        if test.role not in {
            "anonymous",
            "invalid-token",
        } and authentication is None:
            return ExecutionResult(
                test_id=test.test_id,
                category=test.category,
                role=test.role,
                method=method,
                path=test.path,
                expected_statuses=test.expected_statuses,
                skipped=True,
                error=(
                    f"No authentication context available "
                    f"for role '{test.role}'."
                ),
            )

        if (
            authentication is not None
            and not authentication.success
        ):
            return ExecutionResult(
                test_id=test.test_id,
                category=test.category,
                role=test.role,
                method=method,
                path=test.path,
                expected_statuses=test.expected_statuses,
                skipped=True,
                error=(
                    f"Authentication failed for role "
                    f"'{test.role}': "
                    f"{authentication.error}"
                ),
            )

        resolved_path = self._resolve_path(
            test.path,
            test.parameter_overrides,
            test.role,
        )

        if resolved_path is None:
            return ExecutionResult(
                test_id=test.test_id,
                category=test.category,
                role=test.role,
                method=method,
                path=test.path,
                expected_statuses=test.expected_statuses,
                skipped=True,
                error=(
                    "Path parameters could not be resolved. "
                    "Provide the required resource values "
                    "through the target configuration."
                ),
            )

        url = (
            f"{self.target.base_url}"
            f"{resolved_path}"
        )

        headers = {}

        cookies = {}

        if test.role == "invalid-token":

            headers["Authorization"] = (
                "Bearer "
                f"{self.auth_manager.invalid_token()}"
            )

        elif authentication is not None:

            headers.update(
                self.auth_manager.build_headers(
                    authentication
                )
            )

            if authentication.cookies:
                cookies.update(
                    authentication.cookies
                )

        try:

            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                cookies=cookies,
                timeout=self.timeout,
                verify=self.verify_tls,
                allow_redirects=test.category not in {
                    "authentication",
                    "invalid-token",
                },
            )

        except requests.Timeout as error:

            return ExecutionResult(
                test_id=test.test_id,
                category=test.category,
                role=test.role,
                method=method,
                path=test.path,
                expected_statuses=test.expected_statuses,
                request_url=url,
                error=f"Request timeout: {error}",
                finding="",
                evidence=str(error),
            )

        except requests.RequestException as error:

            return ExecutionResult(
                test_id=test.test_id,
                category=test.category,
                role=test.role,
                method=method,
                path=test.path,
                expected_statuses=test.expected_statuses,
                request_url=url,
                error=str(error),
                finding="",
                evidence=str(error),
            )

        actual_status = response.status_code

        passed = (
            actual_status
            in test.expected_statuses
        )

        finding = self._build_finding(
            test,
            actual_status,
            passed,
        )

        evidence = (
            f"HTTP {actual_status} "
            f"from {method} {resolved_path}"
        )

        body = self._safe_response_body(
            response
        )

        return ExecutionResult(
            test_id=test.test_id,
            category=test.category,
            role=test.role,
            method=method,
            path=test.path,
            expected_statuses=test.expected_statuses,
            actual_status=actual_status,
            passed=passed,
            skipped=False,
            request_url=url,
            response_body=body,
            finding=finding,
            evidence=evidence,
        )

    # ========================================================
    # AUTHENTICATION CONTEXT
    # ========================================================

    def _authentication_for_test(self, test):
        if test.role in {
            "anonymous",
            "invalid-token",
        }:
            return None

        return self.authentications.get(
            test.role
        )

    # ========================================================
    # PATH RESOLUTION
    # ========================================================

    def _resolve_path(
        self,
        path,
        overrides,
        role,
    ):
        """
        Resolve OpenAPI path parameters using target
        configuration and candidate overrides.

        Supported placeholders:

            <own-resource-id>
            <other-resource-id>

        The actual values come from target.resources.
        """

        resolved = path

        resources = getattr(
            self.target,
            "resources",
            {},
        )

        for parameter_name, value in overrides.items():

            if value == "<own-resource-id>":
                value = self._resource_value(
                    parameter_name,
                    "own",
                    resources,
                    path,
                    role,
                )

            elif value == "<other-resource-id>":
                value = self._resource_value(
                    parameter_name,
                    "other",
                    resources,
                    path,
                    role,
                )

            elif value == "<another-resource-id>":
                value = self._resource_value(
                    parameter_name,
                    "another",
                    resources,
                    path,
                    role,
                )

            if value is None:
                return None

            resolved = resolved.replace(
                "{" + parameter_name + "}",
                str(value),
            )

        # Resolve any remaining path parameters from the
        # target resource configuration.
        while "{" in resolved and "}" in resolved:

            start_index = resolved.find("{")
            end_index = resolved.find(
                "}",
                start_index,
            )

            if end_index == -1:
                return None

            parameter_name = resolved[
                start_index + 1:end_index
            ]

            value = self._resource_value(
                parameter_name,
                "own",
                resources,
                path, role,
            )

            if value is None:
                return None

            resolved = (
                resolved[:start_index]
                + str(value)
                + resolved[end_index + 1:]
            )

        return resolved

    @staticmethod
    def _resource_value(
        parameter_name,
        ownership,
        resources,
        path=None,
        role=None,
    ):
        """
        Resolve a path parameter from the target resource
        configuration without hardcoded resource types.

        Resource matching is based on:
        1. Explicit parameter names such as user_id or order_id.
        2. The resource name appearing in the endpoint path.
        3. Singular/plural resource-name matching.

        The actual resource IDs come from target.resources.
        """

        if not resources:
            return None

        normalized_parameter = str(
            parameter_name or ""
        ).lower()

        normalized_path = str(
            path or ""
        ).lower()

        for resource_type, resource_config in resources.items():

            resource_name = str(
                resource_type
            ).lower().strip()

            if not resource_name:
                continue

            # Match explicit parameters such as:
            # user_id, order_id, account_id, product_id
            parameter_matches = (
                normalized_parameter == f"{resource_name}_id"
                or normalized_parameter.startswith(
                    f"{resource_name}_"
                )
                or normalized_parameter.endswith(
                    f"_{resource_name}_id"
                )
            )

            # Match endpoint paths such as:
            # /users/{id}
            # /orders/{id}
            # /products/{id}
            path_matches = (
                f"/{resource_name}/" in normalized_path
                or f"/{resource_name}s/" in normalized_path
            )

            if parameter_matches or path_matches:
                if not isinstance(resource_config, dict):
                    continue

                # Backward-compatible support for the original
                # target.resources structure:
                #
                # user:
                #   own: "2"
                #   other: "3"
                if ownership in resource_config:
                    return resource_config.get(
                        ownership
                    )

                # Automatically discovered resources are
                # grouped by authenticated role:
                #
                # user:
                #   admin:
                #     own: "1"
                #     other: "2"
                #   user:
                #     own: "2"
                #     other: "1"
                if role:
                    role_resources = resource_config.get(
                        role
                    )

                    if isinstance(role_resources, dict):
                        value = role_resources.get(
                            ownership
                        )

                        if value is not None:
                            return value

                # Authentication tests use synthetic roles such as
                # "anonymous" and "invalid-token". For these tests,
                # the resource ID only needs to produce a valid path;
                # authentication must be rejected before authorization.
                for role_resources in resource_config.values():
                    if not isinstance(role_resources, dict):
                        continue

                    value = role_resources.get(
                        ownership
                    )

                    if value is not None:
                        return value

        return None

    # ========================================================
    # RESPONSE BODY
    # ========================================================

    @staticmethod
    def _safe_response_body(response):
        try:
            return response.json()
        except ValueError:
            text = response.text

            if len(text) > 4000:
                return text[:4000] + "...[truncated]"

            return text

    # ========================================================
    # FINDING CLASSIFICATION
    # ========================================================

    @staticmethod
    def _build_finding(
        test,
        actual_status,
        passed,
    ):
        if passed:
            return ""

        expected = ", ".join(
            str(status)
            for status in test.expected_statuses
        )

        if test.category in {
            "authentication",
            "invalid-token",
        }:
            return (
                "Authentication control failure: "
                f"{test.role} received HTTP {actual_status} "
                f"for {test.method.upper()} {test.path}; "
                f"expected HTTP status {expected}."
            )

        if test.category in {
            "horizontal",
            "ownership",
        }:
            return (
                "Horizontal authorization failure: "
                f"{test.role} received HTTP {actual_status} "
                f"for {test.method.upper()} {test.path}; "
                f"expected HTTP status {expected}. "
                "The requested resource may be accessible "
                "outside the permitted ownership boundary."
            )

        if test.category == "vertical":
            return (
                "Vertical authorization failure: "
                f"role '{test.role}' received HTTP "
                f"{actual_status} for "
                f"{test.method.upper()} {test.path}; "
                f"expected HTTP status {expected}. "
                "A lower-privileged role received a response "
                "outside its permitted access policy."
            )

        if test.category == "privileged-access":
            return (
                "Privileged-access authorization failure: "
                f"role '{test.role}' received HTTP "
                f"{actual_status} for "
                f"{test.method.upper()} {test.path}; "
                f"expected HTTP status {expected}."
            )

        if test.category == "authenticated-access":
            return (
                "Authenticated-access control failure: "
                f"role '{test.role}' received HTTP "
                f"{actual_status} for "
                f"{test.method.upper()} {test.path}; "
                f"expected HTTP status {expected}."
            )

        return (
            "Access-control test failure: "
            f"role '{test.role}' received HTTP "
            f"{actual_status} for "
            f"{test.method.upper()} {test.path}; "
            f"expected HTTP status {expected}."
        )

