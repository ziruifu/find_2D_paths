import argparse
import imageio.v3 as imageio
import numpy as np
from pathlib import Path

from path_solver import (
    analyze_universe,
    diagnose_two_path_request,
    find_path_between_points,
    find_random_paths,
    find_two_disjoint_paths,
)


OUTPUT_DIR = Path("2D_paths_output")


def load_universe(image_path: str | Path):
    return imageio.imread(image_path)


def save_path_visualization(universe, path, output_name: str, second_path=None, black_threshold: int = 127):
    image = np.asarray(universe)
    if image.ndim == 3:
        image = image[..., :3].mean(axis=2)

    if float(image.max()) <= 1.0:
        image = image * 255.0

    base = np.where(image <= black_threshold, 0, 255).astype(np.uint8)
    canvas = np.stack([base, base, base], axis=-1)

    for x, y in path:
        canvas[y, x] = (220, 40, 40)

    if second_path is not None:
        for x, y in second_path:
            canvas[y, x] = (45, 110, 230)

    if path:
        canvas[path[0][1], path[0][0]] = (0, 180, 0)
        canvas[path[-1][1], path[-1][0]] = (255, 150, 0)

    if second_path:
        canvas[second_path[0][1], second_path[0][0]] = (0, 190, 190)
        canvas[second_path[-1][1], second_path[-1][0]] = (150, 0, 180)

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / output_name
    imageio.imwrite(output_path, canvas)

    return output_path


def build_parser():
    parser = argparse.ArgumentParser(description="Analyze a binary universe image and solve path problems on it.")
    parser.add_argument("--image", required=True, help="Input PNG image.")
    parser.add_argument("--mode", choices=["single", "double", "random"], help="Solve mode. If omitted, enter interactive mode after analysis.")
    parser.add_argument("--point-a", nargs=2, type=int, metavar=("X", "Y"), help="First point for single mode.")
    parser.add_argument("--point-b", nargs=2, type=int, metavar=("X", "Y"), help="Second point for single mode.")
    parser.add_argument("--pair1", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"), help="First point pair for double mode.")
    parser.add_argument("--pair2", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"), help="Second point pair for double mode.")
    parser.add_argument("--algorithm", choices=["bfs", "dfs", "dijkstra"], default="bfs")
    parser.add_argument("--allow-diagonal", action="store_true", help="Allow diagonal moves.")
    parser.add_argument("--black-threshold", type=int, default=127, help="Black/white threshold.")
    parser.add_argument("--max-random-attempts", type=int, default=200, help="Maximum attempts when searching for a random valid point pair.")
    parser.add_argument("--random-count", type=int, help="How many random point pairs and paths to generate.")
    parser.add_argument("--seed", type=int, help="Optional random seed for random mode.")
    parser.add_argument("--output-name", help="Optional file name inside 2D_paths_output.")

    return parser

#! Not necessary but nice to have
def print_analysis(analysis):
    print("Image analysis:")
    print(f"  size: width={analysis['width']}, height={analysis['height']}")
    print(f"  coordinate range: x from {analysis['x_range'][0]} to {analysis['x_range'][1]}, y from {analysis['y_range'][0]} to {analysis['y_range'][1]}")
    print(f"  total pixels: {analysis['total_pixels']}")
    print(f"  black pixels (walkable): {analysis['black_pixels']} ({analysis['black_ratio']:.2%})")
    print(f"  white pixels (blocked): {analysis['white_pixels']} ({analysis['white_ratio']:.2%})")


def prompt_mode():
    while True:
        mode = input("Choose solve mode [single/double/random/quit]: ").strip().lower()
        if mode in {"single", "double", "random", "quit"}:
            return mode
        print("Invalid mode. Please enter single, double, random, or quit.")

#TODO Need to consider some corner cases here e.g. input not valide or out of image bounds, etc
def prompt_point(label: str, analysis):
    while True:
        raw = input(
            f"Enter {label} as 'x y' within x={analysis['x_range'][0]}..{analysis['x_range'][1]}, "
            f"y={analysis['y_range'][0]}..{analysis['y_range'][1]}: "
        ).strip()
        parts = raw.split()
        if len(parts) != 2:
            print("Please enter exactly two integers.")
            continue

        try:
            x, y = int(parts[0]), int(parts[1])
        except ValueError:
            print("Coordinates must be integers.")
            continue

        if not (
            analysis["x_range"][0] <= x <= analysis["x_range"][1]
            and analysis["y_range"][0] <= y <= analysis["y_range"][1]
        ):
            print("Coordinates are outside the valid image range.")
            continue

        return x, y


def prompt_pair(label: str, analysis):
    print(f"Enter coordinates for {label}:")
    point_a = prompt_point(f"{label} point 1", analysis)
    point_b = prompt_point(f"{label} point 2", analysis)
    return point_a, point_b


def prompt_positive_int(label: str):
    while True:
        raw = input(f"Enter {label}: ").strip()
        try:
            value = int(raw)
        except ValueError:
            print("Please enter an integer.")
            continue

        if value < 1:
            print("The value must be at least 1.")
            continue

        return value


def make_output_name(image_path: str | Path, mode: str, output_name: str | None, *points):
    if output_name:
        return output_name

    stem = Path(image_path).stem
    point_text = "__".join(f"{x}_{y}" for x, y in points)

    return f"{stem}_{mode}_{point_text}.png"


def make_series_output_name(output_name: str | None, image_path: str | Path, mode: str, index: int, total: int, *points):
    if output_name:
        target = Path(output_name)
        suffix = target.suffix or ".png"
        stem = target.stem if target.suffix else target.name
        if total == 1:
            return f"{stem}{suffix}"
        return f"{stem}_{index:02d}{suffix}"

    stem = Path(image_path).stem
    point_text = "__".join(f"{x}_{y}" for x, y in points)
    if total == 1:
        return f"{stem}_{mode}_{point_text}.png"
    
    return f"{stem}_{mode}_{index:02d}_{point_text}.png"


def solve_single(universe, image_path, point_a, point_b, args):
    path = find_path_between_points(
        universe,
        point_a,
        point_b,
        algorithm=args.algorithm,
        allow_diagonal=args.allow_diagonal,
        black_threshold=args.black_threshold,
    )
    if path is None:
        print("No valid path exists between the two points.")
        return 1

    output_name = make_output_name(image_path, "single", args.output_name, point_a, point_b)
    output_path = save_path_visualization(
        universe,
        path,
        output_name,
        black_threshold=args.black_threshold,
    )
    print(f"Path found between {point_a} and {point_b}. Length = {len(path)}")
    print(path)
    print(f"Saved visualization to {output_path}")
    return 0


def solve_double(universe, image_path, pair1, pair2, args):
    result = find_two_disjoint_paths(
        universe,
        pair1,
        pair2,
        allow_diagonal=args.allow_diagonal,
        black_threshold=args.black_threshold,
    )
    if result is None:
        diagnosis = diagnose_two_path_request(
            universe,
            pair1,
            pair2,
            allow_diagonal=args.allow_diagonal,
            black_threshold=args.black_threshold,
        )
        if diagnosis is not None:
            print(diagnosis)
        print("No valid pair of different paths was found for the two point pairs.")
        return 1

    first_path, second_path = result
    output_name = make_output_name(image_path, "double", args.output_name, pair1[0], pair1[1], pair2[0], pair2[1])
    output_path = save_path_visualization(
        universe,
        first_path,
        output_name,
        second_path=second_path,
        black_threshold=args.black_threshold,
    )
    print(f"First path for {pair1}: length = {len(first_path)}")
    print(first_path)
    print(f"Second path for {pair2}: length = {len(second_path)}")
    print(second_path)
    print(f"Saved visualization to {output_path}")
    
    return 0


def solve_random(universe, image_path, args):
    random_count = args.random_count if args.random_count is not None else prompt_positive_int("how many random point pairs to generate")
    results = find_random_paths(
        universe,
        count=random_count,
        algorithm=args.algorithm,
        allow_diagonal=args.allow_diagonal,
        black_threshold=args.black_threshold,
        max_attempts=args.max_random_attempts,
        seed=args.seed,
    )
    if not results:
        print("Failed to find any random valid point pair and path.")
        return 1

    if len(results) < random_count:
        print(f"Requested {random_count} random paths, but only found {len(results)} valid unique point pairs.")

    for index, (point_a, point_b, path) in enumerate(results, start=1):
        output_name = make_series_output_name(
            args.output_name,
            image_path,
            "random",
            index,
            len(results),
            point_a,
            point_b,
        )
        output_path = save_path_visualization(
            universe,
            path,
            output_name,
            black_threshold=args.black_threshold,
        )
        print(f"Random path {index}:")
        print(f"  point A: {point_a}")
        print(f"  point B: {point_b}")
        print(f"  length: {len(path)}")
        print(f"  path: {path}")
        print(f"  saved visualization to {output_path}")

    return 0


def main():
    args = build_parser().parse_args()
    universe = load_universe(args.image)
    analysis = analyze_universe(universe, black_threshold=args.black_threshold)
    print_analysis(analysis)

    mode = args.mode
    if mode is None:
        mode = prompt_mode()
        if mode == "quit":
            return 0

    if mode == "single":
        point_a = tuple(args.point_a) if args.point_a is not None else prompt_point("point A", analysis)
        point_b = tuple(args.point_b) if args.point_b is not None else prompt_point("point B", analysis)
        return solve_single(universe, args.image, point_a, point_b, args)

    if mode == "double":
        pair1 = (
            ((args.pair1[0], args.pair1[1]), (args.pair1[2], args.pair1[3]))
            if args.pair1 is not None
            else prompt_pair("pair 1", analysis)
        )
        pair2 = (
            ((args.pair2[0], args.pair2[1]), (args.pair2[2], args.pair2[3]))
            if args.pair2 is not None
            else prompt_pair("pair 2", analysis)
        )
        return solve_double(universe, args.image, pair1, pair2, args)

    return solve_random(universe, args.image, args)


if __name__ == "__main__":
    raise SystemExit(main())
