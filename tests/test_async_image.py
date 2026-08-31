from aui import AsyncImage, AsyncImagePhase, Size, describe_accessibility
from aui.backends.ascii import AsciiBackend


def setup_function():
    AsyncImage.clear_cache()


def test_async_image_success_phase_listener_and_cache():
    calls = []
    phases = []
    image = AsyncImage(
        "https://example.test/image.png",
        loader=lambda url: calls.append(url) or b"image-data",
    )
    cancel = image.subscribe(phases.append)

    phase = image.load()
    cancel()
    assert phase == AsyncImagePhase(AsyncImagePhase.SUCCESS, b"image-data")
    assert phase.is_success and not phase.is_empty
    assert phases == [phase]
    assert calls == ["https://example.test/image.png"]

    cached = AsyncImage("https://example.test/image.png", loader=lambda url: b"other")
    assert cached.phase.data == b"image-data"


def test_async_image_failure_is_a_phase_not_an_exception():
    def failing(url):
        raise OSError("offline")

    image = AsyncImage("https://example.test/missing.png", loader=failing)
    phase = image.load()

    assert phase.is_failure
    assert isinstance(phase.error, OSError)
    assert "offline" in str(phase.error)


def test_async_image_validates_loader_data_and_url():
    image = AsyncImage("https://example.test/empty.png", loader=lambda url: b"")
    assert image.load().is_failure

    try:
        AsyncImage("")
    except ValueError as exc:
        assert "cannot be empty" in str(exc)
    else:
        raise AssertionError("empty URL must fail")


def test_async_image_layout_ascii_and_accessibility_phases():
    image = AsyncImage("memory://image", size=Size(240, 135), loader=lambda url: b"png")

    assert image.size_that_fits(Size(500, 500)) == Size(240, 135)
    assert "loading" in AsciiBackend(width=30, height=2).render(image)
    image.load()
    assert "(image)" in AsciiBackend(width=30, height=2).render(image)
    assert describe_accessibility(image).role == "image"


def test_async_image_cache_can_clear_one_url():
    first = AsyncImage("memory://one", loader=lambda url: b"one")
    second = AsyncImage("memory://two", loader=lambda url: b"two")
    first.load()
    second.load()
    AsyncImage.clear_cache("memory://one")

    assert AsyncImage("memory://one", loader=lambda url: b"new").phase.is_empty
    assert AsyncImage("memory://two", loader=lambda url: b"new").phase.data == b"two"
