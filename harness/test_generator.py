from dataclasses import dataclass, field
from typing import Any, Dict, List

from harness.policy_model import AuthorizationPolicy


@dataclass
class CandidateTest:
    test_id: str
    category: str
    method: str
    path: str
    role: str
    expected_statuses: List[int] = field(
        default_factory=list
    )
    parameter_overrides: Dict[str, Any] = field(
        default_factory=dict
    )
    description: str = ""


class AccessControlTestGenerator:
    """
    Generate target-independent access-control test candidates.

    Endpoint discovery provides the endpoint inventory.
    AuthorizationPolicy provides the observed authorization
    behaviour for each role and endpoint.
    """

    ALLOWED_STATUSES = [
        200,
        201,
        202,
        204,
    ]

    DENIED_STATUSES = [
        401,
        403,
        404,
    ]

    def __init__(
        self,
        endpoints,
        policy: AuthorizationPolicy,
        authentication_type: str = "jwt",
    ):
        self.endpoints = endpoints
        self.policy = policy
        self.authentication_type = (
            authentication_type or "jwt"
        ).lower()

    # ========================================================
    # PUBLIC API
    # ========================================================

    def generate(self):
        tests = []

        counter = 1

        for endpoint in self.endpoints:
            generated = self._generate_for_endpoint(
                endpoint
            )

            for test in generated:
                test.test_id = (
                    f"AC-{counter:04d}"
                )

                tests.append(test)
                counter += 1

        return tests

    # ========================================================
    # ENDPOINT GENERATION
    # ========================================================

    def _generate_for_endpoint(self, endpoint):
        tests = []

        method = str(
            endpoint["method"]
        ).upper()

        path = endpoint["path"]

        security = endpoint.get(
            "security",
            []
        )

        parameters = endpoint.get(
            "parameters",
            []
        )

        is_authenticated = bool(security)

        path_parameters = [
            parameter
            for parameter in parameters
            if parameter.get("in") == "path"
        ]

        # Passive HTML/JavaScript discovery does not provide
        # OpenAPI parameter metadata. Infer path parameters
        # directly from placeholders such as:
        #
        #   /api/users/{user_id}
        #   /api/orders/{order_id}
        #
        # This keeps test generation compatible with
        # passive API discovery.
        if not path_parameters:
            import re

            inferred_names = re.findall(
                r"\{([^{}]+)\}",
                path,
            )

            path_parameters = [
                {
                    "name": name,
                    "in": "path",
                    "required": True,
                }
                for name in inferred_names
            ]

        # ----------------------------------------------------
        # Authentication tests
        # ----------------------------------------------------

        if is_authenticated:
            tests.append(
                CandidateTest(
                    test_id="",
                    category="authentication",
                    method=method,
                    path=path,
                    role="anonymous",
                    expected_statuses=(
                        [401, 403, 302]
                        if self.authentication_type == "session"
                        else [401, 403]
                    ),
                    description=(
                        "Verify that an unauthenticated "
                        "request is rejected."
                    ),
                )
            )

            tests.append(
                CandidateTest(
                    test_id="",
                    category="invalid-token",
                    method=method,
                    path=path,
                    role="invalid-token",
                    expected_statuses=(
                        [401, 403, 302]
                        if self.authentication_type == "session"
                        else [401, 403]
                    ),
                    description=(
                        "Verify that an invalid authentication "
                        "token is rejected."
                    ),
                )
            )

        # ----------------------------------------------------
        # Policy-driven authorization tests
        # ----------------------------------------------------

        for role in self.policy.roles():

            access = self.policy.get(
                role=role,
                method=method,
                path=path,
            )

            if access is None:
                continue

            # ------------------------------------------------
            # No path parameters
            # ------------------------------------------------

            if not path_parameters:

                if access == "allow":
                    tests.append(
                        CandidateTest(
                            test_id="",
                            category="authenticated-access",
                            method=method,
                            path=path,
                            role=role,
                            expected_statuses=(
                                self.ALLOWED_STATUSES.copy()
                            ),
                            description=(
                                "Verify that the role can access "
                                "the endpoint according to the "
                                "automatically discovered policy."
                            ),
                        )
                    )

                elif access == "deny":
                    tests.append(
                        CandidateTest(
                            test_id="",
                            category="authorization",
                            method=method,
                            path=path,
                            role=role,
                            expected_statuses=(
                                self.DENIED_STATUSES.copy()
                            ),
                            description=(
                                "Verify that the role is denied "
                                "access according to the "
                                "automatically discovered policy."
                            ),
                        )
                    )

                continue

            # ------------------------------------------------
            # Resource endpoints
            # ------------------------------------------------

            for parameter in path_parameters:

                parameter_name = parameter.get(
                    "name"
                )

                if not parameter_name:
                    continue

                # --------------------------------------------
                # ANY
                # --------------------------------------------

                if access == "any":

                    tests.append(
                        CandidateTest(
                            test_id="",
                            category="ownership",
                            method=method,
                            path=path,
                            role=role,
                            expected_statuses=(
                                self.ALLOWED_STATUSES.copy()
                            ),
                            parameter_overrides={
                                parameter_name:
                                    (
                                        "<another-resource-id>"
                                        if method == "DELETE"
                                        else "<own-resource-id>"
                                    )
                            },
                            description=(
                                "Verify that the role can access "
                                "a permitted resource according to "
                                "the automatically discovered policy."
                            ),
                        )
                    )

                    tests.append(
                        CandidateTest(
                            test_id="",
                            category="horizontal",
                            method=method,
                            path=path,
                            role=role,
                            expected_statuses=(
                                self.ALLOWED_STATUSES.copy()
                            ),
                            parameter_overrides={
                                parameter_name:
                                    "<other-resource-id>"
                            },
                            description=(
                                "Verify that the role can access "
                                "another resource when the "
                                "automatically discovered policy "
                                "allows unrestricted resource access."
                            ),
                        )
                    )

                # --------------------------------------------
                # OWN
                # --------------------------------------------

                elif access == "own":

                    tests.append(
                        CandidateTest(
                            test_id="",
                            category="ownership",
                            method=method,
                            path=path,
                            role=role,
                            expected_statuses=(
                                self.ALLOWED_STATUSES.copy()
                            ),
                            parameter_overrides={
                                parameter_name:
                                    "<own-resource-id>"
                            },
                            description=(
                                "Verify that the role can access "
                                "its own resource according to "
                                "the automatically discovered policy."
                            ),
                        )
                    )

                    tests.append(
                        CandidateTest(
                            test_id="",
                            category="horizontal",
                            method=method,
                            path=path,
                            role=role,
                            expected_statuses=(
                                self.DENIED_STATUSES.copy()
                            ),
                            parameter_overrides={
                                parameter_name:
                                    "<other-resource-id>"
                            },
                            description=(
                                "Verify that the role cannot access "
                                "another owner's resource according "
                                "to the automatically discovered policy."
                            ),
                        )
                    )

                # --------------------------------------------
                # ALLOW
                # --------------------------------------------

                elif access == "allow":

                    tests.append(
                        CandidateTest(
                            test_id="",
                            category="authenticated-access",
                            method=method,
                            path=path,
                            role=role,
                            expected_statuses=(
                                self.ALLOWED_STATUSES.copy()
                            ),
                            description=(
                                "Verify that the role can access "
                                "the resource endpoint according "
                                "to the automatically discovered policy."
                            ),
                        )
                    )

                # --------------------------------------------
                # DENY
                # --------------------------------------------

                elif access == "deny":

                    tests.append(
                        CandidateTest(
                            test_id="",
                            category="authorization",
                            method=method,
                            path=path,
                            role=role,
                            expected_statuses=(
                                self.DENIED_STATUSES.copy()
                            ),
                            parameter_overrides={
                                parameter_name:
                                    "<other-resource-id>"
                            },
                            description=(
                                "Verify that the role is denied "
                                "access to the resource according "
                                "to the automatically discovered policy."
                            ),
                        )
                    )

        return tests


def generate_tests(
    endpoints,
    policy,
):
    """
    Convenience function.
    """

    generator = AccessControlTestGenerator(
        endpoints,
        policy,
    )

    return generator.generate()


if __name__ == "__main__":
    import argparse

    from harness.discovery import EndpointDiscovery

    parser = argparse.ArgumentParser(
        description=(
            "Generate access-control test candidates "
            "from an OpenAPI specification and "
            "an automatically discovered authorization policy."
        )
    )

    parser.add_argument(
        "openapi_file",
        help="Path to OpenAPI specification",
    )

    args = parser.parse_args()

    discovery = EndpointDiscovery(
        args.openapi_file
    )

    print(
        "This module requires an AuthorizationPolicy "
        "from authorization discovery."
    )
