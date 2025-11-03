# How to Disable Lane Violation (Keep Only Wrong-Way)

## Problem

You're still getting `lane_violation` alerts because some vehicles are outside the lane polygons (possibly on footpath or edges).

## Solution: Focus ONLY on Wrong-Way Detection

### Option 1: Make Lanes Cover Entire Frame (Simplest)

Edit `app/config/roi_config.json`:

```json
{
  "lanes": [
    [[0.0, 1.0], [0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]
  ],
  "lane_directions": [],
  "auto_lane_direction": true,
  "auto_lane_warmup_frames": 240,
  "stop_line": null,
  "classes": ["car", "motorcycle", "bus", "truck", "bicycle"],
  "speed_calib_points": null,
  "speed_calib_distance_m": null,
  "speed_limit_kmh": null,
  "helmet_model_path": null,
  "plate_model_path": null
}
```

**What this does**:
- ONE giant lane covering the entire frame
- No vehicles can be "outside" lanes
- Only wrong-way detection will trigger
- System learns single direction for entire road

### Option 2: Comment Out Lane Violation Code

Edit `app/services/processor_v2.py` around line 376-381:

```python
# # Lane violation (outside all lanes)
# if lane_contours and lane_index == -1:
#     inside_any = any(cv2.pointPolygonTest(cnt, (cx, cy), False) >= 0 for cnt in lane_contours)
#     if not inside_any:
#         self._emit_alert("lane_violation", track_id, {"cx": int(cx), "cy": int(cy)}, frame, bbox_tuple)
#         cv2.putText(frame, "LANE VIOLATION", (int(cx), min(h - 4, int(cy) + 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
```

**What this does**:
- Keeps your two-lane config
- Disables lane violation checking
- Only wrong-way will trigger

---

## Recommended: Option 1

Use the single-lane config above. This way:
- ✅ Simple configuration
- ✅ No lane violations at all
- ✅ Only wrong-way detection
- ✅ Auto-learns one dominant direction
- ✅ Flags anyone going opposite

---

## After Changing Config

```bash
# Restart server
uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000

# Test again
# Enter video path, click Start
# Wait for learning to complete
# Only wrong-way violations should appear now!
```

---

## Why This Works Better

### Your Use Case
**Goal**: Detect vehicles going opposite to traffic flow
**Don't need**: Lane boundaries, footpath detection

### Simple Config
- ONE lane = entire road
- System learns: "Most traffic goes →"
- Anyone going ← = WRONG-WAY
- No false positives from edge cases

### Result
- Clean alerts (only wrong-way)
- Large violator panel shows only real violations
- Perfect for public display!

---

## Test It

1. Apply Option 1 config (single large lane)
2. Restart server
3. Start video
4. Wait for learning
5. **Verify**: No more lane_violation spam
6. **Verify**: Only wrong-way appears in violator panel

**This should solve your issue completely!**

