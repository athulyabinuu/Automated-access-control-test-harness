from dataclasses import dataclass
from typing import Optional

import requests

from harness.config import TestAccount, TargetConfig


@dataclass
class AuthenticationResult:
    account: TestAccount
    success: bool
    token: Optional[str] = None
    cookies: Optional[dict] = None
    session: Optional[requests.Session] = None
    response_status: Optional[int] = None
    error: Optional[str] = None


class AuthenticationManager:
    """
    Handles authentication for an authorized target.

    Authentication behavior is defined by TargetConfig rather
    than being hard-coded for a particular application.
    """

    def __init__(
        self,
        target: TargetConfig,
        timeout: int = 5,
    ):
        self.target = target
        self.timeout = timeout

    # ========================================================
    # LOGIN
    # ========================================================

    def login(
        self,
        account: TestAccount,
        authentication_config=None,
    ) -> AuthenticationResult:

        authentication = (
            authentication_config
            if authentication_config is not None
            else self.target.authentication
        )

        auth_type = authentication.get(
            "type",
            "jwt",
        ).lower()

        login_config = authentication.get(
            "login",
            {},
        )

        method = login_config.get(
            "method",
            "POST",
        ).upper()

        path = login_config.get(
            "path",
            "/api/login",
        )

        username_field = login_config.get(
            "username_field",
            "username",
        )

        password_field = login_config.get(
            "password_field",
            "password",
        )

        url = (
            f"{self.target.base_url}"
            f"{path}"
        )

        payload = {
            username_field: account.username,
            password_field: account.password,
        }

        session = requests.Session()

        try:
            request_kwargs = {
                "method": method,
                "url": url,
                "timeout": self.timeout,
            }

            if auth_type in {
                "cookie",
                "session",
            }:
                request_kwargs["data"] = payload
            else:
                request_kwargs["json"] = payload

            response = session.request(
                **request_kwargs,
            )

        except requests.RequestException as error:
            return AuthenticationResult(
                account=account,
                success=False,
                error=str(error),
            )

        if not 200 <= response.status_code < 300:
            return AuthenticationResult(
                account=account,
                success=False,
                response_status=response.status_code,
                error=(
                    f"Login failed with "
                    f"HTTP {response.status_code}"
                ),
            )

        # ----------------------------------------------------
        # JWT authentication
        # ----------------------------------------------------

        if auth_type == "jwt":
            token = self._extract_token(
                response,
                login_config,
            )

            if not token:
                return AuthenticationResult(
                    account=account,
                    success=False,
                    response_status=response.status_code,
                    error=(
                        "Login succeeded but no JWT "
                        "token was found in the response."
                    ),
                )

            return AuthenticationResult(
                account=account,
                success=True,
                token=token,
                cookies=session.cookies.get_dict(),
                session=session,
                response_status=response.status_code,
            )

        # ----------------------------------------------------
        # Cookie/session authentication
        # ----------------------------------------------------

        if auth_type in {
            "cookie",
            "session",
        }:
            cookies = session.cookies.get_dict()

            return AuthenticationResult(
                account=account,
                success=True,
                cookies=cookies,
                session=session,
                response_status=response.status_code,
            )

        return AuthenticationResult(
            account=account,
            success=True,
            cookies=session.cookies.get_dict(),
            response_status=response.status_code,
        )

    # ========================================================
    # TOKEN EXTRACTION
    # ========================================================

    def _extract_token(
        self,
        response,
        login_config,
    ):
        """
        Extract JWT from a configurable login response.

        Supported response forms include:

            {"token": "..."}
            {"access_token": "..."}
            {"jwt": "..."}
        """

        response_token_field = login_config.get(
            "token_field"
        )

        try:
            data = response.json()
        except ValueError:
            data = None

        if isinstance(data, dict):

            if response_token_field:
                current = data

                for field in response_token_field.split("."):
                    if not isinstance(current, dict):
                        current = None
                        break

                    current = current.get(field)

                if current:
                    return current

            for field in (
                "access_token",
                "token",
                "jwt",
            ):
                token = data.get(field)

                if token:
                    return token

        # Some APIs return the token in a header.
        for header_name in (
            "Authorization",
            "X-Auth-Token",
            "X-Access-Token",
        ):
            value = response.headers.get(
                header_name
            )

            if not value:
                continue

            if value.lower().startswith("bearer "):
                return value[7:].strip()

            return value.strip()

        return None

    # ========================================================
    # REQUEST HEADERS
    # ========================================================

    @staticmethod
    def build_headers(
        authentication: AuthenticationResult,
    ):
        headers = {}

        if authentication.token:
            headers["Authorization"] = (
                f"Bearer {authentication.token}"
            )

        return headers

    # ========================================================
    # INVALID TOKEN
    # ========================================================

    @staticmethod
    def invalid_token():
        return "invalid.jwt.token"

    # ========================================================
    # SESSION
    # ========================================================

    def create_session(
        self,
        authentication: AuthenticationResult,
    ):
        session = requests.Session()

        if authentication.cookies:
            session.cookies.update(
                authentication.cookies
            )

        if authentication.token:
            session.headers.update({
                "Authorization": (
                    f"Bearer {authentication.token}"
                )
            })

        return session
