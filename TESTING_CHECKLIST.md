# Testing Checklist - Road Tracker Pro V2

## Pre-Test Setup

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Copy config: `cp app/config/roi_config.example.json app/config/roi_config.json`
- [ ] Enable auto-learning: Set `"auto_lane_direction": true` in config
- [ ] Start server: `uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000`
- [ ] Open UI: http://localhost:8000

---

## Basic Functionality Tests

### Video Input
- [ ] Test webcam: Enter `0`, click Start
- [ ] Test video file: Enter `/path/to/video.mp4`, click Start
- [ ] Verify stream appears
- [ ] Check FPS counter shows on stream

### UI Controls
- [ ] Signal dropdown works (green/red)
- [ ] Stop button works
- [ ] WebSocket shows green dot (connected)
- [ ] Metrics dashboard updates every 2s

---

## Wrong-Way Detection (Primary Goal)

### Auto-Learning Mode
- [ ] Start video with mostly correct-direction traffic
- [ ] Verify "Learning: X%" appears on stream
- [ ] Wait for learning complete (~6 seconds)
- [ ] Introduce opposite-direction vehicle/person
- [ ] **VERIFY**: System flags with "WRONG WAY" label
- [ ] **VERIFY**: Red arrow shows motion direction
- [ ] **VERIFY**: "VIOLATED" label appears
- [ ] **VERIFY**: Focus spotlight effect activates (dimmed background)
- [ ] **VERIFY**: Alert appears in right panel instantly
- [ ] **VERIFY**: Badge shows "🔄 Wrong-way"

### Manual Direction Mode
- [ ] Set `"auto_lane_direction": false` in config
- [ ] Set `"lane_directions": [[[0.5, 0.9], [0.5, 0.5]]]`
- [ ] Restart server
- [ ] Verify wrong-way detection works without learning phase

---

## Other Violations

### Red Light
- [ ] Set signal to RED
- [ ] Object crosses red stop line
- [ ] **VERIFY**: "RED LIGHT VIOLATION" label
- [ ] **VERIFY**: Alert type `red_light_violation`

### Lane Violation
- [ ] Object moves outside green lane polygon
- [ ] **VERIFY**: "LANE VIOLATION" label
- [ ] **VERIFY**: Alert appears

### Speeding
- [ ] Configure `speed_calib_points` and `speed_limit_kmh`
- [ ] Object exceeds limit
- [ ] **VERIFY**: "SPEED XX km/h" label
- [ ] **VERIFY**: Alert shows speed value

---

## Evidence Saving

- [ ] Trigger any violation
- [ ] Check `violations/crops/` has crop image
- [ ] Check `violations/fullframes/` has full frame
- [ ] Check `violations/metadata/` has JSON file
- [ ] Open metadata JSON, verify structure
- [ ] Click evidence link in UI alert
- [ ] Verify metadata displays

---

## Performance & Metrics

- [ ] Metrics dashboard shows FPS > 5
- [ ] Detections counter updates
- [ ] Violations counter increments on alerts
- [ ] Uptime shows correctly
- [ ] API endpoint works: `curl http://localhost:8000/metrics`

---

## Alert System

### Debouncing
- [ ] Same track triggers same violation
- [ ] Verify only ONE alert per 5 seconds (not every frame)
- [ ] Verify cooldown works

### WebSocket
- [ ] Trigger violation
- [ ] Alert appears instantly (<100ms)
- [ ] Disconnect WebSocket (network tab)
- [ ] Verify red dot shows "Disconnected"
- [ ] Refresh page
- [ ] Verify reconnects (green dot)

### Export
- [ ] Trigger 5+ violations
- [ ] Click "Export CSV" button
- [ ] Verify CSV downloads
- [ ] Open CSV, verify columns: Timestamp, Type, Track ID, Info

---

## Focus Effect

- [ ] Trigger wrong-way violation
- [ ] **VERIFY**: Background dims smoothly
- [ ] **VERIFY**: Violator remains bright
- [ ] **VERIFY**: Red border around violator
- [ ] **VERIFY**: "FOCUS" label shows
- [ ] **VERIFY**: Effect lasts ~5 seconds
- [ ] **VERIFY**: Frame returns to normal after

---

## Edge Cases

### No Detections
- [ ] Point camera at empty scene
- [ ] Verify no crashes
- [ ] Verify metrics show 0 detections

### Video End
- [ ] Play short video to completion
- [ ] Verify processing stops gracefully
- [ ] Verify no error messages

### Invalid Source
- [ ] Enter invalid path `/nonexistent.mp4`
- [ ] Click Start
- [ ] **VERIFY**: Error message appears
- [ ] Verify server doesn't crash

### Stop During Processing
- [ ] Start video
- [ ] Immediately click Stop
- [ ] Verify stops cleanly
- [ ] Verify can restart

---

## Auto Lane Direction Learning

### Accuracy Test
- [ ] Use video with 80%+ traffic going forward
- [ ] Enable auto-learning
- [ ] Let warmup complete
- [ ] Introduce 1-2 opposite-direction vehicles
- [ ] **VERIFY**: System correctly identifies them as wrong-way
- [ ] **VERIFY**: Majority forward traffic is NOT flagged

### Robustness Test
- [ ] Use video with 10-20% wrong-way during warmup
- [ ] Enable auto-learning (median should handle outliers)
- [ ] Verify learned direction still follows majority
- [ ] Verify outliers during warmup don't corrupt learning

---

## Performance Benchmarks

Test on your hardware and note:

| Metric | Target | Your Result |
|--------|--------|-------------|
| FPS (1080p) | 8-12 | ___ |
| FPS (720p) | 12-18 | ___ |
| CPU Usage | 60-80% | ___ |
| Memory | <1GB | ___ |
| Alert Latency | <100ms | ___ |
| Evidence Save Time | <50ms | ___ |

---

## Deployment Tests

### Docker
- [ ] `docker-compose build` succeeds
- [ ] `docker-compose up -d` starts container
- [ ] Access http://localhost:8000
- [ ] Check logs: `docker-compose logs -f`
- [ ] Verify violations saved in volume
- [ ] Stop: `docker-compose down`

### Systemd (if setting up)
- [ ] Service starts: `sudo systemctl start road-tracker`
- [ ] Service auto-restarts on crash
- [ ] Logs work: `sudo journalctl -u road-tracker -f`
- [ ] Service starts on boot: `sudo systemctl enable road-tracker`

---

## Final Checks

- [ ] README is clear and accurate
- [ ] All documentation files created
- [ ] No syntax errors in code
- [ ] Logs show no warnings/errors
- [ ] All violation types work
- [ ] Evidence saving works
- [ ] WebSocket connects
- [ ] Export works
- [ ] Auto-learning works
- [ ] Focus effect works

---

## Success Criteria

✅ **Your app is production-ready when**:

1. Wrong-way detection correctly identifies opposite-direction travelers
2. Evidence is automatically saved for all violations
3. WebSocket provides real-time alerts (<100ms)
4. FPS stays above 8 on your target hardware
5. No crashes during 1+ hour of continuous operation
6. CSV export contains accurate violation history
7. Docker deployment works end-to-end

---

## Known Limitations (CPU Mode)

- FPS limited to 8-12 on 1080p (use 720p for better performance)
- Helmet/plate models may be slow (disabled by default)
- Auto-learning needs ~6s warmup
- Focus effect has slight frame delay on very slow CPUs

**All acceptable for production deployment with CPU-only hardware!**

---

## Next: Public Awareness Campaign

Once testing is complete, you can:

1. Deploy at intersection with overhead camera
2. Display live stream on public screen
3. Show violation count statistics
4. Use saved evidence for awareness materials
5. Export CSV for weekly/monthly reports

**Good luck with testing! 🎉**

