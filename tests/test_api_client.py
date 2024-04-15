from sam.contrib import brave


def test_get_client():
    with brave.get_client() as api:
        assert api.search("test")
