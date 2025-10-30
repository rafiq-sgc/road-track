# Road Tracker (Local Dev)

Local FastAPI app that analyzes live or recorded road video to detect vehicles/people, track them, and flag basic rule violations (stop-line on red, lane zone crossing). Streams annotated frames over MJPEG and exposes an alerts API.

## Features (dev)
- YOLOv8n (free, pre-trained) for detection (people/vehicles)
- ByteTrack via Supervision for multi-object tracking
- Zones: lanes (polygons), stop-line (line) loaded from JSON
- Violations (MVP):
  - Red light violation: crossing stop-line while signal==red
  - Lane-zone violation: tracked object outside allowed lane polygon
- Input: webcam (0) or video file path
- Output: MJPEG stream `/stream`, JSON alerts `/alerts`
- Control: start/stop processing, set signal state (`/signal`)

## Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run (dev)
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open http://localhost:8000 in your browser.

## Configure ROIs
Edit `app/config/roi_config.example.json` and save as `app/config/roi_config.json`.
- `lanes`: list of lane polygons (normalized [0-1] x/y)
- `stop_line`: two points (normalized) defining stop line
- `classes`: which YOLO classes to track (default vehicle + person)

Calibrate once per camera/view. For quick tests, keep defaults.

## Usage
- Start webcam: `POST /start` with `{ "source": 0 }`
- Start video: `POST /start` with `{ "source": "/path/to/video.mp4" }`
- Set signal state: `POST /signal` `{ "state": "red" | "green" }`
- Watch stream: GET `/` or `/stream`
- Get alerts: GET `/alerts`
- Stop: `POST /stop`

## Notes
- Speeding requires calibration (homography) + FPS → left as extension.
- Helmet/no-helmet requires a custom model (free to train; production may use paid APIs/models for better accuracy).
- License plate recognition is out-of-scope for MVP; can be added with open-source OCR (e.g., PaddleOCR) or paid APIs in production.

## Production Considerations (paid or advanced)
- GPU inference (NVIDIA) via CUDA; consider paid managed inference or Triton
- Higher-accuracy models (YOLOv8m/l or SAM/RT-DETR) may need GPUs
- Stream ingestion at scale (RTSP fan-in), Kafka, Redis streams, object storage for clips
- Edge deployments on Jetson/Coral; model quantization (TensorRT/ONNX, INT8)
- Advanced rule engine (trajectory, U-turn, wrong-way, speed) with proper calibration
- Privacy: face/plate blurring, data retention policies

License: MIT
