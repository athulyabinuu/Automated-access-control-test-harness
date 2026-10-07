import re
from urllib.parse import urljoin, urlparse

import requests


class APIRouteDiscovery:
    """
    Passively discover API routes from public HTML and JavaScript.

    This module does not authenticate or send state-changing requests.
    """

    HTTP_METHODS = {
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    }

    API_PATTERNS = [
        # Generic quoted API route
        re.compile(
            r"""["'`]((?:https?://[^"'`]+)?/?(?:api|service)/[A-Za-z0-9_./${}:?=&%-]+)["'`]"""
        ),

        # fetch("/api/...")
        re.compile(
            r"""fetch\s*\(\s*["'`]((?:https?://[^"'`]+)?/?(?:api|service)/[A-Za-z0-9_./${}:?=&%-]+)"""
        ),

        # axios.get("/api/..."), axios.post(...), etc.
        re.compile(
            r"""axios\.(?:get|post|put|patch|delete)\s*\(\s*["'`]((?:https?://[^"'`]+)?/?(?:api|service)/[A-Za-z0-9_./${}:?=&%-]+)""",
            re.IGNORECASE,
        ),

        # method: "GET", url: "/api/..."
        re.compile(
            r"""(?:url|path)\s*:\s*["'`]((?:https?://[^"'`]+)?/?(?:api|service)/[A-Za-z0-9_./${}:?=&%-]+)["'`]""",
            re.IGNORECASE,
        ),
    ]

    METHOD_PATTERNS = [
        (
            "GET",
            re.compile(
                r"""(?:axios\.)?get\s*\(\s*["'`]((?:https?://[^"'`]+)?/?(?:api|service)/[A-Za-z0-9_./${}:?=&%-]+)""",
                re.IGNORECASE,
            ),
        ),
        (
            "POST",
            re.compile(
                r"""(?:axios\.)?post\s*\(\s*["'`]((?:https?://[^"'`]+)?/?(?:api|service)/[A-Za-z0-9_./${}:?=&%-]+)""",
                re.IGNORECASE,
            ),
        ),
        (
            "PUT",
            re.compile(
                r"""(?:axios\.)?put\s*\(\s*["'`]((?:https?://[^"'`]+)?/?(?:api|service)/[A-Za-z0-9_./${}:?=&%-]+)""",
                re.IGNORECASE,
            ),
        ),
        (
            "PATCH",
            re.compile(
                r"""(?:axios\.)?patch\s*\(\s*["'`]((?:https?://[^"'`]+)?/?(?:api|service)/[A-Za-z0-9_./${}:?=&%-]+)""",
                re.IGNORECASE,
            ),
        ),
        (
            "DELETE",
            re.compile(
                r"""(?:axios\.)?delete\s*\(\s*["'`]((?:https?://[^"'`]+)?/?(?:api|service)/[A-Za-z0-9_./${}:?=&%-]+)""",
                re.IGNORECASE,
            ),
        ),
    ]

    FETCH_METHOD_PATTERN = re.compile(
        r"""fetch\s*\(\s*["'`]((?:https?://[^"'`]+)?/?(?:api|service)/[A-Za-z0-9_./${}:?=&%-]+)["'`]\s*,\s*\{(?:(?!\}).)*?\bmethod\s*:\s*["'`](GET|POST|PUT|PATCH|DELETE)["'`]""",
        re.IGNORECASE | re.DOTALL,
    )

    APIFETCH_METHOD_PATTERN = re.compile(
        r"""apiFetch\s*\(\s*["'`]((?:https?://[^"'`]+)?/?(?:api|service)/[A-Za-z0-9_./${}:?=&%-]+)["'`]\s*,\s*\{\s*(?:[^{}]|\{[^{}]*\})*?\bmethod\s*:\s*["'`](GET|POST|PUT|PATCH|DELETE)["'`]""",
        re.IGNORECASE | re.DOTALL,
    )

    APIFETCH_TEMPLATE_PATTERN = re.compile(
        r"""apiFetch\s*\(\s*`([^`]+)`""",
        re.IGNORECASE,
    )

    def __init__(
        self,
        base_url,
        timeout=5,
        verify_tls=True,
        session=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_tls = verify_tls

        self.session = session or requests.Session()

        self.discovered_routes = set()
        self.discovered_methods = set()
        self.javascript_urls = set()

    COMMON_OPENAPI_PATHS = (
        "/openapi.json",
        "/swagger.json",
        "/openapi.yaml",
        "/swagger.yaml",
        "/api/openapi.json",
        "/api/swagger.json",
        "/api-docs",
        "/api/docs",
        "/v1/openapi.json",
        "/v2/openapi.json",
        "/v3/openapi.json",
    )

    def discover_openapi_url(self):
        """
        Passively look for a remotely exposed OpenAPI/Swagger document.

        Only GET requests are used. No authentication or state-changing
        requests are performed.
        """
        for path in self.COMMON_OPENAPI_PATHS:
            url = urljoin(
                self.base_url + "/",
                path.lstrip("/"),
            )

            try:
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    verify=self.verify_tls,
                )

            except requests.RequestException:
                continue

            if not response.ok:
                continue

            content_type = (
                response.headers.get(
                    "Content-Type",
                    "",
                ).lower()
            )

            body = response.text.lstrip()

            # JSON OpenAPI/Swagger documents normally begin with
            # an object containing "openapi" or "swagger".
            if (
                "json" in content_type
                or body.startswith("{")
            ):
                try:
                    document = response.json()
                except ValueError:
                    continue

                if isinstance(document, dict) and (
                    "openapi" in document
                    or "swagger" in document
                ):
                    return url

            # YAML specifications may be served as text/plain,
            # application/yaml, or application/x-yaml.
            if (
                "yaml" in content_type
                or "yml" in content_type
            ):
                if (
                    "openapi:" in body
                    or "swagger:" in body
                ):
                    return url

        return None

    def discover(self):
        """
        Fetch the target entry page and inspect linked JavaScript
        assets for API-looking routes.
        """

        entry_pages = [
            self.base_url,
            urljoin(self.base_url + "/", "start.mvc"),
            urljoin(self.base_url + "/", "index.html"),
            urljoin(self.base_url + "/", "index.htm"),
        ]

        for entry_url in entry_pages:
            try:
                response = self.session.get(
                    entry_url,
                    timeout=self.timeout,
                    verify=self.verify_tls,
                )

            except requests.RequestException:
                continue

            if not response.ok:
                continue

            html = response.text

            before_javascript = len(self.javascript_urls)

            self._extract_routes(html)
            self._extract_html_routes(html)
            self._extract_javascript_urls(html)

            # Keep checking entry pages so all JavaScript assets
            # can be discovered.
            if len(self.javascript_urls) > before_javascript:
                continue

        self._discover_common_javascript_urls()

        processed_javascript_urls = set()

        while True:
            pending_urls = sorted(
                self.javascript_urls - processed_javascript_urls
            )

            if not pending_urls:
                break

            for javascript_url in pending_urls:
                processed_javascript_urls.add(javascript_url)

                try:
                    javascript = self.session.get(
                        javascript_url,
                        timeout=self.timeout,
                        verify=self.verify_tls,
                    )

                    if javascript.ok:
                        self._extract_routes(
                            javascript.text
                        )

                        self._extract_javascript_dependencies(
                            javascript.text,
                            javascript_url,
                        )

                except requests.RequestException:
                    continue

        return self.routes()

    def _extract_routes(self, content):
        # ----------------------------------------------------
        # 1. Detect apiFetch() template-literal routes first.
        #
        # Examples:
        #   apiFetch(`/api/users/${user.user_id}`)
        #   apiFetch(`/api/orders/${oid}`)
        #
        # These are normalized into canonical API paths.
        # ----------------------------------------------------
        for match in self.APIFETCH_TEMPLATE_PATTERN.findall(content):
            route = self._normalise_route(match)

            if route:
                self.discovered_routes.add(route)

        # ----------------------------------------------------
        # 2. Detect generic API-looking routes.
        # ----------------------------------------------------
        for pattern in self.API_PATTERNS:
            for match in pattern.findall(content):
                route = self._normalise_route(match)

                if route:
                    self.discovered_routes.add(route)

        # ----------------------------------------------------
        # 3. Detect method-specific axios/fetch routes.
        # ----------------------------------------------------
        for method, pattern in self.METHOD_PATTERNS:
            for match in pattern.findall(content):
                route = self._normalise_route(match)

                if route:
                    self.discovered_methods.add(
                        (method, route)
                    )
                    self.discovered_routes.add(route)

        # ----------------------------------------------------
        # 4. Detect generic fetch() calls with explicit methods.
        #
        # Example:
        #   fetch('/api/logout', {
        #       method: 'POST'
        #   })
        #
        # This is target-independent and handles multiline
        # fetch() request options.
        # ----------------------------------------------------
        for match in self.FETCH_METHOD_PATTERN.findall(content):
            route, method = match

            route = self._normalise_route(route)

            if route:
                self.discovered_methods.add(
                    (
                        method.upper(),
                        route,
                    )
                )
                self.discovered_routes.add(route)

        # ----------------------------------------------------
        # 5. Detect apiFetch() calls with explicit methods.
        #
        # Example:
        #   apiFetch('/api/login', {
        #       method: 'POST'
        #   })
        # ----------------------------------------------------
        for match in self.APIFETCH_METHOD_PATTERN.findall(content):
            route, method = match

            route = self._normalise_route(route)

            if route:
                self.discovered_methods.add(
                    (
                        method.upper(),
                        route,
                    )
                )
                self.discovered_routes.add(route)

        return self.routes()

    def _extract_html_routes(self, html):
        """
        Extract API routes from HTML href/action/src attributes.
        """
        attribute_pattern = re.compile(
            r"""(?:href|action|src)=["']([^"']+)["']""",
            re.IGNORECASE,
        )

        for value in attribute_pattern.findall(html):
            route = self._normalise_route(value)

            if route:
                self.discovered_routes.add(route)

    def _discover_common_javascript_urls(self):
        """
        Passively look for common JavaScript asset locations.

        This is useful for API targets whose root endpoint returns JSON
        instead of an HTML page containing <script> tags.
        """
        common_paths = (
            "/main.js",
            "/static/js/app.js",
            "/static/js/main.js",
            "/static/app.js",
            "/static/main.js",
            "/js/app.js",
            "/js/main.js",
        )

        for path in common_paths:
            javascript_url = urljoin(
                self.base_url + "/",
                path.lstrip("/"),
            )

            try:
                response = self.session.get(
                    javascript_url,
                    timeout=self.timeout,
                    verify=self.verify_tls,
                )
            except requests.RequestException:
                continue

            if response.ok:
                content_type = response.headers.get(
                    "Content-Type", ""
                ).lower()

                if (
                    "javascript" in content_type
                    or "ecmascript" in content_type
                    or javascript_url.endswith(".js")
                ):
                    self.javascript_urls.add(javascript_url)

    def _extract_javascript_dependencies(self, javascript, source_url):
        """
        Passively discover RequireJS-style JavaScript module dependencies.

        Examples:
            require(["goatApp/goatApp"])
            define(["goatApp/view/GoatRouter"], ...)
        """

        # Only inspect RequireJS-style dependencies.
        # Modern bundled applications such as Juice Shop contain many
        # unrelated strings with "/" and must not be recursively scanned.
        if not re.search(
            r"\b(?:require|define)\s*\(",
            javascript,
            re.IGNORECASE,
        ):
            return

        module_pattern = re.compile(
            r"""['"]([A-Za-z0-9_./-]+)['"]"""
        )

        source_parsed = urlparse(source_url)

        # RequireJS modules are normally resolved relative to the
        # JavaScript application's module root. For this harness,
        # use the /js/ directory when it is present in the source URL.
        source_path = source_parsed.path
        js_marker = "/js/"

        if js_marker in source_path:
            module_root = (
                source_path.split(js_marker, 1)[0]
                + js_marker
            )
        else:
            module_root = source_path.rsplit("/", 1)[0] + "/"

        for module in module_pattern.findall(javascript):
            if not (
                "/" in module
                and not module.startswith(("http://", "https://"))
                and not module.startswith(("/", "#"))
            ):
                continue

            if module.endswith("/"):
                continue

            if module.endswith((".css", ".html", ".json")):
                continue

            module_path = module
            if not module_path.endswith(".js"):
                module_path += ".js"

            dependency_url = urljoin(
                source_url,
                module_root.split(source_parsed.scheme + "://" + source_parsed.netloc, 1)[-1]
                + module_path,
            )

            dependency_parsed = urlparse(dependency_url)

            if dependency_parsed.netloc == source_parsed.netloc:
                self.javascript_urls.add(dependency_url)

    def _extract_javascript_urls(self, html):
        script_pattern = re.compile(
            r"""<script[^>]+src=["']([^"']+)["']""",
            re.IGNORECASE,
        )

        for source in script_pattern.findall(html):
            javascript_url = urljoin(
                self.base_url + "/",
                source,
            )

            parsed = urlparse(javascript_url)
            base_parsed = urlparse(self.base_url)

            if parsed.netloc == base_parsed.netloc:
                self.javascript_urls.add(
                    javascript_url
                )

    @staticmethod
    def _normalise_route(route):
        route = route.strip()

        if not route:
            return None

        # Convert JavaScript template variables:
        # ${user.user_id} -> {user.user_id}
        route = re.sub(
            r"\$\{([A-Za-z_][A-Za-z0-9_.]*)\}",
            r"{\1}",
            route,
        )

        # Convert absolute URLs to their path.
        parsed = urlparse(route)

        if parsed.scheme and parsed.netloc:
            route = parsed.path

            if parsed.query:
                route += "?" + parsed.query

        if not route.startswith("/"):
            route = "/" + route

        # Canonicalize dynamic resource identifiers.
        #
        # /api/users/{targetId}
        # /api/users/{user.user_id}
        #        -> /api/users/{user_id}
        #
        # /api/orders/{oid}
        # /api/orders/{targetId}
        #        -> /api/orders/{order_id}
        #
        # /api/admin/users/{userId}
        #        -> /api/admin/users/{user_id}

        if re.match(r"^/api/users/\{[^}]+\}$", route):
            route = "/api/users/{user_id}"

        elif re.match(r"^/api/orders/\{[^}]+\}$", route):
            route = "/api/orders/{order_id}"

        elif re.match(r"^/api/admin/users/\{[^}]+\}$", route):
            route = "/api/admin/users/{user_id}"

        # Retain API-looking routes.
        api_exact_routes = {
            "/graphql",
            "/graphql/",
            "/openapi.json",
            "/swagger.json",
        }

        if not (
            route == "/api"
            or route.startswith("/api/")
            or route.startswith("/admin/api/")
            or route.startswith("/v1/")
            or route.startswith("/v2/")
            or route.startswith("/v3/")
            or route.startswith("/service/")
            or route in api_exact_routes
        ):
            return None

        return route

    def routes(self):
        """
        Return discovered API routes as endpoint dictionaries.

        Explicit HTTP methods detected from HTML/JavaScript are
        retained. Generic routes are treated as GET only when
        there is no explicit method information for that route.
        """
        endpoints = set()

        # Keep every explicitly discovered method + route.
        for method, route in self.discovered_methods:
            endpoints.add(
                (
                    method.upper(),
                    route,
                )
            )

        # Routes for which at least one HTTP method was explicitly
        # detected. These must not receive an artificial GET.
        explicit_method_routes = {
            route
            for method, route in self.discovered_methods
        }

        # Generic API routes default to GET only when no explicit
        # HTTP method was discovered for that route.
        for route in self.discovered_routes:
            if route in explicit_method_routes:
                continue

            endpoints.add(
                (
                    "GET",
                    route,
                )
            )

        return [
            {
                "method": method,
                "path": route,
                "security": [],
                "parameters": [],
            }
            for method, route in sorted(endpoints)
        ]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Passively discover API routes from "
            "HTML and JavaScript."
        )
    )

    parser.add_argument(
        "base_url",
        help="Target base URL",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="HTTP request timeout",
    )

    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification",
    )

    args = parser.parse_args()

    discovery = APIRouteDiscovery(
        base_url=args.base_url,
        timeout=args.timeout,
        verify_tls=not args.insecure,
    )

    routes = discovery.discover()

    print()
    print("API Route Discovery")
    print("=" * 60)
    print(
        f"Target : {args.base_url}"
    )
    print(
        f"Routes : {len(routes)}"
    )
    print("=" * 60)
    print()

    for route in routes:
        print(
            f"{route['method']:6} "
            f"{route['path']}"
        )
