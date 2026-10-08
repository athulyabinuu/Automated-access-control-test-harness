import re
from urllib.parse import urljoin, urlparse

import requests


class APIRouteDiscovery:
    """
    Passive API route discovery from:
      - public HTML
      - JavaScript
      - Angular HttpClient calls
      - fetch()
      - axios
      - common API path literals

    No authentication is performed here.
    No state-changing request is sent here.
    """

    HTTP_METHODS = {
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    }

    API_PATH_PATTERN = re.compile(
        r"""["'`]((?:/api|/rest)(?:/[^"'`<>\s]*)?)["'`]""",
        re.IGNORECASE,
    )

    HTTP_CALL_PATTERN = re.compile(
        r"""
        \.
        (get|post|put|patch|delete)
        \s*
        \(
        \s*
        (
            "(?:\\.|[^"])*"
            |
            '(?:\\.|[^'])*'
            |
            `(?:\\.|[^`])*`
            |
            this\.[A-Za-z_$][\w$]*
            (?:\s*\+\s*
                (?:
                    "(?:\\.|[^"])*"
                    |
                    '(?:\\.|[^'])*'
                    |
                    `(?:\\.|[^`])*`
                    |
                    [A-Za-z_$][\w$]*
                )
            )*
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    FETCH_PATTERN = re.compile(
        r"""
        fetch
        \s*
        \(
        \s*
        (["'`])
        (.*?)
        \1
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    AXIOS_PATTERN = re.compile(
        r"""
        axios
        \.
        (get|post|put|patch|delete)
        \s*
        \(
        \s*
        (["'`])
        (.*?)
        \2
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    HOST_ASSIGNMENT_PATTERN = re.compile(
        r"""
        \b
        (?:this\.)?
        host
        \s*=\s*
        (
            (?:"[^"]*"|'[^']*')
            |
            this\.hostServer\s*\+\s*(?:"[^"]*"|'[^']*')
            |
            `[^`]*`
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    HOSTSERVER_ASSIGNMENT_PATTERN = re.compile(
        r"""
        \b
        (?:this\.)?
        hostServer
        \s*=\s*
        (
            (?:"[^"]*"|'[^']*')
            |
            `[^`]*`
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    def __init__(self, base_url, timeout=10, session=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        # Reuse the authenticated/session object supplied by the
        # orchestrator when available. Discovery itself remains
        # passive; it only performs GET requests.
        self.session = session or requests.Session()

    # ---------------------------------------------------------
    # Public discovery
    # ---------------------------------------------------------

    def discover(self):
        """
        Discover routes from the target's public HTML and JavaScript.

        The rest of the harness expects endpoint dictionaries:

            {
                "method": "GET",
                "path": "/api/products"
            }

        Deduplication is therefore performed using (method, path)
        keys rather than storing dictionaries in a set.
        """
        endpoints = {}

        try:
            response = self.session.get(
                self.base_url,
                timeout=self.timeout,
                allow_redirects=True,
            )

            if response.ok:
                html = response.text

                # HTML routes are GET candidates.
                for endpoint in self._extract_html_routes(html):
                    key = (
                        endpoint["method"],
                        endpoint["path"],
                    )
                    endpoints[key] = endpoint

                script_urls = self._extract_script_urls(
                    html,
                    response.url,
                )

                for script_url in script_urls:
                    try:
                        js_response = self.session.get(
                            script_url,
                            timeout=self.timeout,
                        )

                        if js_response.ok:
                            discovered = (
                                self._extract_javascript_routes(
                                    js_response.text
                                )
                            )

                            for endpoint in discovered:
                                key = (
                                    endpoint["method"],
                                    endpoint["path"],
                                )
                                endpoints[key] = endpoint

                    except requests.RequestException:
                        continue

        except requests.RequestException:
            pass

        return [
            endpoints[key]
            for key in sorted(endpoints)
        ]

    # ---------------------------------------------------------
    # HTML
    # ---------------------------------------------------------

    def _extract_html_routes(self, content):
        routes = set()

        for match in self.API_PATH_PATTERN.finditer(content):
            path = self._clean_path(match.group(1))

            if path:
                routes.add(("GET", path))

        return routes

    def _extract_script_urls(self, html, page_url):
        urls = set()

        pattern = re.compile(
            r"""<script[^>]+src\s*=\s*["']([^"']+)["']""",
            re.IGNORECASE,
        )

        for match in pattern.finditer(html):
            src = match.group(1)

            if src.startswith("data:"):
                continue

            urls.add(urljoin(page_url, src))

        return urls

    # ---------------------------------------------------------
    # JavaScript
    # ---------------------------------------------------------

    def _extract_javascript_routes(self, content):
        """
        Extract HTTP methods and routes from JavaScript.

        The important part here is that host variables are resolved
        locally near each HTTP call instead of using one global
        host value for the entire minified bundle.
        """
        routes = set()

        # -----------------------------------------------------
        # Angular HttpClient:
        #
        # this.http.get("/rest/products")
        # this.http.post("/rest/login", data)
        # this.http.put(this.host + "/123", data)
        # this.http.delete(`${this.host}/${id}`)
        # -----------------------------------------------------
        for match in self.HTTP_CALL_PATTERN.finditer(content):
            method = match.group(1).upper()
            expression = match.group(2).strip()

            path = self._resolve_expression_near_call(
                expression,
                content,
                match.start(),
            )

            if path:
                routes.add((method, path))

        # -----------------------------------------------------
        # axios:
        #
        # axios.get("/api/users")
        # axios.post("/api/login", data)
        # -----------------------------------------------------
        for match in self.AXIOS_PATTERN.finditer(content):
            method = match.group(1).upper()
            expression = match.group(3).strip()

            path = self._resolve_expression_near_call(
                expression,
                content,
                match.start(),
            )

            if path:
                routes.add((method, path))

        # -----------------------------------------------------
        # fetch():
        #
        # fetch("/api/products")
        #
        # With no explicit method, GET is the passive assumption.
        # -----------------------------------------------------
        for match in self.FETCH_PATTERN.finditer(content):
            expression = match.group(2).strip()

            path = self._resolve_expression_near_call(
                expression,
                content,
                match.start(),
            )

            if path:
                routes.add(("GET", path))

        # -----------------------------------------------------
        # Literal API paths.
        #
        # Only add GET if that exact path was not already found
        # with an explicit HTTP method.
        # -----------------------------------------------------
        explicit_paths = {
            path
            for _, path in routes
        }

        for match in self.API_PATH_PATTERN.finditer(content):
            path = self._clean_path(match.group(1))

            if path and path not in explicit_paths:
                routes.add(("GET", path))

        # The rest of the harness expects endpoint records
        # to be dictionaries, not (method, path) tuples.
        #
        # Keep discovery target-independent while preserving
        # compatibility with the existing authorization and
        # test-generation pipeline.
        return [
            {
                "method": method,
                "path": path,
            }
            for method, path in sorted(routes)
        ]

    def _resolve_expression_near_call(
        self,
        expression,
        content,
        position,
    ):
        expression = expression.strip()

        # -----------------------------------------------------
        # Direct string
        # -----------------------------------------------------
        if self._is_literal(expression):
            return self._clean_path(
                self._strip_quotes(expression)
            )

        # -----------------------------------------------------
        # Template literal
        # -----------------------------------------------------
        if expression.startswith("`") and expression.endswith("`"):
            return self._resolve_template_near_call(
                expression[1:-1],
                content,
                position,
            )

        # -----------------------------------------------------
        # this.host
        # -----------------------------------------------------
        if re.fullmatch(
            r"(?:this\.)?host",
            expression,
        ):
            host = self._find_nearest_host_assignment(
                content,
                position,
            )

            if host:
                return self._clean_path(host)

            return None

        # -----------------------------------------------------
        # this.host + "/something"
        # -----------------------------------------------------
        match = re.match(
            r"""
            (?:this\.)?host
            \s*\+\s*
            ["']([^"']*)["']
            """,
            expression,
            re.IGNORECASE | re.VERBOSE,
        )

        if match:
            suffix = match.group(1)

            host = self._find_nearest_host_assignment(
                content,
                position,
            )

            if host:
                return self._clean_path(
                    host.rstrip("/") +
                    "/" +
                    suffix.lstrip("/")
                )

            return self._clean_path(suffix)

        # -----------------------------------------------------
        # this.host + `/${id}`
        # -----------------------------------------------------
        match = re.match(
            r"""
            (?:this\.)?host
            \s*\+\s*
            `([^`]*)`
            """,
            expression,
            re.IGNORECASE | re.VERBOSE,
        )

        if match:
            suffix = self._replace_js_variables(
                match.group(1)
            )

            host = self._find_nearest_host_assignment(
                content,
                position,
            )

            if host:
                return self._clean_path(
                    host.rstrip("/") +
                    "/" +
                    suffix.lstrip("/")
                )

            return self._clean_path(suffix)

        # -----------------------------------------------------
        # this.hostServer + "/rest/..."
        # -----------------------------------------------------
        match = re.match(
            r"""
            (?:this\.)?hostServer
            \s*\+\s*
            ["']([^"']*)["']
            """,
            expression,
            re.IGNORECASE | re.VERBOSE,
        )

        if match:
            return self._clean_path(
                match.group(1)
            )

        return None

    def _find_nearest_host_assignment(
        self,
        content,
        position,
    ):
        """
        Find the closest preceding host assignment.

        We intentionally use a bounded local window instead of
        maintaining one global `host` variable.

        Example:

            host=this.hostServer+"/rest/products";
            get(e) {
                return this.http.get(`${this.host}/${e}`);
            }

        resolves to:

            /rest/products/{param}

        while a later:

            host=this.hostServer+"/rest/chat";

        does not overwrite the previous service.
        """

        WINDOW = 12000

        start = max(
            0,
            position - WINDOW,
        )

        section = content[start:position]

        matches = list(
            self.HOST_ASSIGNMENT_PATTERN.finditer(
                section
            )
        )

        if not matches:
            return None

        match = matches[-1]

        expression = match.group(1).strip()

        # -----------------------------------------------------
        # host="/rest/products"
        # -----------------------------------------------------
        if self._is_literal(expression):
            return self._strip_quotes(expression)

        # -----------------------------------------------------
        # host=this.hostServer+"/rest/products"
        # -----------------------------------------------------
        combined = re.match(
            r"""
            this\.hostServer
            \s*\+\s*
            ["']([^"']*)["']
            """,
            expression,
            re.IGNORECASE | re.VERBOSE,
        )

        if combined:
            return combined.group(1)

        return None

    def _resolve_template_near_call(
        self,
        template,
        content,
        position,
    ):
        result = template

        host = self._find_nearest_host_assignment(
            content,
            position,
        )

        # -----------------------------------------------------
        # ${this.host}
        # -----------------------------------------------------
        if host:
            result = re.sub(
                r"\$\{\s*this\.host\s*\}",
                host,
                result,
            )

        # -----------------------------------------------------
        # ${this.hostServer}
        #
        # We only need the route portion because hostServer
        # normally represents the target origin.
        # -----------------------------------------------------
        result = re.sub(
            r"\$\{\s*this\.hostServer\s*\}",
            "",
            result,
        )

        # -----------------------------------------------------
        # ${someVariable}
        # -> {param}
        # -----------------------------------------------------
        result = re.sub(
            r"\$\{\s*[^}]+\s*\}",
            "{param}",
            result,
        )

        if host and result.startswith("/"):
            return self._clean_path(result)

        # Direct template such as:
        #
        # `${this.hostServer}/rest/languages`
        #
        if result.startswith("/"):
            return self._clean_path(result)

        return None

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _is_literal(value):
        if len(value) < 2:
            return False

        return (
            value[0] == value[-1]
            and value[0] in {"'", '"'}
        )

    @staticmethod
    def _strip_quotes(value):
        if len(value) >= 2 and value[0] == value[-1]:
            if value[0] in {"'", '"', "`"}:
                return value[1:-1]

        return value

    @staticmethod
    def _replace_js_variables(value):
        return re.sub(
            r"\$\{\s*[^}]+\s*\}",
            "{param}",
            value,
        )

    @staticmethod
    def _clean_path(path):
        if not path:
            return None

        path = path.strip()

        # Remove surrounding quotes/backticks.
        path = path.strip("\"'`")

        # Handle absolute URLs.
        parsed = urlparse(path)

        if parsed.scheme in {"http", "https"}:
            path = parsed.path

            if parsed.query:
                path += "?" + parsed.query

        # Remove accidental whitespace.
        path = re.sub(
            r"\s+",
            "",
            path,
        )

        # Static JavaScript can produce:
        #
        # ?email=
        # ?q=
        #
        # Replace the unknown value with a safe placeholder.
        path = re.sub(
            r"=(&|$)",
            r"={param}\1",
            path,
        )

        # Must be an application-relative path.
        if not path.startswith("/"):
            return None

        # Collapse duplicate slashes.
        path = re.sub(
            r"/{2,}",
            "/",
            path,
        )

        # Remove accidental semicolon at the end.
        path = path.rstrip(";")

        return path
