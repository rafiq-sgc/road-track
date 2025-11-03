# Road Tracker Pro - Complete Features & Usage Guide

## 🎯 Your Main Goal: Detect Opposite Direction Violators

### How It Works

1. **Lane Definition**: Configure lane polygons in `roi_config.json`
2. **Direction Learning**: System observes traffic flow for ~6 seconds
3. **Detection**: Computes motion vector for each tracked object
4. **Comparison**: Compares object motion vs. learned lane direction
5. **Alert**: If persistently opposite (10+ frames), flags as WRONG-WAY
6. **Highlight**: Spotlight effect + "VIOLATED" + "WRONG WAY" labels
7. **Evidence**: Automatically saves crop + full frame to `violations/`

### Visual Feedback on Stream

When wrong-way violation occurs:
```
┌─────────────────────────────────────┐
│  [Dimmed Background]                │
│                                     │
│    ┏━━━━━━━━━━━━━┓                 │
│    ┃ 🚗 FOCUS    ┃ ← Red border    │
│    ┃ VIOLATED    ┃ ← Labels        │
│    ┃ WRONG WAY   ┃ ← Direction     │
│    ┃      ↑      ┃ ← Motion arrow  │
│    ┗━━━━━━━━━━━━━┛                 │
│                                     │
└─────────────────────────────────────┘
```

Effect lasts 5 seconds so operators can clearly see the violator.

---

## 📋 All Violation Types

### 1. Wrong-Way (Opposite Direction) ⭐ PRIMARY
**Trigger**: Object moves opposite to lane direction
**Duration**: Must persist 10+ frames (~0.3s)
**Visual**: Red arrow, "WRONG WAY", spotlight, "VIOLATED"
**Alert**: `{"type": "wrong_way", "lane": 0, "speed_pxps": 45.2}`
**Evidence**: ✅ Saved

### 2. Red Light Violation
**Trigger**: Object crosses stop line while signal is red
**Visual**: "RED LIGHT VIOLATION"
**Alert**: `{"type": "red_light_violation", "cx": 640, "cy": 480}`
**Evidence**: ✅ Saved

### 3. Lane Violation
**Trigger**: Object center outside all lane polygons
**Visual**: "LANE VIOLATION" (orange text)
**Alert**: `{"type": "lane_violation", "cx": 100, "cy": 200}`
**Evidence**: ✅ Saved

### 4. Speeding
**Trigger**: Speed exceeds `speed_limit_kmh` (requires calibration)
**Visual**: "SPEED 65.3 km/h" (blue text)
**Alert**: `{"type": "speeding", "speed_kmh": 65.3}`
**Evidence**: ✅ Saved

### 5. No Helmet (Optional)
**Trigger**: Motorcycle/bicycle without helmet detected
**Requires**: Custom YOLO model at `helmet_model_path`
**Visual**: "NO HELMET"
**Alert**: `{"type": "no_helmet"}`
**Evidence**: ✅ Saved

### 6. Plate Read (Informational)
**Trigger**: License plate detected and read
**Requires**: YOLO plate model + EasyOCR
**Visual**: Plate text in green
**Alert**: `{"type": "plate_read", "text": "ABC1234"}`
**Evidence**: ❌ Not violation, informational only

---

## 🎨 UI Guide

### Main Interface

```
┌─────────────────────────────────────────────────────────┐
│ 🚗 Road Tracker Pro              [●] Connected          │
├─────────────────────────────────────────────────────────┤
│ Controls                                                │
│ [0 or /path/video.mp4] [▶ Start] [⏹ Stop]             │
│ Signal: [green ▼] [Apply] [📥 Export CSV]              │
├─────────────────────────────────────────────────────────┤
│ Performance Metrics                                     │
│ ┌──────┬──────────┬────────────┬────────┐             │
│ │ 10.2 │   12.3   │     15     │   45   │             │
│ │ FPS  │Detection │ Violations │ Uptime │             │
│ └──────┴──────────┴────────────┴────────┘             │
├────────────────────────┬────────────────────────────────┤
│ Live Stream            │ Alerts (15)                    │
│ ┌────────────────────┐ │ ☑ Wrong-way ☑ Red Light       │
│ │                    │ │ ☑ Lane ☑ Speed ☑ Helmet       │
│ │   [Video Stream]   │ │                                │
│ │   FPS: 10.2       │ │ ┌──────────────────────────┐   │
│ │                    │ │ │ 🔄 Wrong-way             │   │
│ └────────────────────┘ │ │ 10:45:32 AM              │   │
│                        │ │ Track: #42               │   │
│                        │ │ {"lane": 0, ...}         │   │
│                        │ │ [View Evidence]          │   │
│                        │ └──────────────────────────┘   │
│                        │ ...more alerts...              │
└────────────────────────┴────────────────────────────────┘
```

### Controls Explained

| Control | Purpose |
|---------|---------|
| Source Input | `0` for webcam, `/path/file.mp4` for video |
| ▶ Start | Begin processing |
| ⏹ Stop | Stop processing |
| Signal Dropdown | Set traffic light state |
| Apply | Update signal |
| 📥 Export CSV | Download all alerts as CSV |

### Metrics Dashboard

| Metric | Meaning |
|--------|---------|
| FPS | Processing speed (target: 8-12) |
| Detection | Avg objects per frame |
| Violations | Total violations detected |
| Uptime | Minutes since start |

### Alert Panel

- **Filters**: Toggle which violations to show
- **Badges**: Color-coded by severity
- **Timestamp**: When violation occurred
- **Track ID**: Unique object identifier
- **Info**: JSON details (speed, lane, coords)
- **View Evidence**: Link to saved images

---

## 🔧 Configuration Deep Dive

### Lane Configuration

**What is it**: Defines valid road areas
**Format**: Array of polygons with normalized coordinates

```json
"lanes": [
  [[0.1, 0.9], [0.4, 0.6], [0.6, 0.6], [0.9, 0.9]]
]
```

**How to set**:
1. Take a screenshot of your video
2. Identify lane boundaries
3. Pick 4+ corner points (clockwise or counter-clockwise)
4. Normalize: `x_norm = x_pixel / frame_width`
5. Normalize: `y_norm = y_pixel / frame_height`

**Multi-lane example**:
```json
"lanes": [
  [[0.0, 0.9], [0.0, 0.5], [0.3, 0.5], [0.3, 0.9]],  # Left lane
  [[0.3, 0.9], [0.3, 0.5], [0.6, 0.5], [0.6, 0.9]]   # Right lane
]
```

### Lane Direction

**Option A: Auto-Learning (Recommended)**
```json
"auto_lane_direction": true,
"lane_directions": []
```

System learns from traffic flow automatically.

**Option B: Manual**
```json
"auto_lane_direction": false,
"lane_directions": [
  [[0.5, 0.95], [0.5, 0.6]]  # Bottom→Top direction
]
```

Each direction is two points: start → end of intended flow.

**How to choose manual direction**:
1. Observe normal traffic flow in your video
2. Pick two points along the centerline
3. Order: where traffic comes FROM → where it goes TO
4. Example: If cars move from bottom of screen to top:
   - Start: `[0.5, 0.9]` (center-bottom)
   - End: `[0.5, 0.5]` (center-middle)

### Speed Calibration

**Purpose**: Convert pixel movement to real-world speed

```json
"speed_calib_points": [[0.1, 0.9], [0.4, 0.9]],
"speed_calib_distance_m": 10.0,
"speed_limit_kmh": 40.0
```

**How to calibrate**:
1. Measure a known distance on the road (e.g., 10 meters)
2. Find those two points in the video frame
3. Normalize coordinates
4. Set the real distance in meters
5. Set speed limit in km/h

**Example**: Two lane markers 10m apart
- Point 1: `[0.1, 0.9]` (left-bottom)
- Point 2: `[0.4, 0.9]` (right-bottom, 10m away)
- Distance: `10.0` meters
- Limit: `40.0` km/h

---

## 💾 Evidence Storage

### Folder Structure

```
violations/
├── crops/
│   └── wrong_way_42_20231102_104532_123.jpg
├── fullframes/
│   └── wrong_way_42_20231102_104532_123.jpg
└── metadata/
    └── wrong_way_42_20231102_104532_123.json
```

### Metadata Format

```json
{
  "timestamp": "20231102_104532_123",
  "violation_type": "wrong_way",
  "track_id": 42,
  "bbox": [320, 240, 480, 360],
  "crop_path": "crops/wrong_way_42_20231102_104532_123.jpg",
  "frame_path": "fullframes/wrong_way_42_20231102_104532_123.jpg",
  "lane": 0,
  "speed_pxps": 45.2
}
```

### Usage

**API**: `GET /evidence/recent?limit=50`
**Returns**: Array of metadata for recent violations

**Individual**: `GET /evidence/{evidence_id}`
**Returns**: Specific violation metadata

**Files**: Served at `/violations/crops/{filename}`

---

## 📊 Metrics API

### Endpoint: `GET /metrics`

**Response**:
```json
{
  "fps": 10.5,
  "avg_process_time_ms": 95.2,
  "avg_detections": 12.3,
  "violations": {
    "wrong_way": 5,
    "red_light_violation": 3,
    "speeding": 2,
    "lane_violation": 1,
    "no_helmet": 0,
    "plate_read": 8
  },
  "uptime_seconds": 3600
}
```

**Usage**:
- Monitor performance in production
- Alert if FPS drops below threshold
- Track violation trends over time

---

## ⚡ WebSocket Usage

### Connect
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/alerts');

ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => {
  const alert = JSON.parse(e.data);
  console.log('New violation:', alert);
};
```

### Alert Format
```json
{
  "ts": 1698931232.123,
  "type": "wrong_way",
  "track_id": 42,
  "info": {"lane": 0, "speed_pxps": 45.2},
  "evidence_id": "wrong_way_42_20231102_104532_123"
}
```

### Use Cases
- Real-time dashboard updates
- Mobile app notifications
- External system integration
- Sound/visual alarms

---

## 🎛️ Tuning Parameters

### In Code (`processor_v2.py`)

**Alert Cooldown** (Line 36):
```python
self.cooldown_seconds = 5.0  # Adjust: 3-10 seconds
```

**Wrong-Way Persistence** (Line 251):
```python
if speed_pxps >= speed_min and dot < -0.5 * speed_pxps:
    self.wrong_way_counter[track_id] += 1
else:
    self.wrong_way_counter[track_id] = 0

if self.wrong_way_counter.get(track_id, 0) >= 10:  # Adjust: 5-20 frames
```

**Minimum Speed** (Line 250):
```python
speed_min = 30.0  # Adjust: 20-50 px/s depending on FPS and resolution
```

**Track History Window** (Line 235):
```python
hist = deque(maxlen=12)  # Adjust: 8-20 samples
```

### In Config (`roi_config.json`)

**Auto-Learning Warmup**:
```json
"auto_lane_warmup_frames": 180  # 120-360 frames
```

**Speed Limit**:
```json
"speed_limit_kmh": 40.0  # Your road's limit
```

---

## 📱 Public Awareness Use Cases

### Use Case 1: Intersection Monitoring
**Setup**:
- Fixed camera at busy intersection
- Auto-learning enabled
- Public display showing live stream
- Daily violation count on screen

**Implementation**:
1. Mount camera overhead
2. Configure lanes for all directions
3. Enable auto-learning
4. Display stream on large screen
5. Show violation statistics

### Use Case 2: School Zone Safety
**Setup**:
- Monitor school zone crosswalk
- Detect wrong-way drivers
- Alert security in real-time

**Implementation**:
1. Configure stop line at crosswalk
2. Set speed limit low (20-30 km/h)
3. WebSocket alerts to security app
4. Save evidence for enforcement

### Use Case 3: Highway Exit Violations
**Setup**:
- Detect vehicles entering exit ramp wrong way
- Critical safety issue

**Implementation**:
1. Configure lane for exit ramp
2. Set direction: exit → highway
3. Focus effect highlights violators
4. SMS alert to highway patrol (custom integration)

---

## 🔍 Advanced Features

### Multi-Camera Support (Future)
Current: Single camera
To add: Modify `main_v2.py` to support multiple processor instances with IDs

### Violation Clips (Future)
Current: Saves single frame
To add: Save 3-5 second video clip around violation timestamp

### Analytics Dashboard (Future)
Current: Real-time metrics
To add: Historical charts, heatmaps, peak hours analysis

### Mobile App (Future)
Current: Web UI only
To add: Flutter/React Native app consuming WebSocket API

---

## 🛠️ Developer Guide

### Adding a New Violation Type

**Step 1**: Add detection logic in `processor_v2.py`
```python
# In _run_loop, around line 260
if some_condition_met:
    self._emit_alert("new_violation_type", track_id, {"detail": "info"}, frame, bbox_tuple)
    cv2.putText(frame, "NEW VIOLATION", (x, y), ...)
```

**Step 2**: Update UI badge map in `main_v2.py`
```javascript
const map = {
  // ... existing ...
  new_violation_type: ['b-danger', '🚫 New Violation']
};
```

**Step 3**: Add filter checkbox in HTML
```html
<label><input type="checkbox" class="flt" value="new_violation_type" checked /> New</label>
```

### Extending Evidence Manager

**Save additional data**:
```python
# In evidence.py, _save_violation
meta["custom_field"] = custom_value
```

**Add new evidence type**:
```python
# Save video clip instead of image
self.evidence_manager.save_video_clip(kind, track_id, video_buffer, metadata)
```

---

## 📊 Performance Optimization (CPU)

### Option 1: Reduce Resolution
```python
# In processor_v2.py, after frame = self.cap.read()
frame = cv2.resize(frame, (1280, 720))  # From 1920x1080
```
**Result**: +40% FPS

### Option 2: Skip Frames
```python
# Process every 2nd frame
if frame_idx % 2 == 0:
    # ... detection logic ...
else:
    # Re-use previous detections
```
**Result**: +50% FPS

### Option 3: Reduce Detection Classes
```python
# Only detect vehicles (exclude person)
ALLOWED_CLASS_NAMES = {"car", "motorcycle", "bus", "truck"}
```
**Result**: +10-15% FPS

### Option 4: Lower JPEG Quality
```python
# In mjpeg_generator
cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])  # From 80
```
**Result**: -20% bandwidth, slight quality loss

---

## 🔐 Security Best Practices

### For Public Deployment

1. **Authentication**:
```python
# Add API key middleware
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_key(api_key: str = Security(api_key_header)):
    if api_key != "your-secret-key":
        raise HTTPException(403)
```

2. **Rate Limiting**:
```python
# Add slowapi
from slowapi import Limiter, _rate_limit_exceeded_handler
limiter = Limiter(key_func=lambda: "global")
app.add_exception_handler(429, _rate_limit_exceeded_handler)
```

3. **HTTPS**: Use Let's Encrypt + nginx

4. **Privacy**: Blur faces/plates before displaying publicly

---

## 📈 Production Monitoring

### Health Check
```bash
curl http://localhost:8000/metrics
```

If FPS < 5 → Performance issue
If violations suddenly spike → Check calibration

### Log Monitoring
```bash
# Watch for errors
tail -f /var/log/road-tracker.log | grep ERROR

# Count violations per hour
grep "Alert: wrong_way" /var/log/road-tracker.log | wc -l
```

### Disk Space
```bash
# Check evidence storage
du -sh violations/

# Alert if > 10GB
```

---

## ✅ Production Readiness Checklist

### Before Deployment
- [ ] Tested with real traffic video (1+ hour)
- [ ] FPS stable above 8
- [ ] Wrong-way detection accuracy > 90%
- [ ] Evidence saves correctly
- [ ] WebSocket stable (no disconnects)
- [ ] Metrics API responsive
- [ ] CSV export works
- [ ] Auto-learning completes successfully
- [ ] Focus effect works smoothly
- [ ] No memory leaks (monitor for 24+ hours)

### Deployment
- [ ] Docker container builds
- [ ] Systemd service starts on boot
- [ ] Nginx reverse proxy configured
- [ ] SSL certificate installed (if public)
- [ ] Firewall rules set
- [ ] Backup script scheduled
- [ ] Log rotation configured
- [ ] Monitoring alerts set up

### Post-Deployment
- [ ] Test from external network
- [ ] Monitor logs for errors
- [ ] Check disk usage daily
- [ ] Verify evidence accumulation
- [ ] Validate violation accuracy weekly
- [ ] Collect user feedback

---

## 🎓 Training Tips

### For Accurate Auto-Learning

**Do**:
- Use video with 80%+ correct-direction traffic
- Let warmup complete fully (watch progress bar)
- Use daytime footage (better detection)
- Keep camera angle consistent

**Don't**:
- Start learning during heavy violations
- Change camera angle mid-session
- Use low-light video for initial learning
- Interrupt learning process

### For Manual Direction Setting

**Best Practice**:
1. Watch 1-2 minutes of normal traffic
2. Note primary flow direction
3. Draw direction vector matching that flow
4. Test with known opposite-direction vehicle
5. Adjust if needed

---

## 🎯 Success Metrics

Your deployment is successful if:

1. ✅ **Accuracy**: 90%+ of wrong-way detections are correct
2. ✅ **Performance**: FPS stays above 8 during peak traffic
3. ✅ **Reliability**: No crashes for 24+ hours continuous operation
4. ✅ **Latency**: Alerts appear within 100ms (WebSocket)
5. ✅ **Evidence**: All violations have saved images
6. ✅ **Usability**: Operators can identify violators within 2 seconds of alert

---

## 📞 Support & Troubleshooting

### Common Issues & Fixes

| Issue | Solution |
|-------|----------|
| FPS too low | Reduce resolution to 720p |
| Wrong-way false positives | Increase persistence frames to 15-20 |
| Missing violations | Lower speed_min threshold |
| WebSocket disconnects | Check nginx WebSocket headers |
| Evidence not saving | `chmod 755 violations/` |
| Auto-learning inaccurate | Increase warmup_frames to 300 |

### Debug Mode

Enable verbose logging:
```python
# In main_v2.py, change logging level
logging.basicConfig(level=logging.DEBUG)
```

---

## 🌟 Best Practices Summary

1. **Always use V2** (`main_v2.py`) for production
2. **Enable auto-learning** for fastest deployment
3. **Monitor metrics** regularly (FPS, violations)
4. **Review evidence** weekly for calibration tuning
5. **Export CSV** for reports and analysis
6. **Set up alerts** for critical violations (wrong-way)
7. **Clean old evidence** to manage disk space
8. **Update thresholds** based on real-world performance

---

**You're ready for production deployment! 🚀**

Start testing with:
```bash
uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000
```

