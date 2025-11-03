# Road Tracker Pro - Deployment Guide

## Quick Start (Development)

### 1. Install Dependencies
```bash
cd /home/sgc/Rafiqul/road-tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure ROIs
```bash
# Copy example config
cp app/config/roi_config.example.json app/config/roi_config.json

# Edit with your camera's ROI settings
nano app/config/roi_config.json
```

### 3. Run (Development Mode - V2 with all improvements)
```bash
# Use the enhanced version
uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000
```

### 4. Access UI
Open http://localhost:8000

---

## Production Deployment

### Option 1: Docker (Recommended)

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 2: Systemd Service

Create `/etc/systemd/system/road-tracker.service`:

```ini
[Unit]
Description=Road Tracker Pro
After=network.target

[Service]
Type=simple
User=sgc
WorkingDirectory=/home/sgc/Rafiqul/road-tracker
Environment="PATH=/home/sgc/Rafiqul/road-tracker/venv/bin"
ExecStart=/home/sgc/Rafiqul/road-tracker/venv/bin/uvicorn app.main_v2:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable road-tracker
sudo systemctl start road-tracker
sudo systemctl status road-tracker
```

### Option 3: Nginx Reverse Proxy

Create `/etc/nginx/sites-available/road-tracker`:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Change this

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # MJPEG stream
    location /stream {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/road-tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## Configuration

### ROI Configuration (`app/config/roi_config.json`)

```json
{
  "lanes": [
    [[0.1, 0.9], [0.4, 0.6], [0.6, 0.6], [0.9, 0.9]]
  ],
  "lane_directions": [
    [[0.5, 0.95], [0.5, 0.6]]
  ],
  "auto_lane_direction": false,
  "auto_lane_warmup_frames": 180,
  "stop_line": [[0.3, 0.8], [0.7, 0.8]],
  "classes": ["person", "car", "motorcycle", "bus", "truck", "bicycle"],
  "speed_calib_points": [[0.1, 0.9], [0.4, 0.9]],
  "speed_calib_distance_m": 10.0,
  "speed_limit_kmh": 40.0,
  "helmet_model_path": null,
  "plate_model_path": null
}
```

**Key Fields:**
- `lanes`: Array of polygons (normalized 0-1 coordinates)
- `lane_directions`: Direction vectors per lane (start→end)
- `auto_lane_direction`: Enable automatic learning (set to `true` if no manual directions)
- `stop_line`: Two points defining the stop line
- `speed_calib_points`: Two points with known real-world distance
- `speed_calib_distance_m`: Distance in meters between calib points

---

## Features (V2)

### ✅ CPU-Optimized Improvements
1. **Alert Debouncing**: 5s cooldown per track+violation type
2. **Evidence Saving**: Auto-saves crops + full frames to `violations/`
3. **Robust Auto-Learning**: Median-based lane direction detection
4. **Performance Metrics**: Real-time FPS, detection count, uptime
5. **Enhanced Focus**: Smooth spotlight on wrong-way violators
6. **WebSocket Alerts**: Real-time push notifications
7. **CSV Export**: Download violation history
8. **Logging**: Full Python logging with levels
9. **Better UI**: Modern dark theme with metrics dashboard

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main UI |
| `/start` | POST | Start processing `{"source": 0 or "/path"}` |
| `/stop` | POST | Stop processing |
| `/signal` | POST | Set signal `{"state": "red" or "green"}` |
| `/stream` | GET | MJPEG video stream |
| `/alerts` | GET | Recent alerts (JSON) |
| `/metrics` | GET | Performance metrics |
| `/evidence/recent` | GET | Recent violations with evidence |
| `/evidence/{id}` | GET | Specific evidence metadata |
| `/ws/alerts` | WebSocket | Real-time alert push |

---

## Performance (CPU)

**Hardware**: Intel i5/i7 (4-8 cores)
**Video**: 1080p @ 30fps
**Model**: YOLOv8n

| Metric | Value |
|--------|-------|
| FPS | 8-12 |
| CPU Usage | 60-80% |
| Memory | ~800MB |
| Alert Latency | <100ms (WebSocket) |

**Optimization Tips:**
- Lower video resolution (720p) → +40% FPS
- Reduce detection frequency (every 2nd frame) → +50% FPS
- Use YOLOv8n-int8 quantized model → +20% FPS

---

## Troubleshooting

### Issue: Low FPS
- **Solution**: Reduce input resolution, process every N frames
- **Check**: `htop` for CPU bottleneck

### Issue: Wrong-way not detecting
- **Solution**: 
  1. Enable auto-learning: `"auto_lane_direction": true`
  2. Or manually set `lane_directions` matching traffic flow
  3. Increase warmup: `"auto_lane_warmup_frames": 300`

### Issue: Too many false alerts
- **Solution**: Increase debounce cooldown in `processor_v2.py`:
  ```python
  self.cooldown_seconds = 10.0  # Increase from 5.0
  ```

### Issue: Evidence not saving
- **Solution**: Check write permissions on `violations/` folder:
  ```bash
  chmod 755 violations/
  ```

### Issue: WebSocket not connecting
- **Solution**: If behind nginx, ensure WebSocket upgrade headers are set (see nginx config above)

---

## Monitoring

### Logs
```bash
# Docker
docker-compose logs -f

# Systemd
sudo journalctl -u road-tracker -f

# Direct
tail -f /var/log/road-tracker.log
```

### Metrics Endpoint
```bash
curl http://localhost:8000/metrics
```

Response:
```json
{
  "fps": 10.5,
  "avg_process_time_ms": 95.2,
  "avg_detections": 12.3,
  "violations": {
    "wrong_way": 5,
    "red_light_violation": 3,
    "speeding": 2
  },
  "uptime_seconds": 3600
}
```

---

## Maintenance

### Clear Old Evidence
```bash
# Keep last 7 days
find violations/ -type f -mtime +7 -delete
```

### Backup Configuration
```bash
tar -czf backup-$(date +%Y%m%d).tar.gz app/config/ violations/metadata/
```

### Update
```bash
git pull
pip install -r requirements.txt --upgrade
sudo systemctl restart road-tracker
```

---

## Security (Production)

1. **Authentication**: Add API key middleware
2. **HTTPS**: Use Let's Encrypt with nginx
3. **Rate Limiting**: Add FastAPI rate limiter
4. **Privacy**: Consider face/plate blurring

---

## Next Steps

1. Test with your video file
2. Calibrate ROIs for your camera angle
3. Enable auto-learning or set manual lane directions
4. Monitor metrics and adjust thresholds
5. Set up systemd for auto-start
6. Configure nginx for public access (if needed)

For questions, check logs and metrics first!

