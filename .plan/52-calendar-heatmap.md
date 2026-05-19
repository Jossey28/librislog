# Calendar Heatmap: Pages Read Per Day

## Overview

Add a calendar heatmap visualization to the statistics page showing pages read per day over the last 365 days. This feature will use LayerChart's `Calendar` component (already installed as `layerchart@2.0.0-next.64`) and introduce a new backend endpoint to aggregate daily page counts from reading progress entries and book completion data.

**Key Components:**
- New backend endpoint: `GET /api/statistics/pages-per-day`
- New frontend calendar component using LayerChart
- Data aggregation logic combining reading logs and book-level fallbacks
- DaisyUI-themed heatmap with appropriate color scaling

---

## 1. Backend Implementation

### 1.1 Create New Endpoint: `GET /api/statistics/pages-per-day`

**Location:** `backend/app/routers/statistics.py`

**Response Schema:**

Add to `backend/app/schemas.py`:

```python
class DailyPages(BaseModel):
    date: str  # ISO date format (YYYY-MM-DD)
    pages: int

class DailyPagesResponse(BaseModel):
    data: list[DailyPages]
    total_days: int
    days_with_activity: int
    total_pages: int
```

**Endpoint Signature:**

```python
@router.get("/pages-per-day", response_model=DailyPagesResponse)
def get_pages_per_day(
    days: int = Query(default=365, ge=1, le=730),
    current_user: User = Depends(require_user),
    session: Session = Depends(get_session),
) -> DailyPagesResponse:
    """
    Aggregate pages read per day over the last N days.
    
    Query Parameters:
    - days: Number of days to look back (default: 365, max: 730)
    """
```

### 1.2 Data Aggregation Logic

The endpoint must compute daily page totals using two data sources:

#### **Approach 1: Reading Progress Entries**

For books with `ReadingProgress` entries:

1. Query all reading progress entries for the user within the date range
2. Sort entries by `book_id` and `created_at`
3. For each consecutive pair of entries on the same book:
   - Calculate pages read: `current.page - previous.page`
   - If positive, attribute the difference to the date of `current.created_at`
   - If negative (reset/correction), skip
4. Group by date (UTC or user timezone) and sum

**Edge Cases:**
- First entry for a book: If `date_started` exists, compute daily rate from start to first log
- Multiple logs per day: Sum all page differences within the day
- Page corrections (going backwards): Ignore negative deltas

#### **Approach 2: Book-Level Fallback**

For books marked as `read` with:
- `date_started` and `date_finished` both set
- `page_count` set
- **No** reading progress entries

Compute daily average and distribute:

```python
total_days = (date_finished - date_started).days + 1
if total_days > 0 and page_count > 0:
    daily_avg = page_count / total_days
    # Distribute daily_avg across each day from date_started to date_finished
```

**Important:** Only apply this fallback if the book has **no** `ReadingProgress` entries. If progress logs exist, use Approach 1 exclusively for that book.

#### **Unaddressable Books**

Books without reading logs AND without complete date/page data cannot be included. Log a debug message but do not error.

### 1.3 Implementation Steps

1. **Helper Function: `_extract_progress_daily_pages()`**
   - Input: List of `ReadingProgress` entries for a user
   - Output: `Counter[str]` (date → pages)
   - Logic: Iterate through entries grouped by `book_id`, compute deltas

2. **Helper Function: `_extract_book_level_daily_pages()`**
   - Input: List of `Book` objects (filtered for read status, no progress entries)
   - Output: `Counter[str]` (date → pages)
   - Logic: Distribute page counts across date ranges

3. **Main Endpoint Logic:**
   ```python
   tz = _user_timezone(session, current_user.id)
   end_date = datetime.now(tz)
   start_date = end_date - timedelta(days=days)
   
   # Fetch all reading progress entries in range
   progress_entries = session.exec(
       select(ReadingProgress)
       .where(
           ReadingProgress.user_id == current_user.id,
           ReadingProgress.created_at >= start_date,
           ReadingProgress.created_at <= end_date
       )
       .order_by(ReadingProgress.book_id, ReadingProgress.created_at)
   ).all()
   
   # Fetch all books for the user
   books = session.exec(
       select(Book).where(Book.user_id == current_user.id)
   ).all()
   
   # Identify books with progress entries
   books_with_progress = set(e.book_id for e in progress_entries)
   
   # Approach 1: Progress-based aggregation
   progress_daily = _extract_progress_daily_pages(progress_entries, tz)
   
   # Approach 2: Book-level fallback for books without progress
   fallback_books = [
       b for b in books 
       if b.id not in books_with_progress
       and b.reading_status == ReadingStatus.read
       and b.date_started and b.date_finished and b.page_count
   ]
   fallback_daily = _extract_book_level_daily_pages(fallback_books, tz)
   
   # Merge counters
   combined = progress_daily + fallback_daily
   
   # Build response
   data = [
       DailyPages(date=date_str, pages=int(pages))
       for date_str, pages in sorted(combined.items())
       if start_date.date() <= datetime.fromisoformat(date_str).date() <= end_date.date()
   ]
   
   return DailyPagesResponse(
       data=data,
       total_days=days,
       days_with_activity=len(data),
       total_pages=sum(d.pages for d in data)
   )
   ```

### 1.4 Error Handling

- **Invalid `days` parameter:** FastAPI query validation handles this
- **Empty data:** Return empty list with `days_with_activity=0`
- **Timezone errors:** Fall back to UTC (existing pattern in `_user_timezone()`)

### 1.5 Testing Considerations

**Unit Test Scenarios:**
- User with only progress entries
- User with only book-level data (no progress logs)
- User with mixed data (some books have logs, others don't)
- Edge case: Book with progress entries but negative deltas
- Edge case: Book with `date_finished` before `date_started` (should skip)
- Empty database (no books or progress)

---

## 2. Frontend Implementation

### 2.1 Update TypeScript Types

**Location:** `frontend/src/lib/types.ts`

Add new interfaces:

```typescript
export interface DailyPages {
	date: string;
	pages: number;
}

export interface DailyPagesResponse {
	data: DailyPages[];
	total_days: number;
	days_with_activity: number;
	total_pages: number;
}
```

### 2.2 Update API Client

**Location:** `frontend/src/lib/api.ts`

Add new method to `api.statistics`:

```typescript
statistics: {
	get(): Promise<StatisticsResponse> {
		return request<StatisticsResponse>('/statistics');
	},
	
	getPagesPerDay(days: number = 365): Promise<DailyPagesResponse> {
		const qs = new URLSearchParams({ days: String(days) });
		return request<DailyPagesResponse>(`/statistics/pages-per-day?${qs}`);
	}
}
```

### 2.3 Create Calendar Heatmap Component

**Location:** `frontend/src/lib/components/CalendarHeatmap.svelte`

**Props:**
- `data: DailyPages[]` — Array of `{ date, pages }` objects
- `emptyText?: string` — Text to display when no data (default: "No reading data available")

**Implementation Approach:**

```svelte
<script lang="ts">
	import { Calendar } from 'layerchart';
	import type { DailyPages } from '$lib/types';

	let {
		data = [],
		emptyText = 'No reading data available for the past year'
	}: {
		data: DailyPages[];
		emptyText?: string;
	} = $props();

	// Compute date range (last 365 days)
	const today = $derived(new Date());
	const startDate = $derived(new Date(today.getFullYear() - 1, today.getMonth(), today.getDate()));

	// Convert data array to Map for O(1) lookup
	const dataMap = $derived(
		new Map(data.map(d => [d.date, d.pages]))
	);

	// Determine color scale based on max value
	const maxPages = $derived(Math.max(...data.map(d => d.pages), 0));

	function getCellColor(pages: number): string {
		if (pages === 0) return 'oklch(var(--b2))'; // Base-200 for empty days
		
		const intensity = Math.min(pages / maxPages, 1);
		
		// DaisyUI primary color with opacity
		if (intensity < 0.25) return 'oklch(var(--p) / 0.3)';
		if (intensity < 0.5) return 'oklch(var(--p) / 0.5)';
		if (intensity < 0.75) return 'oklch(var(--p) / 0.7)';
		return 'oklch(var(--p))'; // Full primary
	}

	function getCellLabel(date: Date): string {
		const dateStr = date.toISOString().split('T')[0];
		const pages = dataMap.get(dateStr) ?? 0;
		return pages > 0 ? `${dateStr}: ${pages} pages` : dateStr;
	}
</script>

{#if data.length === 0}
	<div class="flex items-center justify-center h-40 text-base-content/50">
		<p>{emptyText}</p>
	</div>
{:else}
	<div role="img" aria-label="Pages read per day calendar">
		<Calendar
			start={startDate}
			end={today}
			cellSize={12}
		>
			{#snippet children({ cells, cellSize })}
				{#each cells as cell}
					<rect
						x={cell.x}
						y={cell.y}
						width={cellSize[0]}
						height={cellSize[1]}
						fill={getCellColor(dataMap.get(cell.date.toISOString().split('T')[0]) ?? 0)}
						class="transition-opacity hover:opacity-80"
						aria-label={getCellLabel(cell.date)}
					>
						<title>{getCellLabel(cell.date)}</title>
					</rect>
				{/each}
			{/snippet}
		</Calendar>
	</div>
	
	<!-- Legend -->
	<div class="flex items-center gap-2 mt-3 text-sm text-base-content/70">
		<span>Less</span>
		<div class="flex gap-1">
			<div class="w-3 h-3 rounded-sm" style="background: oklch(var(--b2))"></div>
			<div class="w-3 h-3 rounded-sm" style="background: oklch(var(--p) / 0.3)"></div>
			<div class="w-3 h-3 rounded-sm" style="background: oklch(var(--p) / 0.5)"></div>
			<div class="w-3 h-3 rounded-sm" style="background: oklch(var(--p) / 0.7)"></div>
			<div class="w-3 h-3 rounded-sm" style="background: oklch(var(--p))"></div>
		</div>
		<span>More</span>
	</div>
{/if}
```

**Key Design Decisions:**
- Use `oklch(var(--p))` (DaisyUI primary color) with varying opacity for intensity
- Cell size: 12px (balance between visibility and fitting 365 days on screen)
- Month labels: LayerChart handles this automatically
- Hover effect: CSS transition on opacity + SVG `<title>` for tooltip
- Legend: Show color scale from "Less" to "More"

### 2.4 Integrate into Statistics Page

**Location:** `frontend/src/routes/statistics/+page.svelte`

**Changes:**

1. **Import the component:**
   ```svelte
   import CalendarHeatmap from '$lib/components/CalendarHeatmap.svelte';
   ```

2. **Add state for calendar data:**
   ```svelte
   let calendarData = $state<DailyPagesResponse | null>(null);
   let calendarLoading = $state(false);
   ```

3. **Load calendar data in `onMount()`:**
   ```svelte
   async function loadCalendarData(isActive: () => boolean) {
       calendarLoading = true;
       try {
           const data = await api.statistics.getPagesPerDay(365);
           if (isActive()) {
               calendarData = data;
           }
       } catch (e: unknown) {
           if (isActive()) {
               // Silently fail or show non-blocking error
               console.error('Failed to load calendar data:', e);
               calendarData = null;
           }
       } finally {
           if (isActive()) {
               calendarLoading = false;
           }
       }
   }
   
   onMount(() => {
       let active = true;
       void loadStatistics(() => active);
       void loadCalendarData(() => active); // Load in parallel
       return () => {
           active = false;
       };
   });
   ```

4. **Add calendar section to the markup** (after the book-by-year chart, before favorite author):

   ```svelte
   <div class="card bg-base-100 border border-base-200 shadow-sm">
       <div class="card-body">
           <h2 class="card-title text-base">{$_('statistics.pagesReadCalendar')}</h2>
           
           {#if calendarLoading}
               <div class="flex items-center justify-center h-40">
                   <span class="loading loading-spinner loading-md"></span>
               </div>
           {:else if calendarData}
               <CalendarHeatmap data={calendarData.data} />
               
               <!-- Summary stats -->
               <div class="flex flex-wrap gap-4 text-sm text-base-content/70 mt-2">
                   <span>
                       <strong>{formatNumber(calendarData.total_pages, 0)}</strong> pages over 
                       <strong>{calendarData.days_with_activity}</strong> days
                   </span>
                   <span>
                       Avg: <strong>{formatNumber(calendarData.total_pages / Math.max(calendarData.days_with_activity, 1), 1)}</strong> pages/day
                   </span>
               </div>
           {:else}
               <div class="text-center py-8 text-base-content/50">
                   <p>{$_('statistics.noCalendarData')}</p>
               </div>
           {/if}
       </div>
   </div>
   ```

### 2.5 Internationalization Keys

**Location:** `frontend/src/lib/i18n/locales/en.json`

Add new keys:

```json
{
	"statistics": {
		"pagesReadCalendar": "Reading Activity (Last 365 Days)",
		"noCalendarData": "No reading data available for the past year"
	}
}
```

Repeat for other locale files (`de.json`, etc.).

---

## 3. Edge Cases & Error Handling

### 3.1 Backend Edge Cases

| Scenario | Handling |
|----------|----------|
| No books in database | Return empty array, `days_with_activity=0` |
| No progress entries, no book dates | Return empty array |
| Invalid timezone | Fall back to UTC |
| Progress entry with page=0 | Include in delta calculation (valid start point) |
| Negative page delta | Skip (treat as data correction) |
| Book with `date_finished` before `date_started` | Skip (invalid data) |
| Book read in single day | Attribute all pages to `date_finished` |
| `days` parameter exceeds 730 | FastAPI validation returns 422 error |

### 3.2 Frontend Edge Cases

| Scenario | Handling |
|----------|----------|
| API returns empty data | Show "No reading data available" message |
| API call fails | Log error to console, show fallback message, don't block page load |
| maxPages = 0 | All cells render as base-200 color |
| User has reading activity today | Include in heatmap (end date = today) |
| Timezone mismatch | Rely on backend's user timezone setting |

---

## 4. UI/UX Considerations

### 4.1 Mobile Responsiveness

- Calendar cells may be too small on mobile (<400px width)
- Solution: Use responsive `cellSize` based on viewport width
- Alternative: Show last 90 days on mobile, 365 on desktop

```svelte
const isMobile = $derived(typeof window !== 'undefined' && window.innerWidth < 640);
const daysToShow = $derived(isMobile ? 90 : 365);
```

### 4.2 Color Accessibility

- Ensure sufficient contrast between empty cells (base-200) and filled cells (primary)
- Consider adding a text summary for screen readers:
  ```svelte
  <div class="sr-only">
      Reading activity calendar showing {calendarData.days_with_activity} days with activity
      out of {calendarData.total_days} days
  </div>
  ```

### 4.3 Loading State

- Show spinner during initial load
- Don't block main statistics page if calendar data fails to load

---

## 5. Implementation Checklist

### Backend
- [ ] Add `DailyPages` and `DailyPagesResponse` schemas to `schemas.py`
- [ ] Implement `_extract_progress_daily_pages()` helper in `statistics.py`
- [ ] Implement `_extract_book_level_daily_pages()` helper in `statistics.py`
- [ ] Create `GET /pages-per-day` endpoint with proper query parameter validation
- [ ] Test endpoint with empty database
- [ ] Test endpoint with progress-only data
- [ ] Test endpoint with book-level-only data
- [ ] Test endpoint with mixed data
- [ ] Test negative page deltas handling
- [ ] Test timezone awareness

### Frontend
- [ ] Add `DailyPages` and `DailyPagesResponse` types to `types.ts`
- [ ] Add `getPagesPerDay()` method to `api.ts`
- [ ] Create `CalendarHeatmap.svelte` component with LayerChart integration
- [ ] Add color scale legend to component
- [ ] Test empty data state rendering
- [ ] Test hover tooltips on calendar cells
- [ ] Integrate component into `statistics/+page.svelte`
- [ ] Add loading state for calendar data
- [ ] Add summary stats display (total pages, average pages/day)
- [ ] Add i18n keys for new UI text
- [ ] Test mobile responsiveness (consider showing fewer days on small screens)
- [ ] Test with DaisyUI theme switcher (ensure colors work across themes)

### Documentation
- [ ] Update API documentation (if auto-generated from FastAPI)
- [ ] Add comments explaining delta calculation logic
- [ ] Document fallback behavior for books without progress logs

---

## 6. Future Enhancements

**Not in scope for this plan, but potential follow-ups:**

1. **Interactive Date Range Selector**
   - Allow users to select 30/90/180/365 day views
   - Add dropdown in calendar card header

2. **Click-to-Drill-Down**
   - Click a calendar cell → show list of books read that day
   - Modal or expandable detail section

3. **Streak Tracking**
   - Calculate and display longest reading streak
   - Highlight current streak in the calendar

4. **Weekly/Monthly Aggregation View**
   - Toggle between daily cells and weekly bars
   - Useful for users with sparse data

5. **Export Calendar Data**
   - Download as CSV or PNG image
   - Share reading activity on social media

6. **Comparison View**
   - Compare current year vs. previous year
   - Side-by-side calendars

---

## 7. Testing Strategy

### 7.1 Manual Testing Checklist

**Backend:**
1. Create test user with varied data:
   - 3 books with reading progress entries spanning 6 months
   - 2 books marked "read" with date_started/date_finished but no progress logs
   - 1 book with only date_finished (should be ignored)
2. Call `/api/statistics/pages-per-day?days=365`
3. Verify response contains correct daily totals
4. Verify days without activity are not included in response
5. Test with `days=30`, `days=730` (edge of validation)
6. Test with `days=1000` (expect 422 validation error)

**Frontend:**
1. Navigate to Statistics page
2. Verify calendar renders with correct date range
3. Hover over cells with data → verify tooltip shows date + page count
4. Hover over empty cells → verify tooltip shows date only
5. Test on mobile viewport (<640px) → verify calendar fits screen
6. Switch DaisyUI theme → verify colors update correctly
7. Test with empty data (new user) → verify fallback message displays
8. Test browser back/forward → verify calendar state persists

### 7.2 Automated Testing

**Backend Unit Tests (example with pytest):**

```python
def test_pages_per_day_with_progress_entries(client, test_user, test_books, test_progress):
    """Test calendar endpoint with reading progress data."""
    response = client.get(
        "/api/statistics/pages-per-day?days=30",
        headers={"Authorization": f"Bearer {test_user.token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "total_days" in data
    assert data["total_days"] == 30
    assert len(data["data"]) > 0

def test_pages_per_day_empty_database(client, test_user):
    """Test calendar endpoint with no books."""
    response = client.get(
        "/api/statistics/pages-per-day?days=365",
        headers={"Authorization": f"Bearer {test_user.token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert data["days_with_activity"] == 0
```

**Frontend Component Tests (example with Vitest):**

```typescript
import { render, screen } from '@testing-library/svelte';
import { describe, it, expect } from 'vitest';
import CalendarHeatmap from '$lib/components/CalendarHeatmap.svelte';

describe('CalendarHeatmap', () => {
	it('renders empty state when no data provided', () => {
		render(CalendarHeatmap, { data: [] });
		expect(screen.getByText(/No reading data available/i)).toBeInTheDocument();
	});

	it('renders calendar with data', () => {
		const data = [
			{ date: '2024-05-01', pages: 25 },
			{ date: '2024-05-02', pages: 30 }
		];
		render(CalendarHeatmap, { data });
		// Verify SVG rendering (LayerChart creates SVG elements)
		const svg = screen.getByRole('img', { name: /Pages read per day calendar/i });
		expect(svg).toBeInTheDocument();
	});
});
```

---

## 8. Performance Considerations

### 8.1 Backend Query Optimization

**Potential Performance Issues:**
- Fetching all `ReadingProgress` entries for a user (could be thousands)
- Fetching all `Book` records for a user

**Mitigation:**
1. Add date range filter to progress query (`created_at >= start_date`)
2. Use indexed columns (`user_id`, `created_at`, `book_id`)
3. Consider caching for 1 hour if statistics page has high traffic

**Query Optimization:**
```python
# Only fetch progress entries within the date range
progress_entries = session.exec(
    select(ReadingProgress)
    .where(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.created_at >= start_date,
        ReadingProgress.created_at <= end_date
    )
    .order_by(ReadingProgress.book_id, ReadingProgress.created_at)
).all()
```

### 8.2 Frontend Rendering

**LayerChart Performance:**
- Rendering 365 SVG `<rect>` elements is fast (<16ms on modern browsers)
- No virtualization needed for this use case
- Total component size: ~50KB (LayerChart is already imported for BarChart)

---

## 9. Rollout Plan

### Phase 1: Backend Implementation
1. Implement schemas and helper functions
2. Create endpoint with basic logic (progress entries only)
3. Manual testing with Postman/curl
4. Add book-level fallback logic
5. Write unit tests

### Phase 2: Frontend Component
1. Create `CalendarHeatmap.svelte` with mock data
2. Style with DaisyUI colors
3. Test in isolation (component playground)
4. Add legend and tooltips

### Phase 3: Integration
1. Wire up API client method
2. Integrate into statistics page
3. Add loading states and error handling
4. Manual testing in dev environment
5. Add i18n strings

### Phase 4: Testing & Refinement
1. Cross-browser testing (Chrome, Firefox, Safari)
2. Mobile responsiveness testing
3. Accessibility testing (screen reader, keyboard navigation)
4. Performance profiling (large datasets)

### Phase 5: Deployment
1. Code review
2. Merge to main branch
3. Deploy to staging
4. Smoke test on staging
5. Deploy to production
6. Monitor error logs for 48 hours

---

## 10. Dependencies

### Existing Dependencies (Already Installed)
- ✅ `layerchart@2.0.0-next.64` (frontend)
- ✅ `dayjs@1.11.20` (frontend, for date handling if needed)
- ✅ `daisyui@5.5.19` (frontend, for theming)
- ✅ `sqlmodel` (backend, for ORM)
- ✅ `fastapi` (backend, for API)

### No New Dependencies Required
This feature uses only existing libraries.

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| LayerChart Calendar API changes in future versions | Low | Medium | Pin version `2.0.0-next.64`, test before upgrading |
| Performance issues with large datasets (10k+ progress entries) | Low | Medium | Add date range filter, consider pagination |
| Timezone bugs causing date mismatches | Medium | Medium | Thoroughly test with non-UTC timezones, use existing `_user_timezone()` helper |
| Empty state not user-friendly | Low | Low | Add helpful empty message + link to add books |
| Mobile rendering issues | Medium | Low | Test early, adjust cell size responsively |
| Backend logic errors with delta calculation | Medium | High | Write comprehensive unit tests, validate with real data |

---

## Summary

This plan provides a complete, production-ready implementation of a calendar heatmap showing pages read per day. The feature leverages existing infrastructure (LayerChart, DaisyUI, FastAPI patterns) and follows established project conventions (Svelte 5 runes, timezone-aware date handling, i18n). The two-approach data aggregation strategy ensures maximum data coverage while avoiding double-counting.

**Estimated Effort:**
- Backend: 4-6 hours (including tests)
- Frontend: 3-4 hours (including component + integration)
- Testing & Refinement: 2-3 hours
- **Total: 9-13 hours**

**Key Success Metrics:**
- Calendar renders correctly with 365 days of data
- Hover tooltips show accurate page counts
- Empty state is clear and informative
- No performance degradation on statistics page load
- Works across all supported browsers and devices
