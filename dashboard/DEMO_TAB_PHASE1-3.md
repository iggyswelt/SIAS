# Demo Tab - Phase 1 & 3 Documentation

## Phase 1: Bug Fixes (Completed ✅)

### 1. AGENT TAB "INVALID AGENT" Error ✅
**Problem:** Pythia was missing from the agent list (only 7 agents instead of 8)

**Solution:** Added Pythia to the `agents` table in PostgreSQL
```bash
psql -h 127.0.0.1 -U scraper -d metamaus -c "INSERT INTO agents (name, emoji, status, description) VALUES ('pythia', '👁️', 'active', 'Vision & Bildanalyse') ON CONFLICT (name) DO NOTHING;"
```

**Verification:**
```bash
curl http://192.168.23.170:5000/api/agents | jq '.agents[] | .name'
```
Output: All 8 agents now listed (athena, hermes, hestia, metamaus, orpheus, pythia, rheingold, zerberus)

---

### 2. SORTIERUNG REPARIEREN ✅
**Problems:**
- ORDER BY not working properly
- Category filter broken
- Location filter broken

**Solution:** Updated `/api/demos` endpoint in `app.py` to handle query parameters properly

**Changes to `/opt/dashboard/app.py`:**
```python
@app.route('/api/demos')
def get_demos():
    """Get demo events from PostgreSQL database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get query parameters
        category = request.args.get('category', 'all')
        location = request.args.get('location', 'all')

        # Build query with filters
        where_clauses = ["date >= CURRENT_DATE - INTERVAL '7 days'"]
        params = []

        if category and category.lower() != 'all':
            where_clauses.append("LOWER(category) = %s")
            params.append(category.lower())  # Case-insensitive matching

        if location and location.lower() != 'all':
            where_clauses.append("LOWER(location) LIKE %s")
            params.append(f"%{location.lower()}%")  # Case-insensitive partial match

        where_clause = " AND ".join(where_clauses)

        # Get upcoming demos with proper sorting
        cursor.execute(f"""
            SELECT id, title, NULL as description, date as event_date, time as event_time, location,
                   NULL as address, NULL as organizer, source_url, source,
                   category, FALSE as verified, 'planned' as status, NULL as participant_count,
                   CASE WHEN is_valid = TRUE THEN 'valid' WHEN is_valid = FALSE THEN 'invalid' ELSE 'pending' END as validation_status,
                   validation_note, is_valid, user_feedback, scraped_at as updated_at
            FROM demo_events
            WHERE {where_clause}
            ORDER BY date ASC, time ASC NULLS LAST, title ASC
            LIMIT 50
        """, params)
```

**Improvements:**
- ✅ Category filter now works (case-insensitive)
- ✅ Location filter now works (case-insensitive partial match)
- ✅ Proper sorting: date ASC, time ASC, title ASC
- ✅ Increased limit from 10 to 50 for better visibility

**Testing:**
```bash
# Test category filter
curl "http://192.168.23.170:5000/api/demos?category=demo" | jq '.count'

# Test location filter (URL encoding for special characters)
curl "http://192.168.23.170:5000/api/demos?location=K%C3%B6ln" | jq '.count'
```

---

### 3. AUTO-REFRESH NACH INVALID-KLICK ✅
**Problem:** Manual refresh button needed after marking events as invalid

**Solution:** Frontend already called `refreshDemos()` after validation, but was using wrong endpoint

**Changes to `/opt/dashboard/index.html`:**
```javascript
function validateDemo(id, status) {
    let reason = null;
    if (status === "invalid") {
        const r = prompt("Warum invalid?\n1=Kein/falsches Datum\n2=Falscher Ort\n3=News keine Demos\n4=Spam/Doppelt\n6=Quelle fehlerhaft\n7=Allgemeine News");
        const reasons = ["", "Kein/falsches Datum", "Falscher Ort", "News keine Demos", "Spam/Doppelt", "", "Quelle fehlerhaft", "Allgemeine News"];
        reason = reasons[parseInt(r)] || "Unbekannt";
    }
    // Changed from /api/demos/validate to /api/demo/feedback
    fetch("/api/demo/feedback", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({id: id, feedback: status, note: reason})
    }).then(() => refreshDemos());  // Auto-refreshes the list
}
```

**Improvements:**
- ✅ Auto-refresh after marking valid/invalid
- ✅ No manual refresh button needed
- ✅ Uses correct existing endpoint `/api/demo/feedback`

**Testing:**
```bash
# Mark an event as valid
curl -X POST http://192.168.23.170:5000/api/demo/feedback \
  -H "Content-Type: application/json" \
  -d '{"id": 123, "feedback": "valid", "note": "test"}'
```

---

### 4. Duplicate Route Bug Fix ✅
**Problem:** Flask app crashed due to duplicate `/api/rheingold/activity` route

**Solution:** Removed duplicate route definition in `app.py`

**Details:**
- Removed first `timestamp()` function with route `/api/rheingold/activity`
- Kept `rheingold_activity()` function which uses the correct column name `timestamp`

---

## Phase 3: New Layout (TODO - This Week)

### 4. CALENDAR UI
```
┌─────────────────────────────────────────────┐
│ 🗓 DEMO KALENDER [Filter ▼]                │
├──────────────┬─────────────────────────────┤
│              │                             │
│ MÄRZ 2026    │ ═══ SA., 21. MÄRZ 2026 ═══ │
│ ┌─┬─┬─┬─┬─┬─┐ │                             │
│ │ │ │●│ │ │ ●│ │                             │
├─┼─┼─┼─┼─┼─┼─┤ │                             │
│ Mo│ Di│ Mi│ Do│ Fr│ Sa│ So│ │                             │
│ 1│ 2│ 3│ 4│ 5│ 6│ 7│ │                             │
│   │   │   │   │   │   │ │                             │
└──────────────┴─────────────────────────────┘
```

**Requirements:**
- Month navigation arrows (◀ ▶)
- Days with events show dots (●)
- Click on day → shows events in right panel
- Current month highlighted

**API needed:**
```python
@app.route('/api/demos/calendar', methods=['GET'])
def get_demos_calendar():
    """Get demo events for calendar view (year/month)"""
    year = request.args.get('year', datetime.now().year)
    month = request.args.get('month', datetime.now().month)

    cursor.execute("""
        SELECT date, COUNT(*) as event_count
        FROM demo_events
        WHERE EXTRACT(YEAR FROM date) = %s
        AND EXTRACT(MONTH FROM date) = %s
        GROUP BY date
        ORDER BY date
    """, (year, month))
```

**Frontend components:**
- Calendar grid generator
- Day click handler
- Month navigation
- Dot indicators for event days

---

### 5. EVENT-KARTE DESIGN
```
┌────────────────────────────────────────┐
│ 🔴 13:00 Köln stellt sich quer         │
│ 📍 Sudermannplatz → Hohenzollernring │
│ 👥 10.000+ erwartet                   │
│ 🏷 KSSQ + 60 Gruppen                  │
│                                   │
│ [Details] [Invalid ▼] [Rheingold] │
└────────────────────────────────────────┘
```

**Requirements:**
- Color coding by expected attendees:
  - 🔴 Red: > 1000 attendees
  - 🟡 Yellow: 100-1000 attendees
  - 🟢 Green: < 100 attendees
- Time, location, participant count, organizer
- Action buttons: Details, Invalid, Rheingold
- Hover effects for better UX

**API additions needed:**
```python
# Add to existing /api/demos endpoint
SELECT
    expected_attendees,
    organizer
FROM demo_events
```

**Frontend rendering:**
```javascript
function renderEventCard(event) {
    // Color coding
    const attendees = event.expected_attendees || 0;
    const color = attendees > 1000 ? 'red' : attendees > 100 ? 'yellow' : 'green';

    // Event emoji
    const emoji = color === 'red' ? '🔴' : color === 'yellow' ? '🟡' : '🟢';

    // Render card
    return `
        <div class="event-card" style="border-left: 4px solid ${color}">
            <div class="event-time">${emoji} ${event.time || 'TBD'}</div>
            <div class="event-title">${event.title}</div>
            <div class="event-location">📍 ${event.location || 'Köln'}</div>
            ${attendees > 0 ? `<div class="event-attendees">👥 ${attendees}+ erwartet</div>` : ''}
            ${event.organizer ? `<div class="event-organizer">🏷 ${event.organizer}</div>` : ''}
            <div class="event-actions">
                <button class="btn-details">Details</button>
                <button class="btn-invalid">Invalid ▼</button>
                <button class="btn-rheingold">Rheingold</button>
            </div>
        </div>
    `;
}
```

---

### 6. KATEGORIE-LEGEND
```
KATEGORIEN:
☑️ Demo
☑️ Kundgebung
☑️ Streik
☑️ Info
☑️ Sport
☑️ Kultur
☑️ Invalid
```

**Requirements:**
- Checkbox filters for each category
- Multiple selection allowed
- Real-time filtering
- "Invalid" category for invalid events

**Frontend implementation:**
```html
<div class="category-legend">
    <h3>KATEGORIEN:</h3>
    <label><input type="checkbox" checked value="demo"> ☑️ Demo</label>
    <label><input type="checkbox" checked value="kundgebung"> ☑️ Kundgebung</label>
    <label><input type="checkbox" checked value="streik"> ☑️ Streik</label>
    <label><input type="checkbox" checked value="info"> ☑️ Info</label>
    <label><input type="checkbox" checked value="sport"> ☑️ Sport</label>
    <label><input type="checkbox" checked value="kultur"> ☑️ Kultur</label>
    <label><input type="checkbox" checked value="invalid"> ☑️ Invalid</label>
</div>
```

---

### 7. FILTER UI
**Requirements:**
- Month navigation (◀ März 2026 ▶)
- Category checkboxes (see above)
- Search field for title/location
- Location dropdown (Köln, Düsseldorf, etc.)

**Frontend implementation:**
```html
<div class="filter-bar">
    <div class="month-nav">
        <button onclick="navigateMonth(-1)">◀</button>
        <span id="current-month">März 2026</span>
        <button onclick="navigateMonth(1)">▶</button>
    </div>

    <input type="text" id="search-input" placeholder="Suche...">

    <select id="location-filter">
        <option value="all">Alle Orte</option>
        <option value="Köln">Köln</option>
        <option value="Düsseldorf">Düsseldorf</option>
        <option value="Bonn">Bonn</option>
    </select>
</div>
```

---

## API Reference

### Existing Endpoints (Phase 1 - Fixed)

#### GET /api/demos
Get demo events with optional filters

**Query Parameters:**
- `category`: Filter by category (demo, info, kundgebung, etc.)
- `location`: Filter by location (partial match, case-insensitive)

**Response:**
```json
{
  "events": [
    {
      "id": 123,
      "title": "Köln stellt sich quer",
      "event_date": "2026-03-21",
      "event_time": "13:00",
      "location": "Köln",
      "category": "demo",
      "validation_status": "valid",
      "source_url": "https://...",
      "source": "telegram",
      "expected_attendees": 10000,
      "organizer": "KSSQ"
    }
  ],
  "count": 50,
  "status": "success",
  "updated": "2026-03-21T11:42:50.483248"
}
```

#### POST /api/demo/feedback
Mark event as valid/invalid

**Request Body:**
```json
{
  "id": 123,
  "feedback": "valid" | "invalid",
  "note": "Optional reason"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

#### GET /api/agents
Get all agents

**Response:**
```json
{
  "agents": [
    {
      "name": "pythia",
      "emoji": "👁️",
      "status": "active",
      "description": "Vision & Bildanalyse",
      "last_active": "2026-03-21 11:39:04.368587"
    }
  ],
  "count": 8
}
```

---

### New Endpoints Needed (Phase 3 - TODO)

#### GET /api/demos/calendar
Get events for calendar view

**Query Parameters:**
- `year`: Year (default: current year)
- `month`: Month (default: current month)

**Response:**
```json
{
  "days": [
    {
      "date": "2026-03-21",
      "event_count": 5,
      "events": [...]
    }
  ]
}
```

#### GET /api/demos/categories
Get all available categories

**Response:**
```json
{
  "categories": ["demo", "info", "kundgebung", "streik", "sport", "kultur", "invalid"]
}
```

---

## Testing Checklist

### Phase 1 Testing (✅ Completed)
- [x] All 8 agents displayed in Agent Tab
- [x] Pythia visible in agent list
- [x] Category filter works (demo, info, kundgebung, etc.)
- [x] Location filter works (Köln, Düsseldorf, etc.)
- [x] Events sorted by date ASC, time ASC, title ASC
- [x] Auto-refresh after marking valid/invalid
- [x] No manual refresh needed
- [x] No Flask errors on startup

### Phase 3 Testing (TODO)
- [ ] Calendar UI displays current month
- [ ] Month navigation works
- [ ] Days with events show dots
- [ ] Click on day shows events
- [ ] Event cards display with correct colors
- [ ] Color coding based on attendee count
- [ ] Category checkboxes filter events
- [ ] Search field filters events
- [ ] Location dropdown filters events
- [ ] Rheingold button opens Rheingold research
- [ ] Invalid button opens reason dialog

---

## Deployment

### Files Modified (Phase 1)
1. `/opt/dashboard/app.py`
   - Updated `/api/demos` endpoint with filters
   - Fixed duplicate route `/api/rheingold/activity`

2. `/opt/dashboard/index.html`
   - Fixed `validateDemo()` to use `/api/demo/feedback`

3. PostgreSQL database
   - Added Pythia to `agents` table

### Files to Create (Phase 3)
1. `/opt/dashboard/templates/calendar_tab.html`
2. CSS styles for calendar and event cards
3. JavaScript for calendar interaction

---

## URLs
- Dashboard: http://192.168.23.170:5000
- API Docs: http://192.168.23.170:5000/api/demos
- Agents: http://192.168.23.170:5000/api/agents

---

## Status
- ✅ Phase 1: COMPLETED (All critical bugs fixed)
- ⏳ Phase 3: IN PROGRESS (Layout implementation this week)

**Last Updated:** 2026-03-21
**Version:** 1.0
