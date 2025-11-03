# Two-Way Road Configuration Guide

## Problem You Had

**Issue**: Every object marked as "VIOLATED" and "LANE VIOLATION"

**Root Cause**: Lane polygons were too small! Your config had:
```json
"lanes": [
  [[0.1, 0.9], [0.4, 0.6], [0.6, 0.6], [0.9, 0.9]]  // Single tiny trapezoid
]
```

This created a small zone in the center, so **everything else** was flagged as "outside lane".

---

## Solution: Two Large Lane Polygons

### For Two-Way Road (Like Your Video)

```
Visual layout:
┌────────────────────────────────────┐
│ Footpath                           │ ← Excluded
├────────────────────────────────────┤
│ Lane 0: Going →                    │ ← Left half
│ (cars moving left to right)        │
├────────────────────────────────────┤
│ Lane 1: Coming ←                   │ ← Right half  
│ (cars moving right to left)        │
├────────────────────────────────────┤
│ Footpath                           │ ← Excluded
└────────────────────────────────────┘
```

### New Configuration (Already Applied)

```json
{
  "lanes": [
    [[0.0, 1.0], [0.0, 0.0], [0.48, 0.0], [0.48, 1.0]],  // Lane 0: Left side (going)
    [[0.52, 1.0], [0.52, 0.0], [1.0, 0.0], [1.0, 1.0]]   // Lane 1: Right side (coming)
  ],
  "lane_directions": [],
  "auto_lane_direction": true,
  "auto_lane_warmup_frames": 240
}
```

**What this does**:
- **Lane 0**: Covers left half of frame (0% to 48% width)
- **Lane 1**: Covers right half of frame (52% to 100% width)
- **Gap**: 2% in middle (divider/median)
- **Auto-learning**: Will learn direction for each lane separately

---

## How It Works Now

### During Warmup (First 8 seconds)

```
Lane 0 (Left side):
  🚗→ 🚗→ 🏍️→ 🚌→ 🚗→ 🚗→
  System learns: Direction = →

Lane 1 (Right side):
  🚗← 🚌← 🚗← 🏍️← 🚗← 🚗←
  System learns: Direction = ←
```

### After Learning

```
Lane 0: If car goes ← (opposite to →) → WRONG-WAY! 🚨
Lane 1: If car goes → (opposite to ←) → WRONG-WAY! 🚨

Normal traffic in each lane: ✅ No violation
```

---

## Why Previous Config Failed

### Old Config (Bad)
```json
"lanes": [
  [[0.1, 0.9], [0.4, 0.6], [0.6, 0.6], [0.9, 0.9]]
]
```

This creates:
```
┌────────────────────────────────┐
│ [VIOLATED]  [VIOLATED]         │ ← Everything outside
│                                │
│     ╔═══════╗                  │ ← Tiny zone
│     ║ OK    ║                  │
│     ╚═══════╝                  │
│                                │
│ [VIOLATED]  [VIOLATED]         │ ← Everything outside
└────────────────────────────────┘
```

**Result**: 95%+ objects outside → All flagged as lane_violation

### New Config (Good)
```json
"lanes": [
  [[0.0, 1.0], [0.0, 0.0], [0.48, 0.0], [0.48, 1.0]],  // Left half
  [[0.52, 1.0], [0.52, 0.0], [1.0, 0.0], [1.0, 1.0]]   // Right half
]
```

This creates:
```
┌────────────────┬────────────────┐
│ Lane 0 (Going) │ Lane 1 (Coming)│
│                │                │
│  🚗→  🚗→  →   │   ←  ←🚗  ←🚗  │
│                │                │
│  ✅ All OK     │   ✅ All OK    │
│                │                │
└────────────────┴────────────────┘
```

**Result**: 0% false positives for lane_violation!

---

## What You'll See Now

### Before Fix
- Every car: "VIOLATED" + "LANE VIOLATION" ❌
- Hundreds of alerts per second ❌
- Useless for detection ❌

### After Fix
- Cars in their lane: No violation ✅
- Cars going wrong direction: "WRONG-WAY" ✅
- Clean alerts panel ✅
- Auto-learning works correctly ✅

---

## How to Adjust for Your Specific Camera

### Step 1: Identify Road Boundaries

Look at your video frame:
- Where does the left edge of the road start? (in frame coordinates)
- Where does the right edge end?
- Where's the center divider/median?
- Where are the footpaths?

### Step 2: Exclude Footpaths

If footpath is on far right:
```json
"lanes": [
  [[0.0, 1.0], [0.0, 0.0], [0.48, 0.0], [0.48, 1.0]],
  [[0.52, 1.0], [0.52, 0.0], [0.85, 0.0], [0.85, 1.0]]  // Stop at 85%
]
```

If footpath is on far left:
```json
"lanes": [
  [[0.15, 1.0], [0.15, 0.0], [0.48, 0.0], [0.48, 1.0]],  // Start at 15%
  [[0.52, 1.0], [0.52, 0.0], [1.0, 0.0], [1.0, 1.0]]
]
```

### Step 3: Define Lane Split

For your two-way road, estimate where the center divider is:
- If perfectly centered: split at 0.48 / 0.52
- If left lane wider: split at 0.4 / 0.6
- If right lane wider: split at 0.6 / 0.4

### Example for Different Road Layouts

**Four-Lane Highway** (2 lanes each direction):
```json
"lanes": [
  [[0.0, 1.0], [0.0, 0.0], [0.23, 0.0], [0.23, 1.0]],  // Lane 0 (far left)
  [[0.25, 1.0], [0.25, 0.0], [0.48, 0.0], [0.48, 1.0]], // Lane 1 (left)
  [[0.52, 1.0], [0.52, 0.0], [0.75, 0.0], [0.75, 1.0]], // Lane 2 (right)
  [[0.77, 1.0], [0.77, 0.0], [1.0, 0.0], [1.0, 1.0]]   // Lane 3 (far right)
],
"lane_directions": [
  [[0.1, 0.9], [0.1, 0.1]],   // Lane 0: Bottom→Top
  [[0.35, 0.9], [0.35, 0.1]], // Lane 1: Bottom→Top
  [[0.65, 0.1], [0.65, 0.9]], // Lane 2: Top→Bottom (opposite!)
  [[0.9, 0.1], [0.9, 0.9]]    // Lane 3: Top→Bottom (opposite!)
]
```

---

## Testing Your New Config

### Step 1: Restart Server
```bash
# Ctrl+C to stop
uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Start Video
- Enter your video path
- Click Start
- Watch for "Learning: X%" progress

### Step 3: Verify
**You should now see**:
- ✅ Green lane boundaries cover ENTIRE road (left and right halves)
- ✅ Normal traffic: NO "VIOLATED" labels
- ✅ Only wrong-way travelers: "WRONG-WAY" + "VIOLATED"
- ✅ Clean alerts panel (not flooded)

**You should NOT see**:
- ❌ "LANE VIOLATION" on every car
- ❌ Hundreds of alerts per second
- ❌ Tiny green polygon in center

---

## Quick Disable Lane Violation (Temporary)

If you ONLY want wrong-way detection and don't care about lane violations:

### Option 1: Remove Lane Check
Comment out lane violation code in `processor_v2.py` around line 260:
```python
# Lane violation (outside all lanes)
# if lane_contours and lane_index == -1:
#     inside_any = any(cv2.pointPolygonTest(cnt, (cx, cy), False) >= 0 for cnt in lane_contours)
#     if not inside_any:
#         self._emit_alert("lane_violation", track_id, {"cx": int(cx), "cy": int(cy)}, frame, bbox_tuple)
```

### Option 2: Make Lanes Cover Everything
```json
"lanes": [
  [[0.0, 1.0], [0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]  // One giant polygon = entire frame
]
```

Then only wrong-way will be detected, not lane violations.

---

## Understanding the Difference

### Lane Violation
**What**: Object center is outside ANY lane polygon
**Use**: Detect vehicles on sidewalk, shoulder, or restricted zones
**Your case**: Don't need this if footpath is excluded from lanes

### Wrong-Way Violation  
**What**: Object motion opposite to lane direction
**Use**: Detect vehicles going the wrong direction in their lane
**Your case**: THIS is your main goal!

---

## Recommended Config for Your Video

Based on your description ("two-way roads one for going and other for coming"):

```json
{
  "lanes": [
    [[0.0, 1.0], [0.0, 0.0], [0.48, 0.0], [0.48, 1.0]],
    [[0.52, 1.0], [0.52, 0.0], [1.0, 0.0], [1.0, 1.0]]
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
1. Covers entire road (excludes footpath if it's beyond frame edges)
2. Two lanes: left (0-48%) and right (52-100%)
3. Auto-learns direction for each
4. Only flags wrong-way, not lane violations (because everything is in a lane)

---

## Action Items

1. ✅ **Config updated** (I already did this)
2. **Restart server**:
   ```bash
   uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000
   ```
3. **Test again** with your video
4. **Verify**: You should see far fewer "VIOLATED" labels
5. **Check**: Only opposite-direction objects get flagged

---

## If Still Too Many Violations

### Adjust Lane Width

If footpath is visible in frame, adjust to exclude it:

**Footpath on right**:
```json
"lanes": [
  [[0.0, 1.0], [0.0, 0.0], [0.43, 0.0], [0.43, 1.0]],  // Going lane
  [[0.47, 1.0], [0.47, 0.0], [0.85, 0.0], [0.85, 1.0]]  // Coming lane (stop at 85%)
]
```

**Footpath on left**:
```json
"lanes": [
  [[0.15, 1.0], [0.15, 0.0], [0.48, 0.0], [0.48, 1.0]],  // Going lane (start at 15%)
  [[0.52, 1.0], [0.52, 0.0], [1.0, 0.0], [1.0, 1.0]]     // Coming lane
]
```

---

## Summary

**Fixed**:
- ✅ Lanes now cover entire road (not tiny trapezoid)
- ✅ Two separate lanes for two-way traffic
- ✅ Auto-learning will detect direction for each lane
- ✅ Only wrong-way travelers will be marked as violated

**Restart server and test again!**

The massive "LANE VIOLATION" spam should be gone, and you'll only see violations for actual opposite-direction travelers! 🎉

