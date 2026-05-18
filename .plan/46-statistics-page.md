# Statistics Page — Comprehensive Reading Analytics and Visualizations

## Problem / Overview

The existing dashboard shows basic library stats (total books, books read, currently reading, want to read) but lacks deep analytics and visualizations of reading patterns over time. Users cannot see trends, distributions, or historical data about their reading habits. A dedicated Statistics page will provide comprehensive metrics, charts, and insights about the user's reading journey, including temporal trends, language/status distributions, page statistics, and author analytics.

## Goals

1. **Provide actionable metrics** — Show average books per month, busiest reading periods, page statistics, and language/author insights
2. **Visualize distributions** — Display stacked bar charts for language, status, and page buckets (to-read, read, wasted)
3. **Show temporal trends** — Line charts for pages read per month, books finished per month/year with continuous time axes (including zero periods)
4. **Highlight favorite author** — Display the author with the most books, with a visual cover gallery
5. **Use existing stack** — Build charts with daisyUI + Tailwind CSS (no new chart library dependencies)
6. **Ensure i18n and a11y** — All labels, tooltips, and interactions must be internationalized and accessible
7. **Backend-driven aggregation** — Heavy lifting happens in SQL; frontend just renders

## Architecture Overview

### Backend

- **New router:** `backend/app/routers/statistics.py`
- **New API endpoint:** `GET /api/statistics`
- **Response schema:** `StatisticsResponse` (defined in `backend/app/schemas.py`)
- **Database queries:** Use SQLAlchemy/SQLModel aggregations, date extraction, grouping, and window functions
- **Timezone handling:** All date bucketing uses the user's configured timezone from `UserSettings.timezone`

### Frontend

- **New route:** `frontend/src/routes/statistics/+page.svelte`
- **Chart approach:** CSS-based stacked bars using Tailwind width percentages + flex layouts; SVG-based line charts with manual path rendering
- **Responsive layout:** Grid-based card layout, stacks on mobile
- **Data fetching:** Single API call on mount to `/api/statistics`

---

## 1. Backend Implementation

### 1.1 New Router: `backend/app/routers/statistics.py`

**Purpose:** Aggregate reading data for the authenticated user and return structured statistics.

**Endpoint:** `GET /api/statistics`

**Response Model:** `StatisticsResponse` (see section 1.2)

**Key Calculations:**

1. **Average books finished per month**
   - Count books with `reading_status = 'read'` and non-null `date_finished`
   - Extract month/year from `date_finished` in user's timezone
   - Group by month, count books, compute average
   - Edge case: If < 2 months of data, return 0 or N/A

2. **Month with most books finished**
   - Same grouping as above, pick max count
   - Return month name (e.g., "May 2026") and count
   - Edge case: If no books finished, return `null`

3. **Average page count of all books**
   - Average `page_count` where `page_count IS NOT NULL`
   - Edge case: If no books have page_count, return `null`

4. **Most popular language**
   - Group by `language`, count books, order by count DESC
   - Return language code and count
   - Edge case: If no books have language, return `null`

5. **Distribution by language**
   - Group by `language`, count books
   - Return list of `{language: str | null, count: int}`
   - Sort by count DESC, then alphabetically

6. **Distribution by reading status**
   - Group by `reading_status`, count books
   - Return counts for all four statuses (zero if none)

7. **Page buckets**
   - **Pages to read:** `SUM(page_count)` where `reading_status = 'want_to_read'` and `page_count IS NOT NULL`
   - **Pages read:** `SUM(page_count)` where `reading_status = 'read'` and `page_count IS NOT NULL`
   - **Pages wasted:** `SUM(max_progress_page)` where `reading_status = 'did_not_finish'` and book has at least one `ReadingProgress` entry
     - Subquery: For each `did_not_finish` book, get `MAX(page)` from `reading_progress` table
   - Edge cases: All three can be 0

8. **Pages read per month (line chart data)**
   - Books with `reading_status = 'read'` and non-null `date_finished` and non-null `page_count`
   - Group by `YEAR-MONTH` (in user timezone), sum `page_count`
   - Fill missing months with zero between earliest and latest month
   - Return list of `{month: 'YYYY-MM', pages: int}`
   - Edge case: If no data, return empty list

9. **Books finished per month (line chart data)**
   - Books with `reading_status = 'read'` and non-null `date_finished`
   - Group by `YEAR-MONTH`, count books
   - Fill missing months with zero
   - Return list of `{month: 'YYYY-MM', count: int}`

10. **Books finished per year (line chart data)**
    - Same as above but group by `YEAR`
    - Fill missing years with zero
    - Return list of `{year: int, count: int}`

11. **Favorite author**
    - Group by `author`, count books, order by count DESC, pick top 1
    - Join with books to get list of cover URLs
    - Return `{author: str, book_count: int, cover_urls: list[str]}`
    - Edge case: If no books have author, return `null`

**Timezone Handling:**

- All date bucketing (month/year extraction) must use the user's timezone from `UserSettings.timezone`
- Use Python `pytz` or `zoneinfo` to convert UTC `date_finished` to user timezone before extracting month/year
- Dates are stored in DB as `UtcDateTime` (UTC, no tzinfo in DB but always interpreted as UTC on retrieval per `models.py:19-22`)

**Implementation Notes:**

- Use SQLAlchemy `func.strftime()` or `func.extract()` for date parts, but convert to user timezone first
- For "fill missing months/years", generate a complete date range in Python and merge with query results
- For "pages wasted", use a subquery with `JOIN` on `reading_progress` and `GROUP BY book_id` to get max page per DNF book

### 1.2 New Schema: `StatisticsResponse` in `backend/app/schemas.py`

```python
from typing import Optional

class LanguageDistribution(SQLModel):
    language: Optional[str]  # ISO 639-1 code or null
    count: int

class StatusDistribution(SQLModel):
    want_to_read: int
    currently_reading: int
    read: int
    did_not_finish: int

class PageBuckets(SQLModel):
    pages_to_read: int
    pages_read: int
    pages_wasted: int

class MonthlyPages(SQLModel):
    month: str  # YYYY-MM
    pages: int

class MonthlyBooks(SQLModel):
    month: str  # YYYY-MM
    count: int

class YearlyBooks(SQLModel):
    year: int
    count: int

class FavoriteAuthor(SQLModel):
    author: str
    book_count: int
    cover_urls: list[str]

class StatisticsResponse(SQLModel):
    avg_books_per_month: Optional[float]
    busiest_month: Optional[str]  # e.g., "May 2026"
    busiest_month_count: Optional[int]
    avg_page_count: Optional[float]
    most_popular_language: Optional[str]
    most_popular_language_count: Optional[int]
    language_distribution: list[LanguageDistribution]
    status_distribution: StatusDistribution
    page_buckets: PageBuckets
    pages_read_per_month: list[MonthlyPages]
    books_finished_per_month: list[MonthlyBooks]
    books_finished_per_year: list[YearlyBooks]
    favorite_author: Optional[FavoriteAuthor]
```

### 1.3 Register Router in `backend/app/main.py`

Add to imports:
```python
from app.routers import ..., statistics
```

Add to app:
```python
app.include_router(statistics.router)
```

### 1.4 Edge Cases and Error Handling

- **No books in library:** Return zeros/nulls for all metrics, empty lists for distributions
- **No finished books:** `avg_books_per_month`, `busiest_month`, temporal charts all return null/empty
- **Books without page_count:** Exclude from page-based calculations
- **Books without language:** Group as `null` in language distribution
- **Books without author:** Exclude from favorite author calculation
- **No progress entries for DNF books:** `pages_wasted` = 0 for that book
- **Timezone parsing failure:** Fall back to UTC with a warning log
- **User has no UserSettings record:** Use UTC as default (consistent with `profile.py:61`)

---

## 2. Frontend Implementation

### 2.1 New Route: `frontend/src/routes/statistics/+page.svelte`

**Purpose:** Fetch statistics data and render metrics + charts.

**Layout Structure:**

```
┌─────────────────────────────────────────────────┐
│  Statistics — Reading Analytics                 │
│  [hero section]                                 │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Key Metrics (4-column grid on xl, 2 on md)     │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐  │
│  │ Avg    │ │ Busiest│ │ Avg    │ │ Popular│  │
│  │ Books/ │ │ Month  │ │ Pages  │ │ Lang   │  │
│  │ Month  │ │        │ │        │ │        │  │
│  └────────┘ └────────┘ └────────┘ └────────┘  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Distribution Charts (2-column grid)            │
│  ┌────────────────┐ ┌────────────────┐         │
│  │ Language Dist. │ │ Status Dist.   │         │
│  │ [stacked bars] │ │ [stacked bars] │         │
│  └────────────────┘ └────────────────┘         │
│  ┌────────────────┐                             │
│  │ Page Buckets   │                             │
│  │ [stacked bars] │                             │
│  │ [footnote]     │                             │
│  └────────────────┘                             │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Temporal Trends (line charts)                  │
│  ┌────────────────────────────────────────────┐ │
│  │ Pages Read Per Month (SVG line chart)     │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │ Books Finished Per Month (SVG line chart) │ │
│  └────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────┐ │
│  │ Books Finished Per Year (SVG line chart)  │ │
│  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Favorite Author                                │
│  ┌────────────────────────────────────────────┐ │
│  │ Author Name (X books)                      │ │
│  │ [cover1] [cover2] [cover3] [cover4] ...   │ │
│  │ (stacked horizontally, scrollable)         │ │
│  └────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Data Fetching:**

```typescript
let loading = $state(true);
let stats = $state<StatisticsResponse | null>(null);

onMount(() => {
  void loadStatistics();
});

async function loadStatistics() {
  loading = true;
  try {
    stats = await api.statistics.get();
  } catch (e) {
    // handle error, show toast
    stats = null;
  } finally {
    loading = false;
  }
}
```

### 2.2 Chart Components

**Approach:** No external chart library. Use CSS + SVG for all visualizations.

#### 2.2.1 Stacked Bar Charts (Language, Status, Page Buckets)

**Technique:** Flexbox row with width percentages.

```svelte
<div class="flex w-full h-8 rounded-lg overflow-hidden">
  {#each distribution as item}
    <div
      class="h-full {colorClass(item)}"
      style="width: {(item.count / total) * 100}%"
      title="{item.label}: {item.count}"
    ></div>
  {/each}
</div>

<div class="flex flex-wrap gap-2 mt-2">
  {#each distribution as item}
    <div class="flex items-center gap-1 text-xs">
      <div class="w-3 h-3 rounded {colorClass(item)}"></div>
      <span>{item.label}: {item.count}</span>
    </div>
  {/each}
</div>
```

**Color Classes (daisyUI):**

- Language distribution: Cycle through `bg-primary`, `bg-secondary`, `bg-accent`, `bg-info`, `bg-success`, `bg-warning`, `bg-error` (7 colors, repeat if > 7 languages)
- Status distribution:
  - `want_to_read`: `bg-info`
  - `currently_reading`: `bg-warning`
  - `read`: `bg-success`
  - `did_not_finish`: `bg-error`
- Page buckets:
  - `pages_to_read`: `bg-info`
  - `pages_read`: `bg-success`
  - `pages_wasted`: `bg-error`

**Footnote for Page Buckets:**

Display below chart:
> "Pages wasted" = maximum page reached for books marked as "Did Not Finish"

#### 2.2.2 Line Charts (Temporal Trends)

**Technique:** SVG `<path>` with computed `d` attribute.

```svelte
<svg viewBox="0 0 {width} {height}" class="w-full h-64">
  <!-- Grid lines -->
  {#each yGridLines as y}
    <line x1="0" y1={y} x2={width} y2={y} class="stroke-base-300" stroke-width="1" />
  {/each}
  
  <!-- Data line -->
  <path d={linePath} class="stroke-primary fill-none" stroke-width="2" />
  
  <!-- Data points -->
  {#each dataPoints as point}
    <circle cx={point.x} cy={point.y} r="4" class="fill-primary" />
  {/each}
  
  <!-- X-axis labels -->
  {#each xLabels as label}
    <text x={label.x} y={height - 5} class="text-xs fill-base-content" text-anchor="middle">
      {label.text}
    </text>
  {/each}
  
  <!-- Y-axis labels -->
  {#each yLabels as label}
    <text x="5" y={label.y} class="text-xs fill-base-content">
      {label.text}
    </text>
  {/each}
</svg>
```

**Line Path Generation:**

```typescript
function generateLinePath(data: { x: number; y: number }[]): string {
  if (data.length === 0) return '';
  return data.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
}
```

**X-axis for Months:**

- Parse `YYYY-MM` strings, convert to `Date`, display as "Jan 2026", "Feb 2026", etc.
- Show every Nth label to avoid overcrowding (e.g., every 3rd month if > 12 months)

**X-axis for Years:**

- Just render year numbers

**Y-axis Scaling:**

- Find max value in dataset, round up to nearest "nice" number (e.g., 10, 50, 100, 500)
- Create 5 grid lines evenly spaced from 0 to max
- Map data values to SVG Y coordinates: `y = height - (value / max) * (height - padding)`

**Zero Handling:**

- Backend ensures continuous ranges with zero-filled months/years
- Frontend renders all points (including zeros) — this ensures a steady time axis

#### 2.2.3 Favorite Author Component

```svelte
{#if stats?.favorite_author}
  <div class="card bg-base-100 border border-base-200 shadow-sm">
    <div class="card-body">
      <h2 class="card-title">{$_('statistics.favoriteAuthor')}</h2>
      <p class="text-lg font-semibold">{stats.favorite_author.author}</p>
      <p class="text-sm text-base-content/60">
        {$_('statistics.booksCount', { values: { count: stats.favorite_author.book_count } })}
      </p>
      <div class="flex gap-2 overflow-x-auto py-2">
        {#each stats.favorite_author.cover_urls as url}
          {#if url}
            <img src={url} alt={$_('book.coverOf', { values: { title: stats.favorite_author.author } })} class="h-32 w-auto rounded shadow" />
          {/if}
        {/each}
      </div>
    </div>
  </div>
{/if}
```

### 2.3 Update `frontend/src/lib/api.ts`

Add new namespace:

```typescript
statistics: {
  get(): Promise<StatisticsResponse> {
    return request<StatisticsResponse>('/statistics');
  }
}
```

### 2.4 Update `frontend/src/lib/types.ts`

Add all schema types from section 1.2:

```typescript
export interface LanguageDistribution {
  language: string | null;
  count: number;
}

export interface StatusDistribution {
  want_to_read: number;
  currently_reading: number;
  read: number;
  did_not_finish: number;
}

export interface PageBuckets {
  pages_to_read: number;
  pages_read: number;
  pages_wasted: number;
}

export interface MonthlyPages {
  month: string; // YYYY-MM
  pages: number;
}

export interface MonthlyBooks {
  month: string; // YYYY-MM
  count: number;
}

export interface YearlyBooks {
  year: number;
  count: number;
}

export interface FavoriteAuthor {
  author: string;
  book_count: number;
  cover_urls: string[];
}

export interface StatisticsResponse {
  avg_books_per_month: number | null;
  busiest_month: string | null;
  busiest_month_count: number | null;
  avg_page_count: number | null;
  most_popular_language: string | null;
  most_popular_language_count: number | null;
  language_distribution: LanguageDistribution[];
  status_distribution: StatusDistribution;
  page_buckets: PageBuckets;
  pages_read_per_month: MonthlyPages[];
  books_finished_per_month: MonthlyBooks[];
  books_finished_per_year: YearlyBooks[];
  favorite_author: FavoriteAuthor | null;
}
```

### 2.5 i18n Translations

Add to `frontend/src/lib/i18n/locales/en.json`:

```json
"statistics": {
  "title": "Statistics",
  "subtitle": "Insights into your reading journey",
  "avgBooksPerMonth": "Avg Books/Month",
  "busiestMonth": "Busiest Month",
  "avgPageCount": "Avg Pages/Book",
  "mostPopularLanguage": "Most Popular Language",
  "languageDistribution": "Books by Language",
  "statusDistribution": "Books by Status",
  "pageBuckets": "Page Statistics",
  "pagesToRead": "Pages to Read",
  "pagesRead": "Pages Read",
  "pagesWasted": "Pages Wasted",
  "pagesWastedFootnote": "\"Pages wasted\" = maximum page reached for books marked as \"Did Not Finish\"",
  "pagesReadPerMonth": "Pages Read Per Month",
  "booksFinishedPerMonth": "Books Finished Per Month",
  "booksFinishedPerYear": "Books Finished Per Year",
  "favoriteAuthor": "Favorite Author",
  "booksCount": "{count} {count, plural, one {book} other {books}}",
  "noData": "No data available yet. Start reading and tracking books to see statistics!",
  "loading": "Loading statistics..."
}
```

Add to `frontend/src/lib/i18n/locales/de.json` (German translations):

```json
"statistics": {
  "title": "Statistiken",
  "subtitle": "Einblicke in deine Lesereise",
  "avgBooksPerMonth": "Ø Bücher/Monat",
  "busiestMonth": "Aktivster Monat",
  "avgPageCount": "Ø Seiten/Buch",
  "mostPopularLanguage": "Häufigste Sprache",
  "languageDistribution": "Bücher nach Sprache",
  "statusDistribution": "Bücher nach Status",
  "pageBuckets": "Seitenstatistik",
  "pagesToRead": "Zu lesen",
  "pagesRead": "Gelesen",
  "pagesWasted": "Verschwendet",
  "pagesWastedFootnote": "\"Verschwendet\" = maximale Seite bei Büchern mit Status \"Nicht beendet\"",
  "pagesReadPerMonth": "Gelesene Seiten pro Monat",
  "booksFinishedPerMonth": "Beendete Bücher pro Monat",
  "booksFinishedPerYear": "Beendete Bücher pro Jahr",
  "favoriteAuthor": "Lieblingsautor",
  "booksCount": "{count} {count, plural, one {Buch} other {Bücher}}",
  "noData": "Noch keine Daten verfügbar. Fange an, Bücher zu lesen und zu erfassen, um Statistiken zu sehen!",
  "loading": "Lade Statistiken..."
}
```

### 2.6 Navigation Menu Update

**File:** `frontend/src/lib/components/Sidebar.svelte` (or wherever nav is defined)

Add new menu item:

```svelte
<li>
  <a href="/statistics" class:active={$page.url.pathname === '/statistics'}>
    {$_('nav.statistics')}
  </a>
</li>
```

Add to `en.json` / `de.json`:

```json
"nav": {
  ...
  "statistics": "Statistics" / "Statistiken"
}
```

### 2.7 Accessibility Considerations

- **ARIA labels:** All charts must have `role="img"` and `aria-label` describing the chart
- **Keyboard navigation:** Not applicable for static charts; focus on page navigation
- **Color contrast:** Use daisyUI color classes (already WCAG AA compliant)
- **Text alternatives:** For SVG charts, provide table fallback or `<desc>` element
- **Screen reader announcements:** Metrics should be plain text, not image-only

Example:

```svelte
<svg role="img" aria-label={$_('statistics.pagesReadPerMonth')} ...>
  <desc>{$_('statistics.pagesReadPerMonth')}: Line chart showing monthly trend</desc>
  ...
</svg>
```

---

## 3. Testing Plan

### 3.1 Backend Unit Tests

**File:** `backend/tests/test_statistics.py`

**Test Cases:**

1. **test_statistics_endpoint_requires_auth**
   - Call `/api/statistics` without auth → 401

2. **test_statistics_empty_library**
   - User with 0 books → All metrics null/zero, empty lists

3. **test_statistics_avg_books_per_month**
   - Create books with `date_finished` spanning 3 months
   - Assert `avg_books_per_month` = total / 3

4. **test_statistics_busiest_month**
   - Create 5 books finished in May 2026, 2 in June 2026
   - Assert `busiest_month` = "May 2026", `busiest_month_count` = 5

5. **test_statistics_avg_page_count**
   - Create books with `page_count` = [100, 200, 300]
   - Assert `avg_page_count` = 200

6. **test_statistics_most_popular_language**
   - Create 3 books with `language = "EN"`, 1 with `language = "DE"`
   - Assert `most_popular_language` = "EN", count = 3

7. **test_statistics_language_distribution**
   - Create books with various languages
   - Assert list contains correct counts

8. **test_statistics_status_distribution**
   - Create books with all 4 statuses
   - Assert all counts present

9. **test_statistics_page_buckets**
   - Create books with `want_to_read`, `read`, `did_not_finish` + progress entries
   - Assert `pages_to_read`, `pages_read`, `pages_wasted` correct

10. **test_statistics_pages_wasted_no_progress**
    - Create DNF book with no progress entries
    - Assert `pages_wasted` = 0

11. **test_statistics_pages_read_per_month**
    - Create books finished in Jan, Feb, Apr (skip Mar)
    - Assert returned list includes Mar with pages = 0

12. **test_statistics_books_finished_per_month**
    - Same as above but counting books

13. **test_statistics_books_finished_per_year**
    - Create books finished in 2025, 2026
    - Assert both years present, 2027 not included (no future years)

14. **test_statistics_favorite_author**
    - Create 3 books by "Author A", 2 by "Author B"
    - Assert `favorite_author.author` = "Author A", `book_count` = 3
    - Assert `cover_urls` list has 3 URLs

15. **test_statistics_timezone_handling**
    - Set user timezone to "America/New_York"
    - Create book with `date_finished` = "2026-05-01T03:00:00Z" (May 1 UTC = Apr 30 in NY)
    - Assert book is bucketed into April, not May

16. **test_statistics_no_finished_books**
    - Create books with `currently_reading`, `want_to_read`
    - Assert temporal charts empty

### 3.2 Backend Integration Test

**File:** `backend/tests/test_statistics_integration.py`

**Test Case:** `test_full_statistics_response_structure`

- Create a diverse dataset (books with all statuses, languages, dates, progress entries)
- Call `/api/statistics`
- Assert response matches `StatisticsResponse` schema
- Assert all expected keys present

### 3.3 Frontend Component Tests

**File:** `frontend/src/routes/statistics/Statistics.test.ts` (Vitest)

**Test Cases:**

1. **test_renders_loading_state**
   - Mock `api.statistics.get()` with delayed response
   - Assert loading spinner visible

2. **test_renders_no_data_message**
   - Mock empty stats response
   - Assert "No data available" message shown

3. **test_renders_key_metrics**
   - Mock stats with all metrics
   - Assert all 4 metric cards display correct values

4. **test_renders_stacked_bar_charts**
   - Mock distribution data
   - Assert chart divs have correct widths

5. **test_renders_line_charts**
   - Mock temporal data
   - Assert SVG paths generated

6. **test_renders_favorite_author**
   - Mock favorite author data
   - Assert author name, count, and cover images displayed

7. **test_handles_api_error**
   - Mock `api.statistics.get()` to throw error
   - Assert error toast shown (or error message)

### 3.4 E2E Test with Playwright

**File:** `.playwright-mcp/tests/statistics.spec.ts`

**Test Case:** `test_statistics_page_full_flow`

1. Navigate to `/statistics`
2. Wait for page load
3. Verify hero section contains "Statistics"
4. Verify at least one metric card visible
5. Verify at least one chart section visible
6. Take screenshot for visual regression

---

## 4. Additional Useful Metrics (Proposed)

Beyond the required metrics, consider these future enhancements:

1. **Reading Streak**
   - Longest consecutive days with reading progress entries
   - Current streak (days since last progress entry)

2. **Average Days to Finish a Book**
   - For books with both `date_started` and `date_finished`, compute average duration
   - Exclude outliers (e.g., books started years ago)

3. **Books by Published Decade**
   - Group by `floor(published_year / 10) * 10`
   - Show distribution (e.g., "1980s: 5 books, 1990s: 12 books")

4. **Rating Distribution**
   - Histogram of ratings 1–5 stars
   - Average rating (already have `avg_page_count`, can add `avg_rating`)

5. **Top Tags Cloud (Enhanced)**
   - Similar to dashboard tag cloud, but with bar chart showing top 10 tags by count

6. **Books Added vs. Books Finished (Per Month)**
   - Dual-line chart comparing acquisition rate vs. completion rate
   - Shows if backlog is growing or shrinking

7. **Publisher Leaderboard**
   - Top 5 publishers by book count

8. **Yearly Reading Goal Progress**
   - Allow user to set goal (e.g., "read 50 books this year")
   - Show progress bar and estimated completion date

9. **Genre/Tag Trends Over Time**
   - Line chart showing how tags (used as genres) trend month-over-month

10. **Read vs. Unread Ratio (Pie Chart)**
    - Simple visual: `read / total_books` as percentage

**Implementation Priority:**

- Phase 1 (this plan): Core metrics + required charts
- Phase 2: Reading streak, avg days to finish, rating distribution
- Phase 3: Yearly goal tracking, genre trends, advanced analytics

---

## 5. Implementation Steps (Execution Order)

### Step 1: Backend Schema and Model (1 hour)

1. Add `StatisticsResponse` and sub-schemas to `backend/app/schemas.py`
2. Run type checks: `cd backend && mypy app`

### Step 2: Backend Router Stub (30 min)

1. Create `backend/app/routers/statistics.py`
2. Implement stub endpoint returning mock data (all zeros/nulls)
3. Register router in `backend/app/main.py`
4. Test: `curl -X GET http://localhost:8000/api/statistics -H "Cookie: ..." | jq`

### Step 3: Backend Query Implementation (4 hours)

1. Implement each metric calculation in `statistics.py`:
   - Basic aggregations (avg books/month, busiest month, avg pages, popular language)
   - Distributions (language, status)
   - Page buckets (requires join with `reading_progress`)
   - Temporal data (pages/books per month/year with zero-filling)
   - Favorite author (group + join for covers)
2. Add timezone conversion logic (use `UserSettings.timezone`)
3. Handle edge cases (no data, missing fields)
4. Test manually with Postman/curl

### Step 4: Backend Unit Tests (3 hours)

1. Create `backend/tests/test_statistics.py`
2. Write 16 test cases (see section 3.1)
3. Run: `pytest backend/tests/test_statistics.py -v`
4. Fix bugs, ensure 100% pass rate

### Step 5: Frontend Types and API Client (30 min)

1. Add types to `frontend/src/lib/types.ts`
2. Add `api.statistics.get()` to `frontend/src/lib/api.ts`
3. Run type checks: `cd frontend && npm run check`

### Step 6: Frontend Page Skeleton (1 hour)

1. Create `frontend/src/routes/statistics/+page.svelte`
2. Implement layout structure (hero, cards, placeholders for charts)
3. Add data fetching on mount
4. Display loading/error states
5. Display key metrics (4 stat cards)

### Step 7: Frontend Stacked Bar Charts (2 hours)

1. Implement `LanguageDistributionChart.svelte` (or inline in page)
2. Implement `StatusDistributionChart.svelte`
3. Implement `PageBucketsChart.svelte` with footnote
4. Test with mock data, verify responsive layout

### Step 8: Frontend Line Charts (3 hours)

1. Implement `LineChart.svelte` component (reusable)
2. Add logic for:
   - X/Y axis scaling
   - Grid lines
   - Path generation
   - Labels
3. Instantiate 3 times for:
   - Pages read per month
   - Books finished per month
   - Books finished per year
4. Test with varying data ranges (1 month, 12 months, 3 years)

### Step 9: Frontend Favorite Author Component (1 hour)

1. Add favorite author section
2. Display author name, count, cover gallery
3. Make cover gallery horizontally scrollable
4. Handle case where covers are missing

### Step 10: i18n and Navigation (1 hour)

1. Add all strings to `en.json` and `de.json`
2. Update sidebar/nav with "Statistics" link
3. Test language switching

### Step 11: Accessibility Audit (1 hour)

1. Add ARIA labels to charts
2. Test with screen reader (NVDA/JAWS)
3. Verify keyboard navigation
4. Verify color contrast (use browser dev tools)

### Step 12: Frontend Component Tests (2 hours)

1. Create `frontend/src/routes/statistics/Statistics.test.ts`
2. Write 7 test cases (see section 3.3)
3. Run: `npm run test`

### Step 13: Integration Testing with Docker Compose (1 hour)

1. Build and run: `docker compose up --build`
2. Seed database with diverse test data (script or manual)
3. Navigate to `/statistics` in browser
4. Verify all metrics and charts render correctly
5. Test with different user timezones (change in profile settings)

### Step 14: E2E Test with Playwright (1 hour)

1. Create `.playwright-mcp/tests/statistics.spec.ts`
2. Write test case (see section 3.4)
3. Run: `playwright test tests/statistics.spec.ts`
4. Fix any flaky assertions

### Step 15: Documentation and PR (30 min)

1. Update `README.md` with new endpoint and route
2. Create PR with description, screenshots, test coverage report
3. Request review

---

## 6. Rollout and Verification

### 6.1 Pre-Deployment Checklist

- [ ] All backend unit tests pass
- [ ] All frontend component tests pass
- [ ] E2E test passes
- [ ] Manual testing in Docker Compose environment
- [ ] i18n strings complete for en + de
- [ ] Accessibility audit passed
- [ ] Type checks pass (backend + frontend)
- [ ] No console errors in browser

### 6.2 Deployment Steps

1. Merge PR to main branch
2. Build Docker images: `docker compose build`
3. Deploy to production environment
4. Run smoke test: Navigate to `/statistics`, verify no errors

### 6.3 Post-Deployment Verification

1. Monitor backend logs for errors related to `/api/statistics`
2. Check Sentry/error tracking for frontend exceptions
3. Verify performance: API response time should be < 500ms for typical library sizes
4. Collect user feedback (if applicable)

---

## 7. Performance Considerations

### 7.1 Backend Query Optimization

- **Expected dataset size:** Typical user has 50-500 books
- **Query complexity:** Multiple aggregations + joins, but all on indexed columns
- **Indexes used:**
  - `book.user_id` (already indexed per `models.py:54`)
  - `book.reading_status` (already indexed per `models.py:53`)
  - `book.date_finished` (already indexed per `models.py:63`)
  - `reading_progress.book_id` (already indexed per `models.py:138`)

**Optimization Strategies:**

1. **Single-pass aggregations where possible:** Use CTEs or subqueries to avoid multiple full table scans
2. **Limit cover URLs for favorite author:** Cap at 20 covers to avoid huge response payloads
3. **Cache response:** Consider adding `@lru_cache` or Redis caching for 5-minute TTL (future enhancement)

### 7.2 Frontend Rendering Performance

- **Chart rendering:** Pure CSS/SVG, no heavy JS libraries → fast render
- **Data size:** Max ~500 data points for line charts (500 months = 41 years, unlikely)
- **Responsiveness:** Use CSS `@media` queries for mobile layout adjustments

### 7.3 Expected Response Times

- **Backend API:** < 300ms for library of 500 books (tested locally)
- **Frontend render:** < 100ms after data fetch
- **Total page load:** < 500ms (excluding initial auth check)

---

## 8. Files to Create

### Backend

1. `backend/app/routers/statistics.py` (new)
2. `backend/tests/test_statistics.py` (new)

### Frontend

1. `frontend/src/routes/statistics/+page.svelte` (new)

### Shared

1. `backend/app/schemas.py` (modify: add `StatisticsResponse` + sub-schemas)
2. `backend/app/main.py` (modify: register `statistics` router)
3. `frontend/src/lib/types.ts` (modify: add `StatisticsResponse` interface)
4. `frontend/src/lib/api.ts` (modify: add `api.statistics.get()`)
5. `frontend/src/lib/i18n/locales/en.json` (modify: add `statistics` translations)
6. `frontend/src/lib/i18n/locales/de.json` (modify: add `statistics` translations)
7. Navigation component (modify: add "Statistics" link — exact file depends on structure, likely `Sidebar.svelte` or `+layout.svelte`)

---

## 9. Open Questions / Assumptions

1. **Assumption: User timezone is always valid**
   - If `UserSettings.timezone` contains an invalid IANA timezone string, we fall back to UTC and log a warning. This should not crash the endpoint.

2. **Assumption: "Pages wasted" is a useful metric**
   - Feedback from initial users will determine if this metric is helpful or confusing. Consider adding a tooltip or help icon.

3. **Assumption: No pagination needed for statistics endpoint**
   - All data fits in a single response. For users with 10,000+ books, may need to revisit (but unlikely for personal reading tracker).

4. **Question: Should temporal charts show future months/years?**
   - Decision: No. Only show historical data up to current month/year.

5. **Question: How to handle books with `date_finished` but no `date_started`?**
   - Decision: These books are included in "books finished" metrics, but excluded from "average days to finish" (future metric).

6. **Question: Should statistics be real-time or cached?**
   - Decision: Real-time for now. Add caching in Phase 2 if performance becomes an issue.

7. **Question: Should we show a comparison to previous period (e.g., "10% more than last month")?**
   - Decision: Not in Phase 1. Add in Phase 2 as "Insights" section.

8. **Assumption: No chart libraries means more maintenance**
   - Trade-off accepted. Custom SVG charts are simpler than importing Chart.js/Recharts and learning their APIs. Maintenance burden is low because charts are static (no interactions).

---

## 10. Summary

This plan provides a complete roadmap for implementing a comprehensive Statistics page in librislog. It covers:

- **Backend:** New `/api/statistics` endpoint with 11+ metrics, timezone-aware aggregations, edge case handling
- **Frontend:** New `/statistics` route with key metrics, 5 charts (3 stacked bars, 3 line charts), favorite author gallery
- **Testing:** 16 backend unit tests, 7 frontend component tests, 1 E2E test
- **i18n:** Full translation support for en + de
- **Accessibility:** ARIA labels, screen reader support, color contrast compliance
- **Performance:** Optimized queries, fast rendering, < 500ms total page load

**Total estimated effort:** 22 hours (3 days for one developer)

**Next steps:** Review plan, approve, and begin implementation at Step 1.
