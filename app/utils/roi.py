from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "roi_config.json"
EXAMPLE_PATH = Path(__file__).resolve().parents[1] / "config" / "roi_config.example.json"


@dataclass
class ROIConfig:
    lanes: List[List[Tuple[float, float]]] = field(default_factory=list)
    stop_line: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None
    classes: List[str] = field(default_factory=lambda: [
        "person", "car", "motorcycle", "bus", "truck", "bicycle"
    ])
    # Lane directions (normalized points), parallel to lanes list
    lane_directions: List[Tuple[Tuple[float, float], Tuple[float, float]]] = field(default_factory=list)
    # Auto lane direction learning
    auto_lane_direction: bool = False
    auto_lane_warmup_frames: int = 180
    # Speed calibration
    speed_calib_points: Optional[Tuple[Tuple[float, float], Tuple[float, float]]] = None
    speed_calib_distance_m: Optional[float] = None
    speed_limit_kmh: Optional[float] = None
    # Optional model paths
    helmet_model_path: Optional[str] = None
    plate_model_path: Optional[str] = None


def load_roi_config() -> ROIConfig:
    path = CONFIG_PATH
    if not path.exists():
        # Write example if nothing exists
        EXAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not EXAMPLE_PATH.exists():
            EXAMPLE_PATH.write_text(json.dumps({
                "lanes": [
                    [[0.05, 0.9], [0.45, 0.5], [0.55, 0.5], [0.95, 0.9]]
                ],
                "lane_directions": [
                    [[0.5, 0.95], [0.5, 0.6]]
                ],
                "auto_lane_direction": False,
                "auto_lane_warmup_frames": 180,
                "stop_line": [[0.3, 0.8], [0.7, 0.8]],
                "classes": ["person", "car", "motorcycle", "bus", "truck", "bicycle"],
                "speed_calib_points": [[0.1, 0.9], [0.4, 0.9]],
                "speed_calib_distance_m": 10.0,
                "speed_limit_kmh": 40.0,
                "helmet_model_path": None,
                "plate_model_path": None
            }, indent=2))
        return ROIConfig()
    data = json.loads(path.read_text())
    lanes = [
        [(float(x), float(y)) for x, y in poly]
        for poly in data.get("lanes", [])
    ]
    stop_line = data.get("stop_line")
    if stop_line is not None:
        stop_line = (
            (float(stop_line[0][0]), float(stop_line[0][1])),
            (float(stop_line[1][0]), float(stop_line[1][1]))
        )
    classes = [str(c) for c in data.get("classes", [])]

    # Lane directions
    lane_dirs_in = data.get("lane_directions", [])
    lane_directions: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    for d in lane_dirs_in:
        lane_directions.append(((float(d[0][0]), float(d[0][1])), (float(d[1][0]), float(d[1][1]))))

    auto_lane_direction = bool(data.get("auto_lane_direction", False))
    auto_lane_warmup_frames = int(data.get("auto_lane_warmup_frames", 180))

    scp = data.get("speed_calib_points")
    speed_calib_points = None
    if scp is not None:
        speed_calib_points = (
            (float(scp[0][0]), float(scp[0][1])),
            (float(scp[1][0]), float(scp[1][1]))
        )
    speed_calib_distance_m = float(data.get("speed_calib_distance_m")) if data.get("speed_calib_distance_m") is not None else None
    speed_limit_kmh = float(data.get("speed_limit_kmh")) if data.get("speed_limit_kmh") is not None else None

    helmet_model_path = data.get("helmet_model_path")
    plate_model_path = data.get("plate_model_path")

    return ROIConfig(
        lanes=lanes,
        stop_line=stop_line,
        classes=classes,
        lane_directions=lane_directions,
        auto_lane_direction=auto_lane_direction,
        auto_lane_warmup_frames=auto_lane_warmup_frames,
        speed_calib_points=speed_calib_points,
        speed_calib_distance_m=speed_calib_distance_m,
        speed_limit_kmh=speed_limit_kmh,
        helmet_model_path=helmet_model_path,
        plate_model_path=plate_model_path,
    )


def denormalize_points(points, width: int, height: int):
    if points is None:
        return None
    if isinstance(points[0], (list, tuple)) and len(points) == 2 and isinstance(points[0][0], (int, float)):
        # line
        (x1, y1), (x2, y2) = points
        return ((int(x1 * width), int(y1 * height)), (int(x2 * width), int(y2 * height)))
    # polygon
    poly = [(int(x * width), int(y * height)) for (x, y) in points]
    return poly
