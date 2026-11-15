"""Load and display the bundled parking-camera annotations."""

from functools import lru_cache
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import pandas as pd
from PIL import Image, ImageDraw


DATASET_DIR = Path(__file__).parent / "data" / "parking new "
ANNOTATIONS_PATH = DATASET_DIR / "annotations.xml"

LABEL_COLORS = {
    "free_parking_space": (46, 204, 113, 115),
    "not_free_parking_space": (231, 76, 60, 115),
    "partially_free_parking_space": (241, 196, 15, 115),
}


def _parse_points(points: str) -> list[tuple[float, float]]:
    """Convert CVAT's ``x,y;x,y`` polygon value into coordinate pairs."""
    return [tuple(map(float, point.split(","))) for point in points.split(";")]


@lru_cache(maxsize=1)
def _load_annotation_rows() -> tuple[dict, ...]:
    """Read the CVAT XML once and return its image and parking-space labels."""
    if not ANNOTATIONS_PATH.exists():
        return ()

    root = ET.parse(ANNOTATIONS_PATH).getroot()
    rows = []
    for image in root.findall("image"):
        image_path = DATASET_DIR / image.attrib["name"]
        if not image_path.exists():
            continue

        polygons = [
            {
                "label": polygon.attrib["label"],
                "points": _parse_points(polygon.attrib["points"]),
            }
            for polygon in image.findall("polygon")
        ]
        rows.append(
            {
                "id": int(image.attrib["id"]),
                "image_path": image_path,
                "polygons": polygons,
            }
        )
    return tuple(rows)


def load_camera_frames() -> pd.DataFrame:
    """Return camera frames and their parking-space polygons from annotations.xml."""
    return pd.DataFrame(_load_annotation_rows(), columns=["id", "image_path", "polygons"])


def get_camera_frame(frame_index: int = 0) -> Optional[pd.Series]:
    """Get one annotated frame, wrapping the requested index when needed."""
    frames = load_camera_frames()
    if frames.empty:
        return None
    return frames.iloc[frame_index % len(frames)]


def render_annotation_overlay(frame: pd.Series) -> Image.Image:
    """Draw the CVAT parking-space polygons over a camera image."""
    image = Image.open(frame["image_path"]).convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for polygon in frame["polygons"]:
        color = LABEL_COLORS.get(polygon["label"], (52, 152, 219, 115))
        draw.polygon(polygon["points"], fill=color, outline=color[:3], width=3)

    return Image.alpha_composite(image, overlay).convert("RGB")
