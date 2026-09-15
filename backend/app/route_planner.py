"""Deterministic road-network routing for emergency route previews."""

from __future__ import annotations

import heapq
from collections.abc import Sequence

ROAD_CLASS = 5


def _validate_point(point: dict[str, int], grid_size: int, label: str) -> tuple[int, int]:
    try:
        row = int(point["row"])
        column = int(point["column"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{label} must include integer row and column values.") from error
    if not (0 <= row < grid_size and 0 <= column < grid_size):
        raise ValueError(f"{label} must be inside the semantic grid.")
    return row, column


def plan_route(
    semantic_data: Sequence[int],
    grid_size: int,
    start: dict[str, int],
    destination: dict[str, int],
) -> dict[str, object]:
    """Return the shortest four-connected path through semantic road cells."""
    if grid_size < 2:
        raise ValueError("gridSize must be at least 2.")
    expected_size = grid_size * grid_size
    if len(semantic_data) != expected_size:
        raise ValueError(f"semanticData must contain exactly {expected_size} cells.")

    labels = [int(value) for value in semantic_data]
    if any(value < 0 or value > 6 for value in labels):
        raise ValueError("semanticData contains an unknown semantic class.")

    start_point = _validate_point(start, grid_size, "start")
    destination_point = _validate_point(destination, grid_size, "destination")
    index_for = lambda row, column: row * grid_size + column
    if labels[index_for(*start_point)] != ROAD_CLASS:
        raise ValueError("start must be on a semantic road cell.")
    if labels[index_for(*destination_point)] != ROAD_CLASS:
        raise ValueError("destination must be on a semantic road cell.")

    def heuristic(point: tuple[int, int]) -> int:
        return abs(point[0] - destination_point[0]) + abs(point[1] - destination_point[1])

    frontier: list[tuple[int, int, int, int]] = [(heuristic(start_point), 0, start_point[0], start_point[1])]
    costs = {start_point: 0}
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    directions = ((-1, 0), (0, -1), (0, 1), (1, 0))
    while frontier:
        _, cost, row, column = heapq.heappop(frontier)
        current = (row, column)
        if cost != costs.get(current):
            continue
        if current == destination_point:
            break
        for row_delta, column_delta in directions:
            next_row = row + row_delta
            next_column = column + column_delta
            if not (0 <= next_row < grid_size and 0 <= next_column < grid_size):
                continue
            next_point = (next_row, next_column)
            if labels[index_for(next_row, next_column)] != ROAD_CLASS:
                continue
            next_cost = cost + 1
            if next_cost >= costs.get(next_point, 1_000_000_000):
                continue
            costs[next_point] = next_cost
            came_from[next_point] = current
            heapq.heappush(frontier, (next_cost + heuristic(next_point), next_cost, next_row, next_column))

    if destination_point not in costs:
        raise ValueError("No connected road route exists between the selected points.")

    path = [destination_point]
    while path[-1] != start_point:
        path.append(came_from[path[-1]])
    path.reverse()
    return {
        "path": [{"row": row, "column": column} for row, column in path],
        "start": {"row": start_point[0], "column": start_point[1]},
        "destination": {"row": destination_point[0], "column": destination_point[1]},
        "gridSize": grid_size,
        "distanceCells": len(path) - 1,
    }
