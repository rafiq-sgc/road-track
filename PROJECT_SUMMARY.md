## Road Tracker - Project Summary

### What it does
- Analyzes live or recorded road video
- Detects and tracks vehicles/people (YOLOv8 + ByteTrack)
- Flags violations and shows them on a live stream
- Provides a readable alerts feed (filterable) in the UI

### Violations supported
- Red light violation (crossing stop line while red)
- Lane violation (outside lane polygons)
- Wrong-way travel (against configured lane direction)
- Speeding (with calibration)
- Optional: No-helmet (custom YOLO model)
- Optional: Plate read (YOLO plate model + EasyOCR; informational)

### Tech stack
- Python, FastAPI, Uvicorn, OpenCV
- Ultralytics YOLOv8, Supervision (ByteTrack)
- EasyOCR (optional, for plates)

### Run locally
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open http://localhost:8000

### UI usage
- Controls: set source (0 for webcam or absolute video path), Start/Stop, Signal state
- Live stream on left; Alerts panel on right with filters and auto-scroll

### API endpoints
- POST /start { "source": 0 | "/abs/path/video.mp4" }
- POST /stop
- POST /signal { "state": "red" | "green" }
- GET /stream (MJPEG)
- GET /alerts (JSON)

### Configuration (app/config/roi_config.json)
- lanes: list of polygons (normalized [0–1])
- lane_directions: list of 2-point normalized vectors (start→end)
- stop_line: 2 points normalized
- classes: YOLO classes to track
- speed_calib_points: 2 normalized points with known real distance
- speed_calib_distance_m: meters between the points
- speed_limit_kmh: threshold for speeding
- helmet_model_path: optional YOLO model path
- plate_model_path: optional YOLO model path

Tip: copy `app/config/roi_config.example.json` to `app/config/roi_config.json` and adjust.

### How violations are computed (brief)
- Red light: center crosses stop line while signal=red
- Lane: center not inside any lane polygon
- Wrong-way: motion vector persistently opposite lane direction (dot product < 0 threshold)
- Speed: pixel speed → m/s via calibration → km/h > limit
- No-helmet: optional head crop via YOLO; alert on negative
- Plate: optional YOLO plate + EasyOCR (informational)

### Visual overlays
- Lanes (green), stop line (red)
- On violation, track shows a red "VIOLATED" label for ~3s
- Wrong-way adds a red arrow and label

### Production notes
- Use GPU and larger models for accuracy/performance
- Consider managed inference / Triton (paid)
- Add storage for clips, messaging, calibration UI, privacy features

License: MIT
