"""Deterministic road-network routing for emergency route previews."""

from __future__ import annotations

import heapq
import math
from collections.abc import Sequence

ROAD_CLASS = 5
ROUTE_PROFILES = {
    "fastest": {"distance": 1.0, "risk": 0.04, "accessibility": 0.02},
    "safest": {"distance": 0.55, "risk": 1.0, "accessibility": 0.2},
    "accessible": {"distance": 0.7, "risk": 0.5, "accessibility": 1.0},
}


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
    blocked_cells: Sequence[dict[str, int]] | None = None,
    avoid_water: bool = True,
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

    blocked: set[tuple[int, int]] = set()
    for point in blocked_cells or []:
        blocked.add(_validate_point(point, grid_size, "blocked cell"))
    if start_point in blocked or destination_point in blocked:
        raise ValueError("The selected route endpoint is inside a debris zone.")
    water_cells = sum(value == 4 for value in labels)
    water_blocked: set[tuple[int, int]] = set()
    if avoid_water:
        for row in range(grid_size):
            for column in range(grid_size):
                if labels[index_for(row, column)] != ROAD_CLASS:
                    continue
                if any(
                    0 <= row + row_delta < grid_size
                    and 0 <= column + column_delta < grid_size
                    and labels[index_for(row + row_delta, column + column_delta)] == 4
                    for row_delta in (-1, 0, 1)
                    for column_delta in (-1, 0, 1)
                    if row_delta or column_delta
                ):
                    water_blocked.add((row, column))
    if start_point in water_blocked:
        raise ValueError("start must not be adjacent to an active water hazard.")
    if destination_point in water_blocked:
        raise ValueError("destination must not be adjacent to an active water hazard.")

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
            if next_point in blocked or next_point in water_blocked:
                continue
            next_cost = cost + 1
            if next_cost >= costs.get(next_point, 1_000_000_000):
                continue
            costs[next_point] = next_cost
            came_from[next_point] = current
            heapq.heappush(frontier, (next_cost + heuristic(next_point), next_cost, next_row, next_column))

    if destination_point not in costs:
        raise ValueError("No connected road route exists after applying the active hazards.")

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
        "hazards": {
            "waterCells": water_cells if avoid_water else 0,
            "waterBlockedRoadCells": len(water_blocked),
            "debrisCells": len(blocked),
            "blockedRoadCells": sum(labels[index_for(row, column)] == ROAD_CLASS for row, column in blocked),
            "waterAvoidance": avoid_water,
        },
    }


def _hazard_cells(labels: list[int], grid_size: int, blocked_cells: Sequence[dict[str, int]], avoid_water: bool) -> tuple[set[tuple[int, int]], set[tuple[int, int]], int]:
    index_for = lambda row, column: row * grid_size + column
    blocked = {_validate_point(point, grid_size, "blocked cell") for point in blocked_cells}
    water_cells = sum(value == 4 for value in labels)
    water_blocked: set[tuple[int, int]] = set()
    if avoid_water:
        for row in range(grid_size):
            for column in range(grid_size):
                if labels[index_for(row, column)] != ROAD_CLASS:
                    continue
                if any(
                    0 <= row + row_delta < grid_size
                    and 0 <= column + column_delta < grid_size
                    and labels[index_for(row + row_delta, column + column_delta)] == 4
                    for row_delta in (-1, 0, 1)
                    for column_delta in (-1, 0, 1)
                    if row_delta or column_delta
                ):
                    water_blocked.add((row, column))
    return blocked, water_blocked, water_cells


def _route_inputs(semantic_data: Sequence[int], grid_size: int, start: dict[str, int], destination: dict[str, int], blocked_cells: Sequence[dict[str, int]], avoid_water: bool) -> tuple[list[int], tuple[int, int], tuple[int, int], set[tuple[int, int]], set[tuple[int, int]], int]:
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
    blocked, water_blocked, water_cells = _hazard_cells(labels, grid_size, blocked_cells, avoid_water)
    if start_point in blocked or destination_point in blocked:
        raise ValueError("The selected route endpoint is inside a debris zone.")
    if start_point in water_blocked:
        raise ValueError("start must not be adjacent to an active water hazard.")
    if destination_point in water_blocked:
        raise ValueError("destination must not be adjacent to an active water hazard.")
    return labels, start_point, destination_point, blocked, water_blocked, water_cells


def _find_weighted_path(labels: list[int], grid_size: int, start: tuple[int, int], destination: tuple[int, int], blocked: set[tuple[int, int]], water_blocked: set[tuple[int, int]], cell_cost, penalties: set[tuple[int, int]]) -> list[tuple[int, int]] | None:
    def heuristic(point: tuple[int, int]) -> float:
        return abs(point[0] - destination[0]) + abs(point[1] - destination[1])

    index_for = lambda row, column: row * grid_size + column
    frontier: list[tuple[float, float, int, int]] = [(heuristic(start), 0.0, start[0], start[1])]
    costs = {start: 0.0}
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    directions = ((-1, 0), (0, -1), (0, 1), (1, 0))
    while frontier:
        _, cost, row, column = heapq.heappop(frontier)
        current = (row, column)
        if cost != costs.get(current):
            continue
        if current == destination:
            path = [destination]
            while path[-1] != start:
                path.append(came_from[path[-1]])
            path.reverse()
            return path
        for row_delta, column_delta in directions:
            next_row, next_column = row + row_delta, column + column_delta
            if not (0 <= next_row < grid_size and 0 <= next_column < grid_size):
                continue
            next_point = (next_row, next_column)
            if labels[index_for(next_row, next_column)] != ROAD_CLASS or next_point in blocked or next_point in water_blocked:
                continue
            next_cost = cost + cell_cost(next_point) + (2.25 if next_point in penalties and next_point not in (start, destination) else 0.0)
            if next_cost >= costs.get(next_point, float("inf")):
                continue
            costs[next_point] = next_cost
            came_from[next_point] = current
            heapq.heappush(frontier, (next_cost + heuristic(next_point), next_cost, next_row, next_column))
    return None


def plan_ranked_routes(
    semantic_data: Sequence[int],
    grid_size: int,
    start: dict[str, int],
    destination: dict[str, int],
    blocked_cells: Sequence[dict[str, int]] | None = None,
    avoid_water: bool = True,
    height_data: Sequence[float] | None = None,
    uncertainty_data: Sequence[float] | None = None,
    profile: str = "fastest",
) -> dict[str, object]:
    """Return deterministic fastest, safest, or accessible ranked route alternatives."""
    if profile not in ROUTE_PROFILES:
        raise ValueError("profile must be one of: fastest, safest, accessible.")
    labels, start_point, destination_point, blocked, water_blocked, water_cells = _route_inputs(semantic_data, grid_size, start, destination, blocked_cells or [], avoid_water)
    expected_size = grid_size * grid_size
    raw_heights = [0.0] * expected_size if height_data is None else list(height_data)
    raw_uncertainty = [0.0] * expected_size if uncertainty_data is None else list(uncertainty_data)
    if len(raw_heights) != expected_size or len(raw_uncertainty) != expected_size:
        raise ValueError(f"heightData and uncertaintyData must contain exactly {expected_size} cells.")
    if any(not math.isfinite(float(value)) for value in raw_heights + raw_uncertainty):
        raise ValueError("heightData and uncertaintyData must contain finite numeric values.")
    heights = [float(value) for value in raw_heights]
    uncertainty = [max(0.0, min(1.0, float(value))) for value in raw_uncertainty]
    height_range = max(max(heights) - min(heights), 1.0)
    index_for = lambda row, column: row * grid_size + column

    def cell_features(point: tuple[int, int]) -> tuple[float, float, set[str]]:
        row, column = point
        index = index_for(row, column)
        neighbours = [(row + row_delta, column + column_delta) for row_delta, column_delta in ((-1, 0), (1, 0), (0, -1), (0, 1)) if 0 <= row + row_delta < grid_size and 0 <= column + column_delta < grid_size]
        slope = min(1.0, max(abs(heights[index] - heights[index_for(neighbour_row, neighbour_column)]) for neighbour_row, neighbour_column in neighbours) / height_range) if neighbours else 0.0
        nearby_labels = [labels[index_for(neighbour_row, neighbour_column)] for neighbour_row, neighbour_column in neighbours]
        hazard_names: set[str] = set()
        if nearby_labels and any(value == 3 for value in nearby_labels):
            hazard_names.add("building proximity")
        if uncertainty[index] >= 0.35:
            hazard_names.add("prediction uncertainty")
        if point in water_blocked:
            hazard_names.add("water")
        risk = slope * 38.0 + uncertainty[index] * 42.0 + (12.0 if 3 in nearby_labels else 0.0) + (20.0 if point in water_blocked else 0.0)
        return min(100.0, risk), slope * 100.0, hazard_names

    profile_weights = ROUTE_PROFILES[profile]
    candidates: list[dict[str, object]] = []
    penalties: set[tuple[int, int]] = set()
    for _ in range(3):
        path = _find_weighted_path(
            labels,
            grid_size,
            start_point,
            destination_point,
            blocked,
            water_blocked,
            lambda point: 1.0 + (cell_features(point)[0] * profile_weights["risk"] / 100.0) + (cell_features(point)[1] * profile_weights["accessibility"] / 100.0),
            penalties,
        )
        if not path:
            break
        if any(candidate["path"] == [{"row": row, "column": column} for row, column in path] for candidate in candidates):
            break
        features = [cell_features(point) for point in path]
        risk_score = round(sum(feature[0] for feature in features) / len(features), 1)
        accessibility_score = round(sum(feature[1] for feature in features) / len(features), 1)
        encountered = {name for _, _, names in features for name in names}
        all_hazards: set[str] = set()
        if blocked:
            all_hazards.add("debris")
        if water_cells and avoid_water:
            all_hazards.add("water")
        for cell_row in range(grid_size):
            for cell_column in range(grid_size):
                cell = (cell_row, cell_column)
                if labels[index_for(cell_row, cell_column)] == ROAD_CLASS:
                    all_hazards.update(cell_features(cell)[2])
        avoided = sorted(all_hazards - encountered)
        distance = len(path) - 1
        score = round(distance * profile_weights["distance"] + risk_score * profile_weights["risk"] + accessibility_score * profile_weights["accessibility"], 3)
        candidates.append({"path": [{"row": row, "column": column} for row, column in path], "distanceCells": distance, "travelTimeMinutes": round(distance * 1.2, 1), "riskScore": risk_score, "accessibilityScore": accessibility_score, "avoidedHazards": avoided, "profileScore": score})
        penalties.update(path[1:-1])
    if not candidates:
        raise ValueError("No connected road route exists after applying the active hazards.")
    candidates.sort(key=lambda item: (item["profileScore"], item["distanceCells"], str(item["path"])))
    selected = candidates[0]
    return {
        **selected,
        "start": {"row": start_point[0], "column": start_point[1]},
        "destination": {"row": destination_point[0], "column": destination_point[1]},
        "gridSize": grid_size,
        "profile": profile,
        "selectedIndex": 0,
        "alternatives": candidates,
        "hazards": {"waterCells": water_cells if avoid_water else 0, "waterBlockedRoadCells": len(water_blocked), "debrisCells": len(blocked), "blockedRoadCells": sum(labels[index_for(row, column)] == ROAD_CLASS for row, column in blocked), "waterAvoidance": avoid_water},
    }
