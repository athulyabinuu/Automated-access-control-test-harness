from dataclasses import dataclass, field
from typing import Dict


@dataclass
class AuthorizationRule:
    role: str
    method: str
    path: str
    access: str


@dataclass
class AuthorizationPolicy:
    """
    Normalized authorization policy generated from
    observed application behaviour.
    """

    rules: list[AuthorizationRule] = field(
        default_factory=list
    )

    def add_rule(
        self,
        role,
        method,
        path,
        access,
    ):
        self.rules.append(
            AuthorizationRule(
                role=role,
                method=method.upper(),
                path=path,
                access=access,
            )
        )

    def get(
        self,
        role,
        method,
        path,
    ):
        method = method.upper()

        for rule in self.rules:
            if (
                rule.role == role
                and rule.method == method
                and rule.path == path
            ):
                return rule.access

        return None

    def roles(self):
        return sorted(
            {
                rule.role
                for rule in self.rules
            }
        )

    def as_dict(self):
        result = {
            "roles": {}
        }

        for rule in self.rules:
            role_rules = result["roles"].setdefault(
                rule.role,
                {},
            )

            role_rules[
                f"{rule.method} {rule.path}"
            ] = {
                "access": rule.access
            }

        return result


def policy_from_discovery(
    discovered_policy,
):
    """
    Convert the raw authorization-discovery result
    into a normalized AuthorizationPolicy.
    """

    policy = AuthorizationPolicy()

    for role, rules in (
        discovered_policy
        .get("roles", {})
        .items()
    ):

        for endpoint, rule in rules.items():

            parts = endpoint.split(
                " ",
                1,
            )

            if len(parts) != 2:
                continue

            method, path = parts

            policy.add_rule(
                role=role,
                method=method,
                path=path,
                access=rule.get(
                    "access",
                    "deny",
                ),
            )

    return policy
