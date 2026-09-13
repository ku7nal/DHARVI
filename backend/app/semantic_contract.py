"""Shared GAMUS semantic class identifiers and display metadata."""

CLASS_COUNT = 7
BUILDING_CLASS = 3
CLASS_NAMES: tuple[str, ...] = (
    "others",
    "ground",
    "low_vegetation",
    "building",
    "water",
    "road",
    "tree",
)

SEMANTIC_CLASSES = (
    {"id": 0, "name": "others", "label": "Others", "color": "#d9d9d9"},
    {"id": 1, "name": "ground", "label": "Ground", "color": "#b6c99e"},
    {"id": 2, "name": "low_vegetation", "label": "Low vegetation", "color": "#83a96f"},
    {"id": 3, "name": "building", "label": "Building", "color": "#c7cbd1"},
    {"id": 4, "name": "water", "label": "Water", "color": "#72aee8"},
    {"id": 5, "name": "road", "label": "Road", "color": "#e8e1d6"},
    {"id": 6, "name": "tree", "label": "Tree", "color": "#4f8258"},
)
