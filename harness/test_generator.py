import re

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
        ownership_evidence=None,
    ):
        self.endpoints = endpoints
        self.policy = policy
        self.authentication_type = (
            authentication_type or "jwt"
        ).lower()

        # Optional independently discovered ownership evidence.
        # Existing policy inference is not modified.
        self.ownership_evidence = (
            ownership_evidence or {}
        )

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

    def _generate_ownership_evidence_tests(
        self,
        endpoint,
        method,
        path,
        path_parameters,
    ):
        """
        Generate strict ownership tests only when ownership was
        independently established from authenticated JWT claims.

        Existing targets without such evidence are unaffected.
        """

        if not self.ownership_evidence:
            return []

        if not path_parameters:
            return []

        # JWT ownership evidence maps one resource ID to one
        # path parameter. Do not apply it to ambiguous endpoints
        # containing multiple resource parameters.
        if len(path_parameters) != 1:
            return []

        resource_type = (
            self._resource_type_from_path(path)
        )

        if not resource_type:
            return []

        evidence = (
            self.ownership_evidence.get(
                resource_type
            )
        )

        if not isinstance(
            evidence,
            dict,
        ):
            return []

        if evidence.get(
            "source"
        ) != "jwt_claim":
            return []

        roles = evidence.get(
            "roles",
            {},
        )

        if not isinstance(
            roles,
            dict,
        ):
            return []

        tests = []

        for parameter in path_parameters:

            parameter_name = (
                parameter.get("name")
            )

            if not parameter_name:
                continue

            for role, role_data in roles.items():

                if not isinstance(
                    role_data,
                    dict,
                ):
                    continue

                own = role_data.get(
                    "own"
                )

                other = role_data.get(
                    "other"
                )

                if (
                    own is None
                    or other is None
                ):
                    continue

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
                            "Verify that the authenticated "
                            "role can access its own "
                            "JWT-associated resource."
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
                            "Verify that the authenticated "
                            "role cannot access another "
                            "authenticated role's resource. "
                            "Ownership was independently "
                            "established from JWT resource "
                            "identifiers."
                        ),
                    )
                )

        return tests

    @staticmethod
    def _resource_type_from_path(path):

        parts = [
            part.strip()
            for part in str(path).split("/")
            if part.strip()
        ]

        for index, part in enumerate(parts):

            if not re.fullmatch(
                r"\{[^{}]+\}",
                part,
            ):
                continue

            if index == 0:
                return None

            resource = (
                parts[index - 1]
                .lower()
            )

            if resource.endswith("ies"):
                resource = (
                    resource[:-3] + "y"
                )

            elif resource.endswith("ses"):
                resource = resource[:-2]

            elif (
                resource.endswith("s")
                and not resource.endswith("ss")
            ):
                resource = resource[:-1]

            return resource

        return None

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
        # Evidence-based ownership tests
        # ----------------------------------------------------
        #
        # These are generated separately from observed policy.
        # Therefore a vulnerable HTTP 200 cannot be learned as
        # an expected authorization result.

        tests.extend(
            self._generate_ownership_evidence_tests(
                endpoint=endpoint,
                method=method,
                path=path,
                path_parameters=path_parameters,
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

            # When independently established JWT ownership evidence
            # exists for this resource, policy-driven resource tests
            # are only safe for endpoints with one resource parameter.
            # Multi-parameter endpoints such as:
            #   /rest/basket/{id}/coupon/{code}
            # must not reuse the basket ID for the second parameter.
            resource_type_for_policy = (
                self._resource_type_from_path(path)
            )

            has_jwt_ownership_evidence = (
                resource_type_for_policy in self.ownership_evidence
                and isinstance(
                    self.ownership_evidence.get(
                        resource_type_for_policy
                    ),
                    dict,
                )
                and self.ownership_evidence.get(
                    resource_type_for_policy
                ).get("source") == "jwt_claim"
            )

            if (
                has_jwt_ownership_evidence
                and len(path_parameters) != 1
            ):
                continue

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
