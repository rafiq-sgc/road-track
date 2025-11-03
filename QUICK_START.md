# 🚀 Quick Start Guide - Road Tracker Pro

## TL;DR - Get Running in 3 Steps

```bash
# 1. Install
pip install -r requirements.txt

# 2. Run
uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000

# 3. Open browser
http://localhost:8000
```

---

## What You Get

### ✅ Wrong-Way Detection
- Auto-learns lane direction from traffic flow
- OR use manual direction vectors
- Highlights violators with red border + spotlight
- Saves evidence automatically

### ✅ Other Violations
- Red light (crossing stop line)
- Lane violation (outside lane zones)
- Speeding (with calibration)
- No helmet (optional, needs model)
- Plate reading (optional, needs model)

### ✅ Production Features
- Real-time WebSocket alerts
- Performance metrics (FPS, counts)
- Evidence saving (crops + full frames)
- CSV export
- Alert debouncing (no spam)
- Docker deployment

---

## First Time Setup

### 1. Configure Your Camera ROI

Edit `app/config/roi_config.json`:
/home/sgc/Rafiqul/test4.mp4
```json
{
  "lanes": [
    [[0.1, 0.9], [0.4, 0.6], [0.6, 0.6], [0.9, 0.9]]
  ],
  "lane_directions": [],
  "auto_lane_direction": true,
  "auto_lane_warmup_frames": 180,
  "stop_line": [[0.3, 0.8], [0.7, 0.8]],
  "speed_calib_points": [[0.1, 0.9], [0.4, 0.9]],
  "speed_calib_distance_m": 10.0,
  "speed_limit_kmh": 40.0
}
```

**Coordinates are normalized (0-1)**:
- `0.0` = left/top edge
- `1.0` = right/bottom edge
- Example: `[0.5, 0.5]` = center of frame

### 2. Enable Auto Lane Direction Learning

Set in config:
```json
"auto_lane_direction": true,
"lane_directions": []
```

The system will:
1. Watch traffic for ~6 seconds (180 frames)
2. Compute median flow direction per lane
3. Use that as "forward" direction
4. Flag opposite movers as wrong-way

### 3. Test with Your Video

In the UI:
1. Enter video path: `/path/to/your/video.mp4`
2. Click "Start"
3. Watch for "Learning: X%" indicator
4. Wait for completion (~6s)
5. Violators will be auto-detected

---

## Understanding the UI

### Top Bar
- **🚗 Road Tracker Pro**: Title
- **Green Dot**: WebSocket connected (real-time alerts)
- **Red Dot**: WebSocket disconnected (polling fallback)

### Controls Panel
- **Source Input**: 0 for webcam, or file path
- **▶ Start**: Begin processing
- **⏹ Stop**: Stop processing
- **Signal Dropdown**: Set traffic light state
- **📥 Export CSV**: Download violation history

### Metrics Dashboard
- **FPS**: Frames per second (target: 8-12 on CPU)
- **Detections**: Average objects per frame
- **Violations**: Total count across all types
- **Uptime**: Minutes since start

### Live Stream
- **Green Lines**: Lane boundaries
- **Red Line**: Stop line
- **VIOLATED Label**: Recent violator (3s duration)
- **FOCUS Label**: Wrong-way spotlight (5s duration)
- **FPS Counter**: Top-right corner

### Alerts Panel
- **Filters**: Toggle violation types
- **Badge Colors**: 
  - 🔴 Red = Dangerous (wrong-way, red light, no helmet)
  - 🟡 Yellow = Warning (lane)
  - 🔵 Blue = Info (speeding)
  - 🟢 Green = Info (plate read)
- **Evidence Link**: Click to view saved images

---

## Common Workflows

### Scenario 1: Test with Webcam
```bash
# 1. Run server
uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000

# 2. In UI: enter "0" as source, click Start
# 3. Enable auto-learning in config
# 4. Drive/walk in front of camera both directions
# 5. Check alerts panel for violations
```

### Scenario 2: Analyze Pre-Recorded Video
```bash
# 1. Place video file: /home/sgc/traffic.mp4
# 2. In UI: enter full path, click Start
# 3. Monitor learning progress indicator
# 4. Export CSV when done
# 5. Check violations/ folder for evidence
```

### Scenario 3: Deploy for Production
```bash
# Option A: Docker
docker-compose up -d

# Option B: Systemd
sudo systemctl start road-tracker

# Option C: Screen (quick)
screen -dmS road-tracker uvicorn app.main_v2:app --host 0.0.0.0 --port 8000
```

---

## Calibration Tips

### For Wrong-Way Detection
1. **Use auto-learning** if traffic is mostly correct-direction
2. **Use manual directions** if mixed or complex intersection
3. **Adjust warmup frames** if learning is inaccurate:
   - More frames = more robust, but slower
   - Default 180 frames (~6s at 30fps) works for most cases

### For Speed Detection
1. Measure a known distance on the road (e.g. 10 meters)
2. Find those two points in the video frame
3. Convert to normalized coordinates
4. Set in config:
   ```json
   "speed_calib_points": [[x1, y1], [x2, y2]],
   "speed_calib_distance_m": 10.0
   ```

### For Stop Line
1. Find the line vehicles should stop at
2. Pick two points along that line
3. Normalize coordinates
4. Set in config:
   ```json
   "stop_line": [[x1, y1], [x2, y2]]
   ```

---

## Troubleshooting in 30 Seconds

### Problem: Low FPS (< 5)
**Fix**: Lower video resolution or skip frames

### Problem: Wrong-way not detecting
**Fix**: Check `auto_lane_direction: true` and `lane_directions: []`

### Problem: Too many false alerts
**Fix**: Increase cooldown in `processor_v2.py` line 36: `self.cooldown_seconds = 10.0`

### Problem: WebSocket disconnected
**Fix**: Check browser console, try refresh

### Problem: No evidence saving
**Fix**: `chmod 755 violations/`

---

## Next Steps

1. ✅ Run with your video
2. ✅ Verify wrong-way detection works
3. ✅ Check `violations/` folder for evidence
4. ✅ Export CSV and review violations
5. ✅ Adjust ROI config for your camera
6. ✅ Deploy with Docker for production

**Read full docs:**
- `PRODUCTION_READY_SUMMARY.md` - All features explained
- `DEPLOYMENT_GUIDE.md` - Production deployment
- `PROJECT_SUMMARY.md` - Quick reference

---

## Support

Check logs first:
```bash
# Development mode
# Logs appear in terminal

# Docker
docker-compose logs -f

# Systemd
sudo journalctl -u road-tracker -f
```

Check metrics:
```bash
curl http://localhost:8000/metrics
```

**You're ready to go! 🎉**

