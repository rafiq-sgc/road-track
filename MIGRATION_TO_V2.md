# Migration from V1 to V2

## What Changed

You now have **two versions**:
- `app/main.py` + `app/services/processor.py` - **V1 (Basic)**
- `app/main_v2.py` + `app/services/processor_v2.py` - **V2 (Production-Ready)**

## Quick Migration Steps

### 1. Update Dependencies
```bash
pip install -r requirements.txt
```

New packages:
- `python-dateutil` (for timestamps)
- `pillow` (for image handling)

### 2. Update Config
Add to your `app/config/roi_config.json`:

```json
{
  "auto_lane_direction": true,
  "auto_lane_warmup_frames": 180
}
```

### 3. Run V2
```bash
# Stop V1 if running (Ctrl+C)

# Start V2
uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test
- Open http://localhost:8000
- Check green WebSocket indicator
- Start a video source
- Watch for "Learning: X%" during warmup
- Trigger violations and check `violations/` folder

## What You Gain

| Feature | V1 | V2 |
|---------|----|----|
| Alert Spam | ❌ Every frame | ✅ Debounced (5s) |
| Evidence | ❌ None | ✅ Auto-saved |
| Real-time | Polling (800ms) | WebSocket (<50ms) |
| Metrics | ❌ None | ✅ FPS, counts, uptime |
| CSV Export | ❌ None | ✅ One-click |
| Auto-Learning | Mean (noisy) | Median (robust) |
| Focus Effect | Basic | Gaussian blur |
| Logging | Prints | Python logging |
| Deployment | Manual | Docker ready |

## Backward Compatibility

**V1 still works!** You can run:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

This is useful if you want to compare or if V2 has issues.

## Breaking Changes

None! V2 is fully backward-compatible with your existing config.

## Recommended: Switch Default to V2

If you want V2 as default, rename files:
```bash
# Backup V1
mv app/main.py app/main_v1_backup.py
mv app/services/processor.py app/services/processor_v1_backup.py

# Make V2 default
cp app/main_v2.py app/main.py
cp app/services/processor_v2.py app/services/processor.py
```

Then run normally:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Need Help?

Check in order:
1. `QUICK_START.md` - Fast setup
2. `PRODUCTION_READY_SUMMARY.md` - All features
3. `DEPLOYMENT_GUIDE.md` - Production deployment
4. Logs (terminal or `docker-compose logs -f`)

