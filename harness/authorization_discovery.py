from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import requests


@dataclass
class AuthorizationObservation:
    role: str
    method: str
    path: str
    scenario: str
    parameter_values: Dict[str, Any]
    status: Optional[int]
    success: bool
    error: str = ""


class AuthorizationDiscovery:
    """
    Automatically infer authorization behaviour from
    observed responses of authorized test accounts.

    This module does not use a manually supplied role matrix.

    Policy values inferred by this module:

        allow
        deny
        own
        any

    The discovery process is observation-based. It does not
    assume that /admin/ means administrator-only.
    """

    ALLOWED_STATUSES = {
        200,
        201,
        202,
        204,
    }

    DENIED_STATUSES = {
        401,
        403,
    }

    def __init__(
        self,
        target,
        accounts,
        authentications,
        endpoints,
        timeout=5,
        verify_tls=True,
    ):
        self.target = target
        self.accounts = accounts
        self.authentications = authentications
        self.endpoints = endpoints
        self.timeout = timeout
        self.verify_tls = verify_tls

        self.observations: List[
            AuthorizationObservation
        ] = []

    # ========================================================
    # PUBLIC API
    # ========================================================

    def discover(self):
        """
        Probe discovered endpoints and infer authorization
        behaviour from the observed HTTP responses.
        """

        for endpoint in self.endpoints:
            self._probe_endpoint(endpoint)

        return self.build_policy()

    # ========================================================
    # ENDPOINT PROBING
    # ========================================================

    def _probe_endpoint(self, endpoint):
        method = str(
            endpoint.get("method", "GET")
        ).upper()

        path = str(
            endpoint.get("path", "/")
        )

        # Authentication endpoints are not authorization
        # policy endpoints. The login request requires
        # credentials rather than an already authenticated
        # authorization context.
        login_config = (
            getattr(
                self.target,
                "authentication",
                {},
            ).get("login", {})
        )

        login_method = str(
            login_config.get(
                "method",
                "POST",
            )
        ).upper()

        login_path = login_config.get(
            "path",
            "/api/login",
        )

        if (
            method == login_method
            and path == login_path
        ):
            return

        parameters = endpoint.get(
            "parameters",
            [],
        )

        path_parameters = [
            parameter
            for parameter in parameters
            if parameter.get("in") == "path"
        ]

        # Passive HTML/JavaScript discovery does not have
        # OpenAPI parameter metadata. Infer path parameters
        # directly from placeholders such as:
        #
        #   /api/users/{user_id}
        #   /api/orders/{order_id}
        #
        # This allows resource-level authorization testing
        # even when OpenAPI is unavailable.
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

        for role, account in self.accounts.items():

            authentication = self.authentications.get(
                role
            )

            if authentication is None:
                continue

            if not authentication.success:
                continue

            if path_parameters:
                self._probe_resource_endpoint(
                    role=role,
                    method=method,
                    path=path,
                    path_parameters=path_parameters,
                )
            else:
                self._probe_simple_endpoint(
                    role=role,
                    method=method,
                    path=path,
                    authentication=authentication,
                )

    # ========================================================
    # SIMPLE ENDPOINTS
    # ========================================================

    def _probe_simple_endpoint(
        self,
        role,
        method,
        path,
        authentication,
    ):
        status, error = self._request(
            method=method,
            path=path,
            authentication=authentication,
        )

        self.observations.append(
            AuthorizationObservation(
                role=role,
                method=method,
                path=path,
                scenario="baseline",
                parameter_values={},
                status=status,
                success=(
                    status
                    in self.ALLOWED_STATUSES
                ),
                error=error,
            )
        )

    # ========================================================
    # RESOURCE ENDPOINTS
    # ========================================================

    def _probe_resource_endpoint(
        self,
        role,
        method,
        path,
        path_parameters,
    ):
        resources = getattr(
            self.target,
            "resources",
            {},
        )

        for parameter in path_parameters:

            parameter_name = parameter.get(
                "name"
            )

            if not parameter_name:
                continue

            own_value = self._resource_value(
                parameter_name,
                "own",
                resources,
                path,
                role,
            )

            other_value = self._resource_value(
                parameter_name,
                "other",
                resources,
                path,
                role,
            )

            if own_value is not None:
                self._probe_resource(
                    role=role,
                    method=method,
                    path=path,
                    parameter_name=parameter_name,
                    value=own_value,
                    scenario="own",
                )

            if other_value is not None:
                self._probe_resource(
                    role=role,
                    method=method,
                    path=path,
                    parameter_name=parameter_name,
                    value=other_value,
                    scenario="other",
                )

    def _probe_resource(
        self,
        role,
        method,
        path,
        parameter_name,
        value,
        scenario,
    ):
        authentication = self.authentications.get(
            role
        )

        if authentication is None:
            return

        resolved_path = path.replace(
            "{" + parameter_name + "}",
            str(value),
        )

        status, error = self._request(
            method=method,
            path=resolved_path,
            authentication=authentication,
        )

        self.observations.append(
            AuthorizationObservation(
                role=role,
                method=method,
                path=path,
                scenario=scenario,
                parameter_values={
                    parameter_name: value,
                },
                status=status,
                success=(
                    status
                    in self.ALLOWED_STATUSES
                ),
                error=error,
            )
        )

    # ========================================================
    # HTTP REQUEST
    # ========================================================

    def _request(
        self,
        method,
        path,
        authentication,
    ):
        url = (
            f"{self.target.base_url}"
            f"{path}"
        )

        headers = {}

        cookies = {}

        if authentication is not None:
            headers.update(
                self.target_auth_headers(
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
            )

            return response.status_code, ""

        except requests.RequestException as error:
            return None, str(error)

    # ========================================================
    # AUTHENTICATION HEADER ADAPTER
    # ========================================================

    def target_auth_headers(
        self,
        authentication,
    ):
        """
        Build authentication headers using the same
        AuthenticationManager already used by the harness.
        """

        from harness.authentication import (
            AuthenticationManager,
        )

        manager = AuthenticationManager(
            target=self.target,
            timeout=self.timeout,
        )

        return manager.build_headers(
            authentication
        )

    # ========================================================
    # RESOURCE RESOLUTION
    # ========================================================

    @staticmethod
    def _resource_value(
        parameter_name,
        ownership,
        resources,
        path,
        role,
    ):
        if not resources:
            return None

        normalized_parameter = str(
            parameter_name or ""
        ).lower()

        normalized_path = str(
            path or ""
        ).lower()

        for resource_type, resource_config in (
            resources.items()
        ):

            resource_name = str(
                resource_type
            ).lower().strip()

            if not resource_name:
                continue

            parameter_matches = (
                normalized_parameter
                == f"{resource_name}_id"
                or normalized_parameter.startswith(
                    f"{resource_name}_"
                )
                or normalized_parameter.endswith(
                    f"_{resource_name}_id"
                )
            )

            path_matches = (
                f"/{resource_name}/"
                in normalized_path
                or
                f"/{resource_name}s/"
                in normalized_path
            )

            if parameter_matches or path_matches:
                if isinstance(
                    resource_config,
                    dict,
                ):
                    role_resources = resource_config.get(
                        role
                    )

                    if isinstance(
                        role_resources,
                        dict,
                    ):
                        return role_resources.get(
                            ownership
                        )

        return None

    # ========================================================
    # POLICY INFERENCE
    # ========================================================

    def build_policy(self):
        """
        Convert observations into an automatically inferred
        role/access policy.
        """

        roles = {}

        grouped = {}

        for observation in self.observations:

            key = (
                observation.role,
                observation.method,
                observation.path,
            )

            grouped.setdefault(
                key,
                [],
            ).append(observation)

        for (
            role,
            method,
            path,
        ), observations in grouped.items():

            access = self._infer_access(
                observations
            )

            roles.setdefault(
                role,
                {}
            )[
                f"{method} {path}"
            ] = {
                "access": access,
                "observations": [
                    asdict(
                        observation
                    )
                    for observation
                    in observations
                ],
            }

        return {
            "roles": roles
        }

    # ========================================================
    # ACCESS INFERENCE
    # ========================================================

    def _infer_access(
        self,
        observations,
    ):
        own = [
            item
            for item in observations
            if item.scenario == "own"
        ]

        other = [
            item
            for item in observations
            if item.scenario == "other"
        ]

        if own or other:

            own_allowed = any(
                item.success
                for item in own
            )

            other_allowed = any(
                item.success
                for item in other
            )

            if own_allowed and other_allowed:
                return "any"

            if own_allowed and not other_allowed:
                return "own"

            if (
                not own_allowed
                and not other_allowed
            ):
                return "deny"

            if other_allowed:
                return "any"

            return "deny"

        baseline = [
            item
            for item in observations
            if item.scenario == "baseline"
        ]

        if any(
            item.success
            for item in baseline
        ):
            return "allow"

        return "deny"
