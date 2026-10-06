from harness.test_generator import CandidateTest


class WebAccessControlTestGenerator:
    """
    Generate access-control tests for discovered web routes.

    The generator is target-independent. Expected access is
    supplied through an AuthorizationPolicy.
    """

    ALLOWED_STATUSES = [
        200,
        201,
        202,
        204,
    ]

    DENIED_STATUSES = [
        403,
        404,
    ]

    def __init__(
        self,
        routes,
        policy,
    ):
        self.routes = routes
        self.policy = policy

    def generate(self):
        tests = []
        counter = 1

        for route in self.routes:
            method = str(
                route["method"]
            ).upper()

            path = route["path"]

            for role in self.policy.roles():
                access = self.policy.get(
                    role,
                    method,
                    path,
                )

                if access is None:
                    continue

                if access == "allow":
                    expected_statuses = (
                        self.ALLOWED_STATUSES
                    )
                else:
                    expected_statuses = (
                        self.DENIED_STATUSES
                    )

                tests.append(
                    CandidateTest(
                        test_id=(
                            f"WEB-AC-{counter:04d}"
                        ),
                        category=(
                            "web-authorization"
                        ),
                        method=method,
                        path=path,
                        role=role,
                        expected_statuses=(
                            expected_statuses
                        ),
                        description=(
                            f"Web {method} {path} "
                            f"for role '{role}' "
                            f"expects {access} access."
                        ),
                    )
                )

                counter += 1

        return tests
