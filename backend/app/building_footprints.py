"""Convert aligned GAMUS building labels into normalized LoD2 footprints."""

from collections import defaultdict, deque
from typing import Iterable

import numpy as np

from app.semantic_contract import BUILDING_CLASS


Point = tuple[float, float]


def _components(mask: np.ndarray, minimum_area: int) -> list[list[tuple[int, int]]]:
    visited = np.zeros(mask.shape, dtype=bool)
    components: list[list[tuple[int, int]]] = []
    height, width = mask.shape
    for row in range(height):
        for column in range(width):
            if not mask[row, column] or visited[row, column]:
                continue
            queue = deque([(row, column)])
            visited[row, column] = True
            component: list[tuple[int, int]] = []
            while queue:
                current_row, current_column = queue.popleft()
                component.append((current_row, current_column))
                for row_delta, column_delta in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    next_row = current_row + row_delta
                    next_column = current_column + column_delta
                    if (
                        0 <= next_row < height
                        and 0 <= next_column < width
                        and mask[next_row, next_column]
                        and not visited[next_row, next_column]
                    ):
                        visited[next_row, next_column] = True
                        queue.append((next_row, next_column))
            if len(component) >= minimum_area:
                components.append(component)
    return components


def _boundary_loops(component: set[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    edges: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
    for row, column in component:
        if (row - 1, column) not in component:
            edges[(column, row)].append((column + 1, row))
        if (row, column + 1) not in component:
            edges[(column + 1, row)].append((column + 1, row + 1))
        if (row + 1, column) not in component:
            edges[(column + 1, row + 1)].append((column, row + 1))
        if (row, column - 1) not in component:
            edges[(column, row + 1)].append((column, row))

    loops: list[list[tuple[int, int]]] = []
    while edges:
        start = min(edges)
        current = start
        loop = [start]
        while True:
            targets = edges[current]
            target = targets.pop()
            if not targets:
                del edges[current]
            if target == start:
                break
            loop.append(target)
            current = target
        loops.append(loop)
    return loops


def _point_line_distance(point: Point, start: Point, end: Point) -> float:
    vector_x = end[0] - start[0]
    vector_y = end[1] - start[1]
    if vector_x == 0 and vector_y == 0:
        return float(np.hypot(point[0] - start[0], point[1] - start[1]))
    scale = ((point[0] - start[0]) * vector_x + (point[1] - start[1]) * vector_y) / (vector_x**2 + vector_y**2)
    scale = min(1.0, max(0.0, scale))
    projection = (start[0] + scale * vector_x, start[1] + scale * vector_y)
    return float(np.hypot(point[0] - projection[0], point[1] - projection[1]))


def _simplify(points: list[Point], tolerance: float) -> list[Point]:
    if len(points) <= 4:
        return points
    closed = points + [points[0]]

    def simplify_open(sequence: list[Point]) -> list[Point]:
        if len(sequence) <= 2:
            return sequence
        distances = [_point_line_distance(point, sequence[0], sequence[-1]) for point in sequence[1:-1]]
        farthest = int(np.argmax(distances)) + 1
        if distances[farthest - 1] <= tolerance:
            return [sequence[0], sequence[-1]]
        left = simplify_open(sequence[: farthest + 1])
        right = simplify_open(sequence[farthest:])
        return left[:-1] + right

    simplified = simplify_open(closed[:-1] + [closed[0]])[:-1]
    return simplified if len(simplified) >= 3 else points


def _normalized_loop(loop: Iterable[tuple[int, int]], rows: int, columns: int, tolerance: float) -> list[list[float]]:
    points = [(column / columns - 0.5, row / rows - 0.5) for column, row in loop]
    grid_tolerance = tolerance / max(rows, columns)
    return [[round(value, 6) for value in point] for point in _simplify(points, grid_tolerance)]


def _surrounding_values(component: set[tuple[int, int]], heights: np.ndarray, labels: np.ndarray | None = None) -> np.ndarray:
    candidates: list[float] = []
    rows, columns = heights.shape
    for row, column in component:
        for row_delta in (-1, 0, 1):
            for column_delta in (-1, 0, 1):
                candidate = (row + row_delta, column + column_delta)
                if candidate in component:
                    continue
                if 0 <= candidate[0] < rows and 0 <= candidate[1] < columns:
                    if labels is not None and int(labels[candidate]) != 0:
                        continue
                    value = float(heights[candidate])
                    if np.isfinite(value):
                        candidates.append(value)
    return np.asarray(candidates, dtype=np.float32)


def extract_building_footprints(
    semantic_labels: np.ndarray,
    height_map: np.ndarray,
    *,
    minimum_area: int = 1,
    simplify_tolerance: float = 0.75,
) -> list[dict[str, object]]:
    """Return clean polygon regions in the viewer's normalized scene coordinates."""
    labels = np.asarray(semantic_labels)
    heights = np.asarray(height_map, dtype=np.float32)
    if labels.ndim != 2 or heights.shape != labels.shape:
        raise ValueError("semantic_labels and height_map must be aligned 2D arrays")
    rows, columns = labels.shape
    regions: list[dict[str, object]] = []
    for cells in _components(labels == BUILDING_CLASS, minimum_area):
        component = set(cells)
        loops = _boundary_loops(component)
        if not loops:
            continue
        normalized_loops = [_normalized_loop(loop, rows, columns, simplify_tolerance) for loop in loops]

        def loop_area(loop: list[list[float]]) -> float:
            return abs(sum(loop[index][0] * loop[(index + 1) % len(loop)][1] - loop[(index + 1) % len(loop)][0] * loop[index][1] for index in range(len(loop))) / 2)

        normalized_loops.sort(key=loop_area, reverse=True)
        ground_values = _surrounding_values(component, heights, labels)
        if not ground_values.size:
            ground_values = _surrounding_values(component, heights)
        finite_component_heights = np.asarray([heights[row, column] for row, column in cells], dtype=np.float32)
        finite_component_heights = finite_component_heights[np.isfinite(finite_component_heights)]
        ground_height = float(np.percentile(ground_values, 50)) if ground_values.size else 0.0
        roof_height = float(np.percentile(finite_component_heights, 90)) if finite_component_heights.size else ground_height
        if len(cells) == 1 and roof_height - ground_height < max(0.5, abs(ground_height) * 0.25):
            continue
        relative_height = max(roof_height - ground_height, 0.05)
        spread = float(np.percentile(finite_component_heights, 90) - np.percentile(finite_component_heights, 10)) if finite_component_heights.size else 0.0
        min_row = min(row for row, _ in cells)
        max_row = max(row for row, _ in cells)
        min_column = min(column for _, column in cells)
        max_column = max(column for _, column in cells)
        regions.append({
            "centerX": ((min_column + max_column + 1) / 2 / columns) - 0.5,
            "centerZ": ((min_row + max_row + 1) / 2 / rows) - 0.5,
            "width": (max_column - min_column + 1) / columns,
            "depth": (max_row - min_row + 1) / rows,
            "height": round(relative_height, 4),
            "groundHeight": round(ground_height, 4),
            "roofHeight": round(roof_height, 4),
            "roofType": "flat" if spread <= max(0.8, relative_height * 0.08) else "gabled",
            "footprint": normalized_loops[0],
            "holes": normalized_loops[1:],
            "area": len(cells),
            "minRow": min_row,
            "maxColumn": max_column,
            "source": "semantic_head",
        })
    return regions
