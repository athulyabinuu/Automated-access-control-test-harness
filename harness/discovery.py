from pathlib import Path

from harness.openapi_parser import parse_openapi


class EndpointDiscovery:
    """
    Discovers API endpoints from an OpenAPI specification.

    This module is target-independent. It does not know about
    Target 1, Target 2, or any specific application.
    """

    def __init__(self, openapi_file):
        self.openapi_file = Path(openapi_file)
        self.spec = None

    def discover(self):
        if not self.openapi_file.exists():
            raise FileNotFoundError(
                f"OpenAPI specification not found: "
                f"{self.openapi_file}"
            )

        self.spec = parse_openapi(
            str(self.openapi_file)
        )

        return self.spec

    def endpoints(self):
        if self.spec is None:
            self.discover()

        return self.spec.get(
            "endpoints",
            []
        )

    def security_schemes(self):
        if self.spec is None:
            self.discover()

        return self.spec.get(
            "security_schemes",
            {}
        )

    def summary(self):
        if self.spec is None:
            self.discover()

        endpoints = self.endpoints()

        return {
            "openapi_version": self.spec.get(
                "openapi_version"
            ),
            "title": self.spec.get(
                "title"
            ),
            "version": self.spec.get(
                "version"
            ),
            "endpoint_count": len(endpoints),
            "security_scheme_count": len(
                self.security_schemes()
            ),
        }


def discover_remote_openapi(
    base_url,
    timeout=5,
    verify_tls=True,
):
    """
    Automatically searches common public locations for an
    OpenAPI/Swagger specification.

    This is target-independent. It does not assume any
    application-specific endpoint names.
    """
    import json

    import requests
    import yaml

    base_url = base_url.rstrip("/")

    candidates = [
        "/openapi.json",
        "/openapi.yaml",
        "/openapi.yml",
        "/swagger.json",
        "/swagger.yaml",
        "/swagger.yml",
        "/api/openapi.json",
        "/api/openapi.yaml",
        "/api/openapi.yml",
        "/api/swagger.json",
        "/api/swagger.yaml",
        "/api/swagger.yml",
        "/v3/api-docs",
        "/api-docs",
    ]

    for path in candidates:
        url = f"{base_url}{path}"

        try:
            response = requests.get(
                url,
                timeout=timeout,
                verify=verify_tls,
                allow_redirects=True,
            )
        except requests.RequestException:
            continue

        if response.status_code != 200:
            continue

        content = response.text.strip()

        if not content:
            continue

        spec = None

        # Try JSON first.
        try:
            spec = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            pass

        # Then try YAML.
        if spec is None:
            try:
                spec = yaml.safe_load(content)
            except yaml.YAMLError:
                continue

        if not isinstance(spec, dict):
            continue

        # A valid OpenAPI/Swagger document should contain
        # an OpenAPI/Swagger version and a paths object.
        if not (
            spec.get("openapi")
            or spec.get("swagger")
        ):
            continue

        if not isinstance(
            spec.get("paths"),
            dict,
        ):
            continue

        return {
            "url": url,
            "spec": spec,
            "content": content,
        }

    return None


def discover_openapi(openapi_file):
    """
    Convenience function for the harness.
    """
    discovery = EndpointDiscovery(
        openapi_file
    )

    return discovery.discover()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Discover endpoints from an "
            "OpenAPI specification."
        )
    )

    parser.add_argument(
        "openapi_file",
        help="Path to OpenAPI YAML/JSON file",
    )

    args = parser.parse_args()

    discovery = EndpointDiscovery(
        args.openapi_file
    )

    summary = discovery.summary()

    print()
    print("OpenAPI Discovery")
    print("=" * 60)
    print(
        f"Title     : {summary['title']}"
    )
    print(
        f"Version   : {summary['version']}"
    )
    print(
        f"OpenAPI   : {summary['openapi_version']}"
    )
    print(
        f"Endpoints : {summary['endpoint_count']}"
    )
    print(
        f"Security  : {summary['security_scheme_count']}"
    )
    print("=" * 60)

    print()

    for endpoint in discovery.endpoints():
        print(
            f"{endpoint['method']:6} "
            f"{endpoint['path']}"
        )

        if endpoint.get("summary"):
            print(
                f"       {endpoint['summary']}"
            )

        for parameter in endpoint.get(
            "parameters",
            []
        ):
            print(
                f"       parameter: "
                f"{parameter['name']} "
                f"({parameter['in']})"
            )

        print()
