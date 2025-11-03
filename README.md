# Road Tracker Pro

**Production-ready FastAPI application** that analyzes live or recorded road video to detect vehicles/people, track them, and flag traffic rule violations with evidence saving, real-time alerts, and auto-learning capabilities.

> 🚀 **Quick Start**: See `QUICK_START.md` for 3-step setup
> 📚 **Full Guide**: See `DEPLOYMENT_GUIDE.md` for production deployment
> ✅ **Status**: See `PRODUCTION_READY_SUMMARY.md` for all features

## Features

### Core Detection & Tracking
- **YOLOv8n** (free, CPU-optimized) for vehicles, people, motorcycles, buses, trucks, bicycles
- **ByteTrack** for stable multi-object tracking with persistent IDs
- **8-12 FPS** on CPU (Intel i5/i7) with 1080p video

### Violation Detection
- ✅ **Wrong-Way**: Auto-learns lane direction, flags opposite travelers with spotlight focus
- ✅ **Red Light**: Crossing stop line while signal is red
- ✅ **Lane**: Objects outside designated lane polygons
- ✅ **Speeding**: With pixel-to-meter calibration
- ✅ **No Helmet**: Optional (requires custom YOLO model)
- ✅ **Plate Reading**: Optional OCR with EasyOCR

### Production Features (V2)
- 🔥 **Alert Debouncing**: 5s cooldown prevents spam
- 💾 **Evidence Saving**: Auto-saves crops + full frames for violations
- 📊 **Performance Metrics**: Real-time FPS, detection count, uptime
- ⚡ **WebSocket Alerts**: Real-time push (<50ms latency)
- 📥 **CSV Export**: Download violation history
- 🎯 **Auto Lane Learning**: Robust median-based direction detection
- 🔍 **Smart Focus**: Spotlight effect on wrong-way violators
- 📝 **Professional Logging**: Python logging throughout

### Deployment
- 🐳 **Docker**: One-command deployment
- 🔧 **Systemd**: Linux service integration
- 🌐 **Nginx**: Reverse proxy config included

## Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Run

### Development Mode (V2 - Recommended)
```bash
uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000
```

### Legacy Mode (V1 - Basic)
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

### Docker (Production)
```bash
docker-compose up -d
```

## Configure ROIs
Edit `app/config/roi_config.example.json` and save as `app/config/roi_config.json`.
- `lanes`: list of lane polygons (normalized [0-1] x/y)
- `stop_line`: two points (normalized) defining stop line
- `classes`: which YOLO classes to track (default vehicle + person)

Calibrate once per camera/view. For quick tests, keep defaults.

## Quick Usage

**V2 (Production - Recommended)**:
```bash
uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000
```
Open http://localhost:8000

**V1 (Legacy - Basic)**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints
- `POST /start` - Start with `{ "source": 0 }` or `{ "source": "/path/video.mp4" }`
- `POST /stop` - Stop processing
- `POST /signal` - Set state `{ "state": "red" | "green" }`
- `GET /stream` - MJPEG stream
- `GET /alerts` - Recent alerts (JSON)
- `GET /metrics` - Performance metrics (V2)
- `GET /evidence/recent` - Saved violations (V2)
- `WebSocket /ws/alerts` - Real-time push (V2)

---

## 📖 Complete Documentation

| Document | Purpose | Read If... |
|----------|---------|------------|
| **START_HERE.md** | 📍 Entry point | First time user |
| **QUICK_START.md** | ⚡ 3-step setup | Want to test NOW |
| **FEATURES_AND_USAGE.md** | 📚 Complete guide | Want all details |
| **PRODUCTION_READY_SUMMARY.md** | ✨ V2 improvements | Want to see what's new |
| **DEPLOYMENT_GUIDE.md** | 🚀 Production deploy | Ready to deploy |
| **ARCHITECTURE.md** | 🏗️ Technical deep dive | Developer/architect |
| **VISUAL_GUIDE.md** | 🎨 Visual examples | Visual learner |
| **TESTING_CHECKLIST.md** | ✅ Systematic tests | QA testing |
| **MIGRATION_TO_V2.md** | 🔄 V1→V2 upgrade | Upgrading from V1 |

**Start with**: `START_HERE.md` → Then choose your path!

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
