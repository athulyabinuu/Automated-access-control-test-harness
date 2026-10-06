import os
from pathlib import Path

import yaml


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

REPORT_DIR = BASE_DIR / "reports"
CONFIG_DIR = BASE_DIR / "configs"

REQUEST_TIMEOUT = int(
    os.getenv("ACCESS_CONTROL_TIMEOUT", "5")
)


# ============================================================
# TEST ACCOUNT
# ============================================================

class TestAccount:
    def __init__(
        self,
        name,
        username,
        password,
        role=None,
    ):
        self.name = name
        self.username = username
        self.password = password
        self.role = role

    def __repr__(self):
        return (
            f"TestAccount("
            f"name={self.name!r}, "
            f"role={self.role!r}, "
            f"username={self.username!r}"
            f")"
        )


# ============================================================
# TARGET CONFIGURATION
# ============================================================

class TargetConfig:
    def __init__(
        self,
        name,
        base_url,
        openapi_file=None,
        role_matrix_file=None,
        authentication=None,
        web_authentication=None,
        accounts=None,
        resources=None,
        role_matrix=None,
        allow_destructive=False,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")

        self.openapi_file = (
            Path(openapi_file)
            if openapi_file
            else None
        )

        self.role_matrix_file = (
            Path(role_matrix_file)
            if role_matrix_file
            else None
        )
        self.authentication = authentication or {}
        self.web_authentication = web_authentication or {}
        self.accounts = accounts or {}
        self.resources = resources or {}
        self.role_matrix = role_matrix or {}
        self.allow_destructive = bool(allow_destructive)

    def __repr__(self):
        return (
            f"TargetConfig("
            f"name={self.name!r}, "
            f"base_url={self.base_url!r}, "
            f"openapi_file={self.openapi_file!r}, "
            f"accounts={list(self.accounts)!r}"
            f")"
        )


# ============================================================
# ENVIRONMENT ACCOUNT LOADING
# ============================================================

def load_account_from_environment(
    username_env,
    password_env,
    name,
    role=None,
):
    username = os.getenv(username_env)
    password = os.getenv(password_env)

    if not username or not password:
        return None

    return TestAccount(
        name=name,
        username=username,
        password=password,
        role=role,
    )


# ============================================================
# CONFIGURATION LOADER
# ============================================================

def load_target_config(config_file):
    """
    Load a target-independent harness configuration.

    The configuration file defines the target URL,
    OpenAPI specification, authentication mechanism,
    role matrix, and test accounts.
    """

    config_path = Path(config_file)

    if not config_path.is_absolute():
        config_path = BASE_DIR / config_path

    if not config_path.exists():
        raise FileNotFoundError(
            f"Target configuration not found: "
            f"{config_path}"
        )

    with config_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "Target configuration must contain "
            "a YAML mapping."
        )

    name = data.get(
        "name",
        "Unnamed Target",
    )

    base_url = data.get("base_url")

    if not base_url:
        raise ValueError(
            "Target configuration requires "
            "'base_url'."
        )

    openapi_file = data.get("openapi_file")

    if openapi_file:
        openapi_file = resolve_config_path(
            config_path,
            openapi_file,
        )

    role_matrix_file = data.get(
        "role_matrix_file"
    )

    if role_matrix_file:
        role_matrix_file = resolve_config_path(
            config_path,
            role_matrix_file,
        )

    authentication = data.get(
        "authentication",
        {},
    )

    if not isinstance(authentication, dict):
        raise ValueError(
            "'authentication' must be a YAML mapping."
        )

    web_authentication = data.get(
        "web_authentication",
        {},
    )

    if not isinstance(web_authentication, dict):
        raise ValueError(
            "'web_authentication' must be a YAML mapping."
        )

    accounts = {}

    for account in data.get("accounts", []):
        if not isinstance(account, dict):
            raise ValueError(
                "Each account must be a YAML mapping."
            )

        account_name = account.get("name")

        if not account_name:
            raise ValueError(
                "Each account requires a 'name'."
            )

        username_env = account.get(
            "username_env"
        )

        password_env = account.get(
            "password_env"
        )

        if not username_env or not password_env:
            raise ValueError(
                f"Account '{account_name}' must "
                "define username_env and password_env."
            )

        test_account = load_account_from_environment(
            username_env=username_env,
            password_env=password_env,
            name=account_name,
            role=account.get("role"),
        )

        if test_account:
            accounts[account_name] = test_account

    resources = data.get("resources", {})

    allow_destructive = data.get(
        "allow_destructive",
        False,
    )

    role_matrix = {}

    if role_matrix_file:
        if not role_matrix_file.exists():
            raise FileNotFoundError(
                f"Role matrix not found: {role_matrix_file}"
            )

        with open(
            role_matrix_file,
            "r",
            encoding="utf-8",
        ) as file:
            role_matrix = yaml.safe_load(file) or {}

        if not isinstance(role_matrix, dict):
            raise ValueError(
                "Role matrix must contain a YAML mapping."
            )

        if not isinstance(
            role_matrix.get("roles", {}),
            dict,
        ):
            raise ValueError(
                "Role matrix must contain a 'roles' mapping."
            )

    return TargetConfig(
        name=name,
        base_url=base_url,
        openapi_file=openapi_file,
        role_matrix_file=role_matrix_file,
        authentication=authentication,
        web_authentication=web_authentication,
        accounts=accounts,
        resources=resources,
        role_matrix=role_matrix,
        allow_destructive=allow_destructive,
    )


# ============================================================
# PATH RESOLUTION
# ============================================================

def resolve_config_path(
    config_path,
    configured_path,
):
    path = Path(configured_path)

    if path.is_absolute():
        return path

    # First interpret paths relative to the project root.
    project_path = BASE_DIR / path

    if project_path.exists():
        return project_path

    # Otherwise interpret them relative to
    # the configuration file.
    return config_path.parent / path
