from collections import deque
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class WebRouteDiscovery:
    """
    Discover web application routes by crawling HTML pages.

    The crawler is target-independent and uses the configured
    target base URL rather than hard-coded application routes.
    """

    def __init__(
        self,
        target,
        session=None,
        start_paths=None,
        timeout=5,
        verify_tls=True,
        max_pages=50,
    ):
        self.target = target
        self.session = session or requests.Session()
        self.start_paths = start_paths or ["/"]
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.max_pages = max_pages

    def discover(self):
        discovered = []
        visited = set()
        queue = deque(self.start_paths)

        while queue and len(visited) < self.max_pages:
            path = queue.popleft()

            normalized_path = self._normalize_path(path)

            if not normalized_path:
                continue

            if normalized_path in visited:
                continue

            if self._should_skip(normalized_path):
                continue

            visited.add(normalized_path)

            response = self._request(normalized_path)

            discovered.append({
                "method": "GET",
                "path": normalized_path,
                "status": response.status_code
                if response is not None
                else None,
            })

            if response is None:
                continue

            content_type = response.headers.get(
                "Content-Type",
                "",
            ).lower()

            if "text/html" not in content_type:
                continue

            for link in self._extract_links(
                response.text,
                response.url,
            ):
                if link not in visited:
                    queue.append(link)

        return discovered

    def _request(self, path):
        url = urljoin(
            f"{self.target.base_url}/",
            path.lstrip("/"),
        )

        try:
            return self.session.get(
                url,
                timeout=self.timeout,
                verify=self.verify_tls,
                allow_redirects=True,
            )
        except requests.RequestException:
            return None

    def _extract_links(self, html, current_url):
        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        links = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href")

            if not href:
                continue

            absolute_url = urljoin(
                current_url,
                href,
            )

            parsed = urlparse(
                absolute_url
            )

            if parsed.scheme not in {
                "http",
                "https",
            }:
                continue

            base = urlparse(
                self.target.base_url
            )

            if (
                parsed.scheme,
                parsed.netloc,
            ) != (
                base.scheme,
                base.netloc,
            ):
                continue

            path = parsed.path or "/"

            if self._should_skip(path):
                continue

            links.add(
                self._normalize_path(path)
            )

        return sorted(links)

    @staticmethod
    def _normalize_path(path):
        if not path:
            return "/"

        if not path.startswith("/"):
            path = "/" + path

        return path.rstrip("/") or "/"

    @staticmethod
    def _should_skip(path):
        return (
            path == "/logout"
            or path.startswith("/api/")
            or path.startswith("/static/")
            or path.startswith("/favicon")
        )


if __name__ == "__main__":
    import argparse
    import os

    from harness.authentication import AuthenticationManager
    from harness.config import load_target_config

    parser = argparse.ArgumentParser(
        description=(
            "Discover web routes by crawling "
            "HTML pages."
        )
    )

    parser.add_argument(
        "config_file",
        help="Target configuration file",
    )

    parser.add_argument(
        "--username",
        default=os.getenv("USER_USERNAME", "user1"),
    )

    parser.add_argument(
        "--password",
        default=os.getenv("USER_PASSWORD", "user123"),
    )

    args = parser.parse_args()

    target = load_target_config(
        args.config_file
    )

    account = None

    for configured_account in target.accounts.values():
        if configured_account.username == args.username:
            account = configured_account
            break

    if account is None:
        from harness.config import TestAccount

        account = TestAccount(
            name="web-user",
            username=args.username,
            password=args.password,
            role="user",
        )

    authentication_manager = AuthenticationManager(
        target
    )

    authentication = authentication_manager.login(
        account,
        authentication_config=target.web_authentication,
    )

    if not authentication.success:
        print(
            "Web authentication failed:"
        )
        print(
            authentication.error
        )
        raise SystemExit(1)

    session = authentication_manager.create_session(
        authentication
    )

    discovery = WebRouteDiscovery(
        target,
        session=session,
        start_paths=["/dashboard"],
    )

    routes = discovery.discover()

    print()
    print("Web Route Discovery")
    print("=" * 60)

    for route in routes:
        print(
            f"{route['method']:6} "
            f"{route['path']:30} "
            f"HTTP {route['status']}"
        )

    print("=" * 60)
    print(
        f"Routes discovered: {len(routes)}"
    )
