# Finding 2D Path
## Zirui Fu for TetraMem Coding Assignment

First of all, thank you so much for your time to review my repo and code.

This pathfinder has been iterated for a few times with improvements in terms of path finding algorithms and user experience.

This current version goes through the following steps:
1. It first loads and analyzes the input image, reporting the image size and range (to easily determine the start and end point coordinates) and black/white pixel count (also to check if the finder is working properly).
2. Then it enters interactive mode so that the user can select to find route between two points (single mode), or to find routes of two pairs of points (double mode), or simply quit.
3. With mode selected, it asks the user to enter the point coordinates, and then output route image(s) to the output dir
4. (optional) this pathfinder also has a CLI mode to allow user to make more adjustments such as path-finding algorithms, diagonal routes, seed, output name, black pixel threshold if image is a gray-scale or RGB file, etc.

## File Structure

this project only has three main code files:
* `main.py`
  - Reads the image
  - Analyzes the image
  - Takes user arguments
  - Calls the path solver
  - Outputs the path image
* `path_algo.py`
  - Contains several path-finding algorithms: BFS, DFS, and Dijkstra
  - Determins distance and if target point is reachable
* `path_solver.py`
  - Normalizes the image
  - Analyze the image and connect points with a desired path according to user selection

## How to use
### Python Package
An environment with python, numpy, and imageio installed. You can use `env.yml` to install the dependencies if you use anaconda/miniconda/mamba/etc.

### Interactivte mode

```bash
python main.py --image your/path/to/image
```

the finder first prints out the image analysis information, then prompt:

```text
Choose solve mode [single/double/random/quit]:
```

* `single`: for finding path between any two points with coordinates
* `double`: for finding paths between any two pairs of points with coordinates
  * It will output two distinctive paths for these two pairs
  * If the two pairs have the same start/end points, it will output two different paths with shared start and end points.
* `random`: randomly pick some start/end points and output paths between them.

### CLI mode

Single mode
```bash
python main.py \
    --image your/path/to/image \
    --mode single \
    --point-a x_a y_a \
    --point-b x_b y_b 
```

Double mode
```bash
python main.py \
    --image your/path/to/image \
    --mode single \
    --pair1 start1_x start1_y end1_x end1_y \
    --pair2 start2_x start2_y end2_x end2_y \
```

Random mode
```bash
python main.py \
  --image your/path/to/image \
  --mode random \
  --random-count 3 \
  --seed 7
```

## General Rules for Pathfinding

### 1. Image Analysis

The finder first normalizes and summrizes the input image to the user:

1. Turns image into black/white grid
2. Summarizes the grid's width and height
3. Set up coordinate limit
4. Count black/white pixel numbers

### 2. Single Path Solving

For a path between any two given points:

1. Set up start point A coordinate
2. Set up end point B coordinate
3. Determines if there is no obstacle between A and B (A-B connectable)
4. If connectable, give a valid path

The finder uses BFS algorithm by default. You can use DFS or Dijkstra instead.

### 3. Double Path Solving

There are a few extra rules I set up for double path solving:

1. Each path only goes through black pixels (of course)
2. The two paths can share start and/or end points
3. The two paths cannot overlap each other except shared start/end points and they must be different (otherwise this is just effectivly one path...)

Generally, the double path solving:

1. Creates the first path following Single Path Solving
2. All pixels used by the first path is temporally banned from the second path
3. Everytime the second path is expanded by BFS, check if it is still valid; restart new path anytime when it is not valid (overlap with the first path or cannot reach end point).

**This algorithm actuallh has a huge loop-hole. I found that when trying to set two pairs of start/end points that would probably lead to two crossing path, it will stuck forever to converge.**
**Solved: Add a error message to two paths that are inevitably crossing.**

### 4. Random Path Solving

Just generate multiple paths according to Single Path Solving rules, but with random start and end points.

## Psudo Code

### Main
```text
function MAIN(image):
    universe = LOAD_IMAGE(image)
    analysis = ANALYZE_UNIVERSE(universe)
    PRINT(analysis)

    mode = GET_USER_MODE()

    if mode == single:
        point_a, point_b = GET_TWO_POINTS()
        solve single path

    if mode == double:
        pair1, pair2 = GET_TWO_PAIRS()
        solve two disjoint paths

    if mode == random:
        count = GET_RANDOM_COUNT()
        solve multiple random valid paths
```

### Image Analysis
```text
function ANALYZE_UNIVERSE(universe):
    grid = NORMALIZE(universe)
    width, height = grid size
    count black pixels
    count white pixels
    return summary
```

### Find Path Between Points
```text
function FIND_PATH_BETWEEN_POINTS(universe, point_a, point_b):
    grid = NORMALIZE(universe)
    solver = CHOOSE_ALGORITHM()
    return solver(grid, point_a, point_b)
```

### Find Random Path
```text
function FIND_RANDOM_PATH(universe):
    grid = NORMALIZE(universe)
    choose a random black point A
    find all black points connected to A
    choose a different random point B from that component
    return path from A to B
```