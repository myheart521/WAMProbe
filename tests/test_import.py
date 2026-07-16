import wamprobe


def test_version_is_exposed() -> None:
    assert wamprobe.__version__ == "0.1.0"
