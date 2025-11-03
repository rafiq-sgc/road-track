# Violator Panel - Complete Guide

## How It Works

### Queue System (FIFO - First In, First Out)

```
Timeline:

10:00:00 - Violation A detected → Add to queue → Show in panel
10:00:02 - Violation B detected → Add to queue → Show below A
10:00:04 - Violation C detected → Add to queue → Show below B

Panel shows:
┌─────────────┐
│ Violator A  │ ← Added first
├─────────────┤
│ Violator B  │
├─────────────┤
│ Violator C  │ ← Added last
└─────────────┘

10:00:05 - 5 seconds passed → Remove A (oldest)
10:00:07 - 5 seconds passed → Remove B
10:00:09 - 5 seconds passed → Remove C

Panel now: "Waiting for violations..."
```

---

## Visual Layout

### Single Violation
```
╔═══════════════════════════════╗
║ 🚨 VIOLATORS (1)              ║
╠═══════════════════════════════╣
║ ┌───────────────────────────┐ ║
║ │                           │ ║
║ │   [Large Crop Image]      │ ║
║ │                           │ ║
║ └───────────────────────────┘ ║
║                               ║
║ 🔄 WRONG-WAY                  ║
║ 🚗 Car • #42 • 🔢 DHK-1234   ║
║                               ║
╚═══════════════════════════════╝
```

### Multiple Violations (Stacked)
```
╔═══════════════════════════════╗
║ 🚨 VIOLATORS (3)              ║
╠═══════════════════════════════╣
║ ┌───────────────────────────┐ ║
║ │ [Violator A]              │ ║ ← Oldest (5s left)
║ │ 🔄 WRONG-WAY              │ ║
║ │ 🚗 Car • #42 • 🔢 ABC123  │ ║
║ └───────────────────────────┘ ║
║                               ║
║ ┌───────────────────────────┐ ║
║ │ [Violator B]              │ ║ ← (4s left)
║ │ 🚦 RED LIGHT              │ ║
║ │ 🚌 Bus • #15              │ ║
║ └───────────────────────────┘ ║
║                               ║
║ ┌───────────────────────────┐ ║
║ │ [Violator C]              │ ║ ← Newest (3s left)
║ │ ⚡ SPEEDING               │ ║
║ │ 🏍️ Motorcycle • #8        │ ║
║ └───────────────────────────┘ ║
║                               ║
║ [Scroll if more...]           ║
╚═══════════════════════════════╝
```

---

## Features

### 1. Auto-Queue Management
- New violations automatically added to bottom
- Each shows for exactly 5 seconds
- Oldest removed first (FIFO)
- Smooth slide-in animation when added
- Smooth fade-out when removed

### 2. Information Display

Each violator card shows:
- ✅ **Large crop image** (with red border)
- ✅ **Violation type** ("🔄 WRONG-WAY", "🚦 RED LIGHT", etc.)
- ✅ **Vehicle type** ("🚗 Car", "🏍️ Motorcycle", "🚌 Bus", etc.)
- ✅ **Track number** ("#42")
- ✅ **License plate** ("🔢 DHK-1234") if readable
- ✅ **Additional info** (lane, speed if applicable)

### 3. Counter
Header shows total active violators: "🚨 VIOLATORS (3)"

### 4. Scrolling
If more than ~3 violators, panel scrolls automatically

---

## Behavior Examples

### Scenario 1: Single Violation

```
Time: 10:00:00 - Wrong-way car detected
Action: Shows in panel with image + details
Time: 10:00:05 - Auto-removes (5s passed)
Panel: "Waiting for violations..."
```

### Scenario 2: Multiple Violations (Burst)

```
10:00:00 - Violator A added → Panel shows [A]
10:00:01 - Violator B added → Panel shows [A, B]
10:00:02 - Violator C added → Panel shows [A, B, C]
10:00:03 - Violator D added → Panel shows [A, B, C, D]
10:00:05 - A removed (5s) → Panel shows [B, C, D]
10:00:06 - B removed (5s) → Panel shows [C, D]
10:00:07 - C removed (5s) → Panel shows [D]
10:00:08 - D removed (5s) → Panel shows "Waiting..."
```

### Scenario 3: Continuous Stream

```
Violations keep coming:
10:00:00 - A added
10:00:02 - B added
10:00:04 - C added
10:00:05 - A removed, D added → [B, C, D]
10:00:06 - E added → [B, C, D, E]
10:00:07 - B removed, F added → [C, D, E, F]
...continues...

Panel always shows last 5 seconds of violations
```

---

## Customization

### Change Display Duration

In `showViolator()` function (line 300):
```javascript
// Current: 5 seconds
setTimeout(()=>{ removeViolator(alert.evidence_id); }, 5000);

// Increase to 10 seconds:
setTimeout(()=>{ removeViolator(alert.evidence_id); }, 10000);

// Decrease to 3 seconds:
setTimeout(()=>{ removeViolator(alert.evidence_id); }, 3000);
```

### Change Grid Columns

For side-by-side display:
```html
<div id="violatorGrid" style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
```

Result:
```
╔═══════════════════════════════╗
║ ┌──────────┐ ┌──────────┐    ║
║ │Violator A│ │Violator B│    ║
║ └──────────┘ └──────────┘    ║
║ ┌──────────┐ ┌──────────┐    ║
║ │Violator C│ │Violator D│    ║
║ └──────────┘ └──────────┘    ║
╚═══════════════════════════════╝
```

### Max Violators Displayed

Add limit to `showViolator()`:
```javascript
function showViolator(alert){
  if(!alert.evidence_id) return;
  
  // Limit to 5 max
  if(violatorQueue.length >= 5){
    const oldest = violatorQueue[0];
    removeViolator(oldest.evidence_id);
  }
  
  // ... rest of code
}
```

---

## What You See

### Display Format

Each card:
```
┌─────────────────────────────┐
│ ╔═════════════════════════╗ │
│ ║                         ║ │
│ ║   [Violator Image]      ║ │ ← Large crop
│ ║   Red border            ║ │
│ ╚═════════════════════════╝ │
│                             │
│ 🔄 WRONG-WAY                │ ← Violation type (bold, red)
│                             │
│ 🚗 Car • #42 • 🔢 DHK-1234 │ ← Details (white text)
│                             │
└─────────────────────────────┘
   ↑ Dark background, red border
```

---

## Benefits for Public Display

### Clear Identification
- Vehicle type visible ("Car", "Bus", "Motorcycle")
- License plate readable (if detected)
- Track number for correlation
- Violation type obvious

### Professional Presentation
- Clean grid layout
- Smooth animations (slide in/out)
- Auto-clearing (no manual intervention)
- Scrollable if many violations

### Public Impact
- People see their vehicle displayed
- Clear "WRONG-WAY" or other violation label
- Embarrassment factor for behavior change
- Evidence of enforcement

---

## Testing

### Step 1: Restart Server
```bash
uvicorn app.main_v2:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Open UI
http://localhost:8000

**Check**:
- ✅ Three columns visible
- ✅ Center panel has red border and "🚨 VIOLATORS (0)"
- ✅ Shows "Waiting for violations..."

### Step 3: Trigger Violations
- Start video
- Wait for auto-learning complete
- Violations appear automatically

**Verify**:
- ✅ Violator card appears with slide-in animation
- ✅ Shows large image with red border
- ✅ Shows violation type in red
- ✅ Shows vehicle type (Car, Bus, etc.)
- ✅ Shows plate if readable
- ✅ Counter increases: "VIOLATORS (1)", "(2)", etc.
- ✅ After 5 seconds, card fades out
- ✅ Counter decreases
- ✅ Next violation appears at bottom

---

## Expected Behavior

### Normal Operation

```
Violation flow:
1. Detection → 2. Evidence saved → 3. Alert → 4. Panel updated

Panel lifecycle:
Add → Display 5s → Animate out → Remove

Queue management:
FIFO (oldest removed first)
Smooth animations
Auto-scrolling if many
```

### Multiple Simultaneous Violations

```
If 3 violations occur within 1 second:
- All 3 appear in panel (stacked)
- Each has its own 5s timer
- They remove independently
- Panel updates smoothly
```

---

## Troubleshooting

### Issue: Panel shows "Waiting..." but violations occurring

**Check**:
1. Are alerts appearing in right panel? (If yes, evidence might not be saving)
2. Check browser console for JavaScript errors
3. Check violations/ folder has new crops
4. Refresh browser (Ctrl+F5)

**Solution**:
```bash
# Ensure violations folder exists and is writable
mkdir -p violations/crops violations/fullframes violations/metadata
chmod 755 violations/
```

### Issue: Images not loading

**Check**:
1. violations/crops/ folder has .jpg files?
2. Browser console shows 404 errors?
3. Check static file mounting in main_v2.py

**Solution**: Files should be accessible at `/violations/crops/{filename}.jpg`

### Issue: No plate numbers showing

**Expected**: Plate reading has ~20-40% accuracy without custom model

**To improve**:
1. Download YOLO plate detection model
2. Set `plate_model_path` in config
3. See `PLATE_DETECTION_SETUP.md`

---

## Advanced: Custom Styling

### Larger Images
```javascript
// In renderViolators, change img style:
<img src="${cropPath}" style="width:100%;height:250px;object-fit:cover;..." />
```

### Highlight Most Severe (Wrong-Way)
```javascript
const borderColor = alert.type === 'wrong_way' ? 'var(--danger)' : '#666';
border:2px solid ${borderColor};
```

### Add Progress Bar (Time Remaining)
```javascript
// Add to card:
<div style="height:3px;background:var(--danger);width:100%;margin-top:4px;animation:shrink 5s linear"></div>

// Add to CSS:
@keyframes shrink{from{width:100%}to{width:0%}}
```

---

## Summary

**What You Have**:
- ✅ Dedicated violator panel (center column)
- ✅ Queue system (FIFO, 5s duration)
- ✅ Multiple violations displayed simultaneously
- ✅ Smooth animations (slide in/out)
- ✅ Vehicle type + plate number displayed
- ✅ Auto-clearing (no manual intervention)
- ✅ Counter shows active violators
- ✅ Scrollable for many violations
- ✅ Perfect for public display!

**Restart server and test!** The panel will now show all violations for 5 seconds each, removing the oldest first! 🎉

