from pathlib import Path

import numpy as np
from PySide6.QtGui import QImage

from woodcut_duotone.io import bgr_to_rgb, load_image, rgb_to_bgr, rgb_to_qimage, save_image


def _fixture_path() -> Path:
    return Path(__file__).parent / "fixtures" / "images" / "test_8x8.png"


def _expected_color(x: int, y: int) -> np.ndarray:
    return np.array([(x * 32) % 256, (y * 32) % 256, ((x + y) * 16) % 256], dtype=np.uint8)


def test_load_image_returns_rgb_uint8() -> None:
    image = load_image(str(_fixture_path()))

    assert image.dtype == np.uint8
    assert image.shape == (8, 8, 3)
    assert np.array_equal(image[2, 3], _expected_color(3, 2))


def test_save_image_roundtrip(tmp_path: Path) -> None:
    image = load_image(str(_fixture_path()))
    out_path = tmp_path / "roundtrip.png"

    save_image(str(out_path), image)

    reloaded = load_image(str(out_path))
    assert np.array_equal(image, reloaded)


def test_rgb_bgr_roundtrip() -> None:
    image = np.array([[[1, 2, 3], [10, 20, 30]]], dtype=np.uint8)

    bgr = rgb_to_bgr(image)
    rgb = bgr_to_rgb(bgr)

    assert np.array_equal(rgb, image)


def test_rgb_to_qimage_properties() -> None:
    image = np.zeros((5, 7, 3), dtype=np.uint8)

    qimage = rgb_to_qimage(image)

    assert isinstance(qimage, QImage)
    assert not qimage.isNull()
    assert qimage.width() == 7
    assert qimage.height() == 5
    assert qimage.format() == QImage.Format.Format_RGB888
