import base64
import binascii
import json
import re

import requests


class ResourceDiscovery:
    """
    Discover resource identifiers from authenticated API responses.

    Resource discovery is target-independent. It uses the discovered
    endpoint inventory to identify collection/item endpoint pairs such as:

        GET /api/documents
        GET /api/documents/{doc_id}

    Collection responses are inspected generically for resource objects
    containing an ``id`` field.

    Conventional /api/me and /api/admin/users discovery is retained as
    a backward-compatible fallback for targets that expose those routes.
    """

    PATH_PARAMETER_PATTERN = re.compile(
        r"\{([^{}]+)\}"
    )

    def __init__(
        self,
        target,
        accounts,
        authentications,
        endpoints=None,
        timeout=5,
        verify_tls=True,
    ):
        self.target = target
        self.accounts = accounts
        self.authentications = authentications
        self.endpoints = endpoints or []
        self.timeout = timeout
        self.verify_tls = verify_tls
        self.ownership_evidence = {}

    # ========================================================
    # MAIN DISCOVERY
    # ========================================================

    def discover(self):
        resources = {}

        # Preserve the existing generic user discovery.
        user_resources = self._discover_user_ids()

        if user_resources:
            resources["user"] = user_resources

        # Discover resources from the endpoint inventory.
        discovered_resources = (
            self._discover_collection_resources()
        )

        for resource_type, resource_data in (
            discovered_resources.items()
        ):
            if resource_type == "user":
                # Merge newly discovered user IDs with the
                # conventional user discovery result.
                resources["user"] = self._merge_resource_data(
                    resources.get("user", {}),
                    resource_data,
                )
            else:
                resources[resource_type] = resource_data

        # JWT resource discovery is only a fallback for resources
        # that normal collection discovery could not identify.
        jwt_resources = (
            self._discover_jwt_claim_resources(
                existing_resources=resources
            )
        )

        for resource_type, resource_data in (
            jwt_resources.items()
        ):
            if resource_type in resources:
                continue

            resources[resource_type] = resource_data

        return resources

    # ========================================================
    # COLLECTION-BASED RESOURCE DISCOVERY
    # ========================================================

    def _discover_collection_resources(self):
        """
        Discover resource IDs from collection endpoints.

        Example:

            GET /api/documents
            GET /api/documents/{doc_id}

        produces:

            {
                "document": {
                    "admin": {
                        "own": "1",
                        "other": "2"
                    },
                    "user": {
                        "own": "2",
                        "other": "1"
                    }
                }
            }
        """

        item_endpoints = []

        for endpoint in self.endpoints:
            if not isinstance(endpoint, dict):
                continue

            method = str(
                endpoint.get("method", "GET")
            ).upper()

            path = str(
                endpoint.get("path", "")
            )

            if method != "GET":
                continue

            parameter_names = (
                self.PATH_PARAMETER_PATTERN.findall(
                    path
                )
            )

            if not parameter_names:
                continue

            collection_path = (
                self._collection_path(path)
            )

            if not collection_path:
                continue

            resource_type = (
                self._infer_resource_type(
                    path,
                    parameter_names,
                )
            )

            if not resource_type:
                continue

            item_endpoints.append(
                (
                    resource_type,
                    collection_path,
                )
            )

        if not item_endpoints:
            return {}

        collection_endpoints = {
            (
                str(endpoint.get("method", "GET")).upper(),
                str(endpoint.get("path", "")),
            )
            for endpoint in self.endpoints
            if isinstance(endpoint, dict)
        }

        resources = {}

        for resource_type, collection_path in sorted(
            set(item_endpoints)
        ):

            if (
                "GET",
                collection_path,
            ) not in collection_endpoints:
                continue

            role_ids = {}

            for role in self.accounts:
                authentication = (
                    self.authentications.get(role)
                )

                if (
                    not authentication
                    or not authentication.success
                ):
                    continue

                session = (
                    self._create_authenticated_session(
                        authentication
                    )
                )

                response_data = (
                    self._get_json_collection(
                        session,
                        collection_path,
                    )
                )

                ids = self._extract_resource_ids(
                    response_data
                )

                if not ids:
                    continue

                role_ids[role] = {
                    "ids": ids,
                }

            if not role_ids:
                continue

            resource_data = (
                self._build_role_resource_data(
                    role_ids
                )
            )

            if resource_data:
                resources[resource_type] = (
                    resource_data
                )

        return resources

    # ========================================================
    # COLLECTION PATH
    # ========================================================

    def _collection_path(self, path):
        """
        Convert an item endpoint into its collection endpoint.

        Example:

            /api/documents/{doc_id}
                ->
            /api/documents
        """

        match = self.PATH_PARAMETER_PATTERN.search(
            path
        )

        if not match:
            return None

        collection = (
            path[:match.start()]
            + path[match.end():]
        )

        collection = collection.rstrip("/")

        if not collection:
            return None

        # Only accept a collection path where the
        # parameter was the final path component.
        if "{" in collection or "}" in collection:
            return None

        return collection

    # ========================================================
    # RESOURCE TYPE
    # ========================================================

    @staticmethod
    def _infer_resource_type(
        path,
        parameter_names,
    ):
        """
        Infer a resource name from the path parameter.

        Examples:

            doc_id      -> document
            order_id    -> order
            user_id     -> user
            documentId  -> document
        """

        if not parameter_names:
            return None

        parameter = (
            parameter_names[-1]
            .strip()
            .lower()
        )

        candidates = []

        if parameter.endswith("_id"):
            candidates.append(
                parameter[:-3]
            )

        if parameter.endswith("id"):
            candidates.append(
                parameter[:-2].rstrip("_")
            )

        for candidate in candidates:
            candidate = candidate.strip(
                "_/- "
            )

            if candidate:
                return (
                    ResourceDiscovery._singularize(
                        candidate
                    )
                )

        # Fallback to the final collection path.
        path_without_parameter = (
            ResourceDiscovery.PATH_PARAMETER_PATTERN
            .sub("", path)
            .rstrip("/")
        )

        segment = (
            path_without_parameter
            .split("/")[-1]
            .strip()
            .lower()
        )

        if segment:
            return (
                ResourceDiscovery._singularize(
                    segment
                )
            )

        return None

    @staticmethod
    def _singularize(value):
        """
        Small, conservative singularization helper.

        This is intentionally simple because resource names are
        primarily derived from explicit path parameter names.
        """

        if value.endswith("ies"):
            return value[:-3] + "y"

        if value.endswith("ses"):
            return value[:-2]

        if value.endswith("s") and not value.endswith(
            "ss"
        ):
            return value[:-1]

        return value

    # ========================================================
    # COLLECTION REQUEST
    # ========================================================

    def _get_json_collection(
        self,
        session,
        path,
    ):
        try:
            response = session.get(
                self.target.base_url + path,
                timeout=self.timeout,
                verify=self.verify_tls,
                allow_redirects=False,
            )
        except requests.RequestException:
            return None

        if response.status_code != 200:
            return None

        try:
            return response.json()
        except ValueError:
            return None

    # ========================================================
    # ID EXTRACTION
    # ========================================================

    def _extract_resource_ids(self, data):
        """
        Recursively extract IDs from JSON responses.

        Supported examples:

            [
                {"id": 1},
                {"id": 2}
            ]

            {
                "documents": [
                    {"id": 1},
                    {"id": 2}
                ]
            }

            {
                "data": {
                    "items": [
                        {"id": 1}
                    ]
                }
            }
        """

        found = []

        def walk(value):
            if isinstance(value, dict):

                if value.get("id") is not None:
                    found.append(
                        str(value["id"])
                    )

                for child in value.values():
                    walk(child)

            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(data)

        # Preserve order while removing duplicates.
        unique = []

        for value in found:
            if value not in unique:
                unique.append(value)

        return unique

    # ========================================================
    # ROLE RESOURCE DATA
    # ========================================================

    @staticmethod
    def _build_role_resource_data(
        role_ids
    ):
        """
        Convert discovered IDs into the resource structure
        already understood by execution.py.

        When multiple IDs are available:

            own   = first ID visible to the role
            other = another ID

        This is a discovery fallback, not a claim that the first
        resource is semantically owned by the authenticated user.
        """

        result = {}

        all_ids = []

        for role_data in role_ids.values():
            for resource_id in role_data.get(
                "ids",
                [],
            ):
                if resource_id not in all_ids:
                    all_ids.append(resource_id)

        for role, role_data in role_ids.items():

            ids = role_data.get(
                "ids",
                []
            )

            if not ids:
                continue

            own = ids[0]

            other = None

            for candidate in all_ids:
                if candidate != own:
                    other = candidate
                    break

            result[role] = {
                "own": own,
            }

            if other is not None:
                result[role]["other"] = other

            another = None

            for candidate in all_ids:
                if candidate != own and candidate != other:
                    another = candidate
                    break

            if another is not None:
                result[role]["another"] = another

        return result

    # ========================================================
    # JWT CLAIM RESOURCE DISCOVERY
    # ========================================================

    def _discover_jwt_claim_resources(
        self,
        existing_resources=None,
    ):
        """
        Fallback resource discovery using authenticated JWT claims.

        This does not replace collection-based discovery.

        Example:

            GET /rest/basket/{param}

        with JWT:

            {"bid": 6}

        produces an ownership mapping for the basket resource.

        Ownership evidence is kept separately so a vulnerable
        HTTP 200 cannot become an expected "any" permission.
        """

        existing_resources = (
            existing_resources or {}
        )

        discovered = {}

        candidate_endpoints = []

        for endpoint in self.endpoints:

            if not isinstance(endpoint, dict):
                continue

            method = str(
                endpoint.get("method", "GET")
            ).upper()

            path = str(
                endpoint.get("path", "")
            )

            if method != "GET":
                continue

            parameter_names = (
                self.PATH_PARAMETER_PATTERN.findall(
                    path
                )
            )

            if not parameter_names:
                continue

            resource_type = (
                self._resource_type_from_path(path)
            )

            if not resource_type:
                continue

            # Existing discovery always wins.
            if resource_type in existing_resources:
                continue

            candidate_endpoints.append(
                (
                    resource_type,
                    parameter_names[0],
                )
            )

        if not candidate_endpoints:
            return {}

        resource_types = sorted(
            {
                resource_type
                for resource_type, _ in candidate_endpoints
            }
        )

        for resource_type in resource_types:

            role_resources = {}

            for role in self.accounts:

                authentication = (
                    self.authentications.get(role)
                )

                if (
                    not authentication
                    or not authentication.success
                ):
                    continue

                token = getattr(
                    authentication,
                    "token",
                    None,
                )

                if not token:
                    continue

                claims = (
                    self._decode_jwt_claims(token)
                )

                if not claims:
                    continue

                resource_id = (
                    self._jwt_resource_id(
                        claims,
                        resource_type,
                    )
                )

                if resource_id is None:
                    continue

                role_resources[role] = {
                    "own": str(resource_id)
                }

            # At least two authenticated roles with different
            # resource IDs are required before ownership is claimed.
            if len(role_resources) < 2:
                continue

            all_ids = []

            for role_data in role_resources.values():

                value = role_data.get("own")

                if (
                    value is not None
                    and value not in all_ids
                ):
                    all_ids.append(value)

            if len(all_ids) < 2:
                continue

            for role, role_data in role_resources.items():

                own = role_data["own"]

                other = next(
                    (
                        value
                        for value in all_ids
                        if value != own
                    ),
                    None,
                )

                if other is not None:
                    role_data["other"] = other

            discovered[resource_type] = role_resources

            self.ownership_evidence[
                resource_type
            ] = {
                "source": "jwt_claim",
                "roles": {
                    role: dict(data)
                    for role, data
                    in role_resources.items()
                },
            }

        return discovered

    @staticmethod
    def _resource_type_from_path(path):

        parts = [
            part.strip()
            for part in str(path).split("/")
            if part.strip()
        ]

        for index, part in enumerate(parts):

            if not ResourceDiscovery.PATH_PARAMETER_PATTERN.fullmatch(
                part
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

    @staticmethod
    def _decode_jwt_claims(token):

        try:

            token = str(token).strip()

            if token.lower().startswith(
                "bearer "
            ):
                token = token[7:].strip()

            parts = token.split(".")

            if len(parts) != 3:
                return None

            payload = parts[1]

            padding = "=" * (
                (-len(payload)) % 4
            )

            decoded = (
                base64.urlsafe_b64decode(
                    (
                        payload + padding
                    ).encode("ascii")
                )
            )

            claims = json.loads(
                decoded.decode("utf-8")
            )

            if isinstance(claims, dict):
                return claims

        except (
            ValueError,
            TypeError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            binascii.Error,
        ):
            pass

        return None

    @staticmethod
    def _jwt_resource_id(
        claims,
        resource_type,
    ):

        normalized = (
            str(resource_type)
            .strip()
            .lower()
        )

        candidates = [
            f"{normalized}_id",
            f"{normalized}id",
        ]

        # Juice Shop uses the compact "bid" claim specifically
        # for the basket resource.
        #
        # Do NOT apply a generic first-letter rule here.
        # For example:
        #   basket     -> bid
        #   basketitem -> bid  <-- incorrect
        #
        # A generic rule would cause basket ownership IDs to be
        # incorrectly reused as BasketItem IDs.
        if normalized == "basket":
            candidates.append("bid")

        for candidate in candidates:

            for actual_key, value in (
                claims.items()
            ):

                if (
                    str(actual_key)
                    .strip()
                    .lower()
                    == candidate
                ):

                    if isinstance(
                        value,
                        (str, int),
                    ) and str(value).strip():

                        return value

        return None

    # ========================================================
    # RESOURCE MERGING
    # ========================================================

    @staticmethod
    def _merge_resource_data(
        existing,
        discovered,
    ):
        """
        Merge two role-based resource maps without destroying
        explicitly discovered values.
        """

        merged = {}

        for role, role_data in existing.items():
            if isinstance(role_data, dict):
                merged[role] = dict(role_data)

        for role, role_data in discovered.items():

            if role not in merged:
                merged[role] = {}

            if isinstance(role_data, dict):
                for key, value in role_data.items():
                    if value is not None:
                        merged[role][key] = value

        return merged

    # ========================================================
    # USER RESOURCE DISCOVERY
    # ========================================================

    def _discover_user_ids(self):
        """
        Discover user IDs from conventional authenticated
        endpoints when available.

        These endpoints are optional. Failure simply means that
        this particular discovery method is unavailable.
        """

        discovered = {
            "all": set(),
            "by_role": {},
        }

        for role, account in self.accounts.items():

            authentication = (
                self.authentications.get(role)
            )

            if (
                not authentication
                or not authentication.success
            ):
                continue

            session = (
                self._create_authenticated_session(
                    authentication
                )
            )

            if session is None:
                continue

            own_id = self._get_current_user_id(
                session
            )

            if own_id is not None:

                discovered["all"].add(
                    str(own_id)
                )

                discovered["by_role"].setdefault(
                    role,
                    {},
                )["own"] = str(own_id)

            user_list = self._get_admin_user_ids(
                session
            )

            for user_id in user_list:

                if user_id is None:
                    continue

                discovered["all"].add(
                    str(user_id)
                )

        all_ids = sorted(
            discovered["all"],
            key=lambda value: (
                int(value)
                if value.isdigit()
                else value
            ),
        )

        for role, role_data in discovered[
            "by_role"
        ].items():

            own_id = role_data.get("own")

            if not own_id:
                continue

            other_ids = [
                value
                for value in all_ids
                if value != own_id
            ]

            if other_ids:
                role_data["other"] = (
                    other_ids[0]
                )

        return discovered["by_role"]

    # ========================================================
    # AUTHENTICATED SESSION
    # ========================================================

    def _create_authenticated_session(
        self,
        authentication,
    ):
        session = requests.Session()

        session.headers.update({
            "User-Agent": (
                "Access-Control-Test-Harness/"
                "ResourceDiscovery"
            )
        })

        if authentication.cookies:
            session.cookies.update(
                authentication.cookies
            )

        if authentication.token:
            session.headers.update({
                "Authorization": (
                    f"Bearer "
                    f"{authentication.token}"
                )
            })

        return session

    # ========================================================
    # CURRENT USER
    # ========================================================

    def _get_current_user_id(
        self,
        session,
    ):
        try:
            response = session.get(
                self.target.base_url + "/api/me",
                timeout=self.timeout,
                verify=self.verify_tls,
                allow_redirects=False,
            )
        except requests.RequestException:
            return None

        if response.status_code != 200:
            return None

        try:
            data = response.json()
        except ValueError:
            return None

        if isinstance(data, dict):

            if data.get("id") is not None:
                return data["id"]

            user = data.get("user")

            if isinstance(user, dict):
                return user.get("id")

        return None

    # ========================================================
    # ADMIN USER LIST
    # ========================================================

    def _get_admin_user_ids(
        self,
        session,
    ):
        try:
            response = session.get(
                self.target.base_url
                + "/api/admin/users",
                timeout=self.timeout,
                verify=self.verify_tls,
                allow_redirects=False,
            )
        except requests.RequestException:
            return []

        if response.status_code != 200:
            return []

        try:
            data = response.json()
        except ValueError:
            return []

        if isinstance(data, list):
            users = data

        elif isinstance(data, dict):
            users = data.get(
                "users",
                [],
            )

        else:
            return []

        if not isinstance(users, list):
            return []

        return [
            user.get("id")
            for user in users
            if (
                isinstance(user, dict)
                and user.get("id") is not None
            )
        ]
