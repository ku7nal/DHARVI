"""Create aligned visual diagnostics for aerial reconstruction examples."""

import argparse
import html
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from app.building_footprints import extract_building_footprints
from app.main import SCENE_GRID_SIZE, _prepare_semantic_labels
from app.model_service import DepthAnythingModelService
from app.semantic_contract import SEMANTIC_CLASSES


def semantic_palette() -> np.ndarray:
    return np.asarray([
        tuple(int(color.lstrip("#")[index:index + 2], 16) for index in (0, 2, 4))
        for color in (item["color"] for item in SEMANTIC_CLASSES)
    ], dtype=np.uint8)


def semantic_preview(labels: np.ndarray) -> Image.Image:
    palette = semantic_palette()
    return Image.fromarray(palette[np.clip(labels, 0, len(palette) - 1)], mode="RGB")


def footprint_preview(labels: np.ndarray, regions: list[dict[str, object]], display_size: tuple[int, int]) -> Image.Image:
    colors = semantic_palette()
    image = Image.fromarray(colors[np.clip(labels, 0, len(colors) - 1)], mode="RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for region in regions:
        for polygon in [region["footprint"], *region.get("holes", [])]:
            points = [(round(point[0] * width + width / 2), round(point[1] * height + height / 2)) for point in polygon]
            if len(points) >= 3:
                draw.line([*points, points[0]], fill="#ff3158", width=max(1, width // 256))
    return image.resize(display_size, Image.Resampling.NEAREST)


def write_case(service: DepthAnythingModelService, name: str, source: Path, output: Path) -> dict[str, object]:
    image = Image.open(source).convert("RGB")
    prediction = service.predict_result(image)
    height = np.maximum(np.nan_to_num(prediction["height"], nan=0.0), 0.0)
    height_grid = np.asarray(
        Image.fromarray(height, mode="F").resize((SCENE_GRID_SIZE, SCENE_GRID_SIZE), Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    boundary = prediction.get("boundary")
    boundary_grid = None if boundary is None else np.asarray(
        Image.fromarray(np.asarray(boundary, dtype=np.float32), mode="F").resize((SCENE_GRID_SIZE, SCENE_GRID_SIZE), Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    semantic_full = semantic_grid = None
    if "semantic" in prediction:
        semantic_full, semantic_grid = _prepare_semantic_labels(
            prediction["semantic"], SCENE_GRID_SIZE, prediction.get("boundary")
        )
    regions = extract_building_footprints(
        semantic_grid if semantic_grid is not None else np.zeros_like(height_grid, dtype=np.uint8),
        height_grid,
        minimum_area=1,
        boundary_confidence=boundary_grid,
    ) if semantic_grid is not None else []

    output.mkdir(parents=True, exist_ok=True)
    image.save(output / "input.png")
    height_preview = np.clip(height / max(float(height.max()), 1e-6) * 255, 0, 255).astype(np.uint8)
    Image.fromarray(height_preview, mode="L").save(output / "height-prediction.png")
    if semantic_full is not None and semantic_grid is not None:
        semantic_preview(semantic_full).save(output / "semantic-full.png")
        scene_grid_preview = semantic_preview(semantic_grid)
        scene_grid_preview.save(output / "semantic-scene-grid-native.png")
        scene_grid_preview.resize(image.size, Image.Resampling.NEAREST).save(output / "semantic-scene-grid.png")
        footprint_preview(semantic_grid, regions, image.size).save(output / "building-footprints.png")
    if boundary is not None:
        Image.fromarray(np.clip(np.asarray(boundary) * 255, 0, 255).astype(np.uint8), mode="L").save(output / "boundary-confidence.png")

    manifest = {
        "name": name,
        "source": source.name,
        "width": image.width,
        "height": image.height,
        "sceneGridSize": SCENE_GRID_SIZE,
        "minHeightMeters": float(height.min()),
        "maxHeightMeters": float(height.max()),
        "buildingRegionCount": len(regions),
        "buildingPixelFraction": float(np.mean(semantic_grid == 3)) if semantic_grid is not None else None,
        "semanticClassFractions": {
            item["name"]: float(np.mean(semantic_grid == item["id"]))
            for item in SEMANTIC_CLASSES
        } if semantic_grid is not None else {},
        "evidence": "visual inspection only; no aligned reference raster supplied",
        "artifacts": [
            "input.png", "height-prediction.png", "semantic-full.png",
            "semantic-scene-grid.png", "semantic-scene-grid-native.png",
            "building-footprints.png", "scene.png",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def write_report(cases: list[dict[str, object]], output: Path) -> None:
    sections = []
    for case in cases:
        case_name = html.escape(str(case["name"]))
        folder = html.escape(str(case["name"]))
        height_text = f"{case['minHeightMeters']:.1f}–{case['maxHeightMeters']:.1f} m estimated nDSM"
        fractions = " · ".join(f"{html.escape(name)} {value:.0%}" for name, value in case["semanticClassFractions"].items())
        stages = [
            ("Input image", "input.png"),
            ("Predicted height", "height-prediction.png"),
            ("Semantic labels (full resolution)", "semantic-full.png"),
            ("Semantic labels (scene grid, aligned)", "semantic-scene-grid.png"),
            ("Building footprints (aligned)", "building-footprints.png"),
            ("Final application scene", "scene.png"),
        ]
        cards = "".join(
            f'<figure><img src="{folder}/{asset}" alt="{html.escape(title)} for {case_name}"><figcaption>{html.escape(title)}</figcaption></figure>'
            for title, asset in stages
            if (output / str(case["name"]) / asset).exists()
        )
        sections.append(
            f'<section><h2>{case_name}</h2><p>{html.escape(height_text)} · {case["buildingRegionCount"]} building regions</p>'
            f'<p class="fractions">{fractions}</p><div class="stages">{cards}</div>'
            f'<p class="finding">First visible divergence: {html.escape(str(case.get("finding", "Not reviewed")))} Evidence is qualitative; no reference-backed accuracy metrics are available for this case.</p></section>'
        )
    document = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>DepthWizard reconstruction failure review</title><style>
body{font:15px system-ui,sans-serif;margin:32px;background:#f5f6fa;color:#202431}main{max-width:1500px;margin:auto}h1{margin-bottom:4px}section{background:white;padding:20px;margin:24px 0;border-radius:12px;box-shadow:0 2px 12px #20243112}.stages{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}figure{margin:0}img{width:100%;aspect-ratio:1.42;object-fit:contain;background:#eef0f4;border-radius:6px}figcaption{padding:7px 2px;font-weight:600}.finding{border-left:3px solid #8070e8;padding:8px 12px;background:#f6f4ff}.fractions{color:#5b6070;font-size:13px}
</style></head><body><main><h1>Reconstruction failure review</h1><p>Visual inspection only. Estimated nDSM values are model outputs, not measured ground truth. Scene screenshots are captured from the running application with the matching source image.</p>""" + "".join(sections) + "</main></body></html>"
    (output / "index.html").write_text(document)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=Path("dinosaur.pth"))
    parser.add_argument("--case", action="append", default=[], metavar="NAME=IMAGE", help="Repeat for each image")
    parser.add_argument("--finding", action="append", default=[], metavar="NAME=TEXT", help="Record the first visible divergence")
    parser.add_argument("--report-only", action="store_true", help="Rebuild the report from existing case manifests")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    findings = {}
    for value in args.finding:
        if "=" not in value:
            parser.error(f"invalid finding {value!r}; expected NAME=TEXT")
        name, finding = value.split("=", 1)
        findings[name] = finding
    cases = [json.loads(path.read_text()) for path in sorted(args.output.glob("*/manifest.json"))] if args.report_only else []
    if args.report_only and args.case:
        parser.error("--case cannot be combined with --report-only")
    service = None if args.report_only else DepthAnythingModelService(args.checkpoint)
    for value in args.case:
        if "=" not in value:
            parser.error(f"invalid case {value!r}; expected NAME=IMAGE")
        name, filename = value.split("=", 1)
        if not name or Path(name).name != name or not Path(filename).is_file():
            parser.error(f"case image does not exist: {filename}")
        case = write_case(service, name, Path(filename), args.output / name)
        cases = [existing for existing in cases if existing["name"] != name]
        cases.append(case)
        print(json.dumps({"case": name, "status": "complete", "regions": case["buildingRegionCount"]}))
    for case in cases:
        if case["name"] in findings:
            case["finding"] = findings[case["name"]]
        case_dir = args.output / str(case["name"])
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "manifest.json").write_text(json.dumps(case, indent=2) + "\n")
    if not cases:
        parser.error("provide at least one --case, or use --report-only after generating cases")
    write_report(cases, args.output)
    print(f"Review report: {args.output / 'index.html'}")


if __name__ == "__main__":
    main()
