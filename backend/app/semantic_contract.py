"""Shared GAMUS semantic class identifiers and display metadata."""

CLASS_COUNT = 6
BUILDING_CLASS = 2
SEMANTIC_CLASSES: tuple[dict[str, object], ...] = (
    {"id": 0, "name": "ground", "label": "Ground", "color": "#b6c99e"},
    {"id": 1, "name": "low_vegetation", "label": "Low vegetation", "color": "#78a66b"},
    {"id": 2, "name": "building", "label": "Building", "color": "#c7cbd1"},
    {"id": 3, "name": "water", "label": "Water", "color": "#72aee8"},
    {"id": 4, "name": "road", "label": "Road", "color": "#f7f5ef"},
    {"id": 5, "name": "tree", "label": "Tree", "color": "#3d744d"},
)
