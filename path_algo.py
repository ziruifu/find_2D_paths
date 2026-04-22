from collections import deque
import heapq


def neighbors(width: int, height: int, x: int, y: int, allow_diagonal: bool = False):
    directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    if allow_diagonal:
        directions.extend([(1, 1), (1, -1), (-1, 1), (-1, -1)])

    for dx, dy in directions:
        nx = x + dx
        ny = y + dy
        if 0 <= nx < width and 0 <= ny < height:
            yield nx, ny


def reconstruct_path(parent: dict[tuple[int, int], tuple[int, int] | None], end: tuple[int, int]):
    path = []
    current = end

    while current is not None:
        path.append(current)
        current = parent[current]

    path.reverse()
    
    return path


def bfs_path(grid, start, end, allow_diagonal: bool = False, blocked=None):
    blocked = set() if blocked is None else set(blocked)
    height = len(grid)
    width = len(grid[0])

    if start in blocked or end in blocked:
        return None
    if not grid[start[1]][start[0]] or not grid[end[1]][end[0]]:
        return None
    if start == end:
        return [start]

    queue = deque([start])
    parent = {start: None}

    while queue:
        x, y = queue.popleft()
        for neighbor in neighbors(width, height, x, y, allow_diagonal):
            if neighbor in blocked or neighbor in parent:
                continue
            if not grid[neighbor[1]][neighbor[0]]:
                continue

            parent[neighbor] = (x, y)
            if neighbor == end:
                return reconstruct_path(parent, end)
            queue.append(neighbor)

    return None


def dfs_path(grid, start, end, allow_diagonal: bool = False, blocked=None):
    blocked = set() if blocked is None else set(blocked)
    height = len(grid)
    width = len(grid[0])

    if start in blocked or end in blocked:
        return None
    if not grid[start[1]][start[0]] or not grid[end[1]][end[0]]:
        return None
    if start == end:
        return [start]

    stack = [start]
    parent = {start: None}

    while stack:
        x, y = stack.pop()
        if (x, y) == end:
            return reconstruct_path(parent, end)

        next_nodes = []
        for neighbor in neighbors(width, height, x, y, allow_diagonal):
            if neighbor in blocked or neighbor in parent:
                continue
            if not grid[neighbor[1]][neighbor[0]]:
                continue
            parent[neighbor] = (x, y)
            next_nodes.append(neighbor)

        for neighbor in reversed(next_nodes):
            stack.append(neighbor)

    return None


def dijkstra_path(grid, start, end, allow_diagonal: bool = False, blocked=None):
    blocked = set() if blocked is None else set(blocked)
    height = len(grid)
    width = len(grid[0])

    if start in blocked or end in blocked:
        return None
    if not grid[start[1]][start[0]] or not grid[end[1]][end[0]]:
        return None
    if start == end:
        return [start]

    heap = [(0, start)]
    parent = {start: None}
    distance = {start: 0}

    while heap:
        current_distance, current = heapq.heappop(heap)
        if current_distance != distance[current]:
            continue
        if current == end:
            return reconstruct_path(parent, end)

        x, y = current
        for neighbor in neighbors(width, height, x, y, allow_diagonal):
            if neighbor in blocked or not grid[neighbor[1]][neighbor[0]]:
                continue

            next_distance = current_distance + 1
            if next_distance >= distance.get(neighbor, float("inf")):
                continue

            distance[neighbor] = next_distance
            parent[neighbor] = current
            heapq.heappush(heap, (next_distance, neighbor))

    return None


def distance_map(grid, end, allow_diagonal: bool = False, blocked=None):
    blocked = set() if blocked is None else set(blocked)
    height = len(grid)
    width = len(grid[0])

    if end in blocked or not grid[end[1]][end[0]]:
        return {}

    queue = deque([end])
    distance = {end: 0}

    while queue:
        x, y = queue.popleft()
        for neighbor in neighbors(width, height, x, y, allow_diagonal):
            if neighbor in blocked or neighbor in distance:
                continue
            if not grid[neighbor[1]][neighbor[0]]:
                continue

            distance[neighbor] = distance[(x, y)] + 1
            queue.append(neighbor)

    return distance


def reachable_points(grid, start, allow_diagonal: bool = False, blocked=None):
    blocked = set() if blocked is None else set(blocked)
    height = len(grid)
    width = len(grid[0])

    if start in blocked or not grid[start[1]][start[0]]:
        return set()

    queue = deque([start])
    visited = {start}

    while queue:
        x, y = queue.popleft()
        for neighbor in neighbors(width, height, x, y, allow_diagonal):
            if neighbor in blocked or neighbor in visited:
                continue
            if not grid[neighbor[1]][neighbor[0]]:
                continue

            visited.add(neighbor)
            queue.append(neighbor)

    return visited
