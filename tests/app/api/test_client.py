class TestClient:
    """
    A minimal client for testing Inty APIs.

    It's not auto-generated from OpenAPI spec, but hand rolled, as we do not need
    complex features.

    These api will use the same internal data structure for convenience,
    but access Inty backend API through HTTP interface.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url

    def create_guest(self):
        pass
