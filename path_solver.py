import sys
import random
import time
import numpy as np

from path_algo import bfs_path, dfs_path, dijkstra_path, distance_map, neighbors, reachable_points

DOUBLE_SEARCH_MAX_SECONDS = 2.0
DOUBLE_SEARCH_MAX_STATES = 50000
_SEARCH_ABORTED = object()


def normalize_universe(universe, black_threshold: int = 127):
    image = np.asarray(universe)
    if image.ndim not in (2, 3):
        raise ValueError("universe must be a 2D grayscale image or a 3D color image")

    if image.ndim == 3:
        image = image[..., :3].mean(axis=2)

    threshold = black_threshold / 255.0 if float(image.max()) <= 1.0 else float(black_threshold)
    
    return image <= threshold


def analyze_universe(universe, black_threshold: int = 127):
    grid = normalize_universe(universe, black_threshold=black_threshold)
    height, width = grid.shape
    black_count = int(grid.sum())
    total_pixels = width * height
    white_count = total_pixels - black_count

    return {
        "width": width,
        "height": height,
        "x_range": (0, width - 1),
        "y_range": (0, height - 1),
        "total_pixels": total_pixels,
        "black_pixels": black_count,
        "white_pixels": white_count,
        "black_ratio": black_count / total_pixels if total_pixels else 0.0,
        "white_ratio": white_count / total_pixels if total_pixels else 0.0,
    }


def points_connected(
    universe,
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    algorithm: str = "bfs",
    allow_diagonal: bool = False,
    black_threshold: int = 127,
) -> bool:
    return (
        find_path_between_points(
            universe,
            point_a,
            point_b,
            algorithm=algorithm,
            allow_diagonal=allow_diagonal,
            black_threshold=black_threshold,
        )
        is not None
    )


def find_path_between_points(
    universe,
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    algorithm: str = "bfs",
    allow_diagonal: bool = False,
    black_threshold: int = 127,
):
    grid = normalize_universe(universe, black_threshold=black_threshold)
    _validate_point(grid, point_a, "point_a")
    _validate_point(grid, point_b, "point_b")

    solver = _select_algorithm(algorithm)

    return solver(grid, point_a, point_b, allow_diagonal=allow_diagonal)


def find_two_disjoint_paths(
    universe,
    pair1: tuple[tuple[int, int], tuple[int, int]],
    pair2: tuple[tuple[int, int], tuple[int, int]],
    allow_diagonal: bool = False,
    black_threshold: int = 127,
):
    grid = normalize_universe(universe, black_threshold=black_threshold)
    first_start, first_end = pair1
    second_start, second_end = pair2

    for label, point in (
        ("pair1.start", first_start),
        ("pair1.end", first_end),
        ("pair2.start", second_start),
        ("pair2.end", second_end),
    ):
        _validate_point(grid, point, label)

    if not _all_points_walkable(grid, first_start, first_end, second_start, second_end):
        return None

    if _has_alternating_outer_boundary_order(grid, pair1, pair2, allow_diagonal=allow_diagonal):
        return None

    orders = [
        (first_start, first_end, second_start, second_end),
        (second_start, second_end, first_start, first_end),
    ]

    for start_a, end_a, start_b, end_b in orders:
        result = _search_two_paths(grid, start_a, end_a, start_b, end_b, allow_diagonal)
        if result is None:
            continue

        path_a, path_b = result
        if (start_a, end_a) == pair1:
            return path_a, path_b
        return path_b, path_a

    return None


def diagnose_two_path_request(
    universe,
    pair1: tuple[tuple[int, int], tuple[int, int]],
    pair2: tuple[tuple[int, int], tuple[int, int]],
    allow_diagonal: bool = False,
    black_threshold: int = 127,
):
    grid = normalize_universe(universe, black_threshold=black_threshold)

    for label, point in (
        ("pair1.start", pair1[0]),
        ("pair1.end", pair1[1]),
        ("pair2.start", pair2[0]),
        ("pair2.end", pair2[1]),
    ):
        _validate_point(grid, point, label)

    if not _all_points_walkable(grid, pair1[0], pair1[1], pair2[0], pair2[1]):
        return "At least one selected endpoint is on a blocked pixel."

    if _has_alternating_outer_boundary_order(grid, pair1, pair2, allow_diagonal=allow_diagonal):
        return (
            "These four endpoints sit on the outer image boundary in alternating order, "
            "so two disjoint paths for this pairing would have to cross."
        )

    return None


def find_random_paths(
    universe,
    count: int = 1,
    algorithm: str = "bfs",
    allow_diagonal: bool = False,
    black_threshold: int = 127,
    max_attempts: int = 200,
    seed: int | None = None,
):
    if count < 1:
        raise ValueError("count must be at least 1")

    grid = normalize_universe(universe, black_threshold=black_threshold)
    walkable = np.argwhere(grid)
    if len(walkable) < 2:
        return []

    solver = _select_algorithm(algorithm)
    rng = random.Random(seed)
    walkable_points = [(int(x), int(y)) for y, x in walkable]
    used_pairs = set()
    results = []

    for _ in range(max_attempts * count):
        point_a = rng.choice(walkable_points)
        component = list(reachable_points(grid, point_a, allow_diagonal=allow_diagonal))
        if len(component) < 2:
            continue

        candidates = [point for point in component if point != point_a]
        point_b = rng.choice(candidates)
        pair_key = tuple(sorted((point_a, point_b)))
        if pair_key in used_pairs:
            continue

        path = solver(grid, point_a, point_b, allow_diagonal=allow_diagonal)
        if path is not None:
            results.append((point_a, point_b, path))
            used_pairs.add(pair_key)
            if len(results) == count:
                return results

    return results


def _search_two_paths(grid, first_start, first_end, second_start, second_end, allow_diagonal):
    if not grid[first_start[1], first_start[0]] or not grid[first_end[1], first_end[0]]:
        return None
    if not grid[second_start[1], second_start[0]] or not grid[second_end[1], second_end[0]]:
        return None

    shared_endpoints = {first_start, first_end} & {second_start, second_end}
    reserved_for_second = {second_start, second_end} - shared_endpoints

    if bfs_path(grid, first_start, first_end, allow_diagonal=allow_diagonal, blocked=reserved_for_second) is None:
        return None
    if bfs_path(grid, second_start, second_end, allow_diagonal=allow_diagonal) is None:
        return None

    heuristic = distance_map(grid, first_end, allow_diagonal=allow_diagonal, blocked=reserved_for_second)
    sys.setrecursionlimit(max(sys.getrecursionlimit(), grid.shape[0] * grid.shape[1] + 100))

    first_path = [first_start]
    used = {first_start}
    height, width = grid.shape
    deadline = time.monotonic() + DOUBLE_SEARCH_MAX_SECONDS
    explored_states = 0

    def dfs(current):
        nonlocal explored_states
        if explored_states >= DOUBLE_SEARCH_MAX_STATES or time.monotonic() >= deadline:
            return _SEARCH_ABORTED
        explored_states += 1

        blocked_for_first = (used - {current}) | reserved_for_second
        if bfs_path(grid, current, first_end, allow_diagonal=allow_diagonal, blocked=blocked_for_first) is None:
            return None

        second_path = bfs_path(
            grid,
            second_start,
            second_end,
            allow_diagonal=allow_diagonal,
            blocked=used - shared_endpoints,
        )
        if second_path is None:
            return None

        if current == first_end:
            if second_path == list(first_path) or second_path == list(reversed(first_path)):
                return None
            return list(first_path), second_path

        next_points = []
        for neighbor in neighbors(width, height, current[0], current[1], allow_diagonal):
            if neighbor in used or neighbor in reserved_for_second:
                continue
            if not grid[neighbor[1], neighbor[0]]:
                continue
            next_points.append(neighbor)

        next_points.sort(
            key=lambda point: (
                heuristic.get(point, float("inf")),
                abs(point[0] - first_end[0]) + abs(point[1] - first_end[1]),
            )
        )

        for neighbor in next_points:
            first_path.append(neighbor)
            used.add(neighbor)
            result = dfs(neighbor)
            if result is _SEARCH_ABORTED:
                return _SEARCH_ABORTED
            if result is not None:
                return result
            used.remove(neighbor)
            first_path.pop()

        return None

    result = dfs(first_start)
    if result is _SEARCH_ABORTED:
        return None
    return result


def _select_algorithm(algorithm: str):
    algorithms = {
        "bfs": bfs_path,
        "dfs": dfs_path,
        "dijkstra": dijkstra_path,
    }
    if algorithm not in algorithms:
        raise ValueError("algorithm must be one of: bfs, dfs, dijkstra")
    
    return algorithms[algorithm]


def _validate_point(grid, point: tuple[int, int], label: str):
    height, width = grid.shape
    x, y = point
    if 0 <= x < width and 0 <= y < height:
        return
    raise ValueError(f"{label} is outside the image bounds")


def _has_alternating_outer_boundary_order(
    grid,
    pair1: tuple[tuple[int, int], tuple[int, int]],
    pair2: tuple[tuple[int, int], tuple[int, int]],
    allow_diagonal: bool,
):
    if allow_diagonal:
        return False

    height, width = grid.shape
    endpoints = [
        (pair1[0], "pair1"),
        (pair1[1], "pair1"),
        (pair2[0], "pair2"),
        (pair2[1], "pair2"),
    ]

    if len({point for point, _ in endpoints}) < 4:
        return False

    ordered_labels = []
    for point, label in endpoints:
        perimeter_index = _outer_boundary_index(point, width, height)
        if perimeter_index is None:
            return False
        ordered_labels.append((perimeter_index, label))

    ordered_labels.sort()
    labels = [label for _, label in ordered_labels]

    for shift in range(len(labels)):
        rotated = labels[shift:] + labels[:shift]
        if rotated == ["pair1", "pair2", "pair1", "pair2"]:
            return True

    return False


def _outer_boundary_index(point: tuple[int, int], width: int, height: int):
    x, y = point

    if y == 0:
        return x
    if x == width - 1:
        return (width - 1) + y
    if y == height - 1:
        return (width - 1) + (height - 1) + (width - 1 - x)
    if x == 0:
        return 2 * (width - 1) + (height - 1) + (height - 1 - y)

    return None


def _all_points_walkable(grid, *points: tuple[int, int]):
    return all(bool(grid[y, x]) for x, y in points)
