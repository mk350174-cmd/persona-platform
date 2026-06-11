# Analytics & Reporting — Persona Platform

Comprehensive guide to the analytics subsystem: what metrics are tracked, how
they are calculated, how to query them via the REST API, and how to hook them
into Grafana or export them as CSV.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Dashboard Metrics](#dashboard-metrics)
3. [Persona Popularity Metrics](#persona-popularity-metrics)
4. [User Engagement Metrics](#user-engagement-metrics)
5. [Revenue Tracking (MRR, ARPU, Churn)](#revenue-tracking)
6. [Cohort Analysis Methodology](#cohort-analysis-methodology)
7. [DAU/MAU Tracking](#daumau-tracking)
8. [Export Formats (CSV, JSON)](#export-formats)
9. [Grafana Dashboard Integration](#grafana-dashboard-integration)
10. [API Reference with Examples](#api-reference)

---

## Architecture Overview

The analytics subsystem is implemented across two files:

| File | Purpose |
|---|---|
| `api/analytics.py` | Pure data layer — dataclasses + SQLAlchemy query functions |
| `api/routers/analytics.py` | FastAPI router — HTTP endpoints, auth checks, response shaping |

**No new tables are introduced.** All queries run against existing tables:

| Table | Used For |
|---|---|
| `users` | User counts, signup timestamps, retention |
| `purchases` | Revenue totals, persona popularity, all-time revenue per persona |
| `subscriptions` | MRR calculation, subscriber counts, churn detection |
| `api_key_usage` | Active users (DAU/MAU), persona usage frequency, session estimation |

All aggregate queries use `sqlalchemy.func` (`func.count`, `func.sum`,
`func.min`, `func.max`, `func.count(distinct(...))`) — no Python-side loops
over result sets.

---

## Dashboard Metrics

**Endpoint:** `GET /analytics/dashboard`  
**Auth:** Admin role required

The dashboard summary provides a real-time snapshot of platform health.

### Metrics Explained

| Field | Type | Description |
|---|---|---|
| `total_users` | int | All non-deleted users in the database |
| `active_users_7d` | int | Distinct users with at least one API call in the last 7 days |
| `active_users_30d` | int | Distinct users with at least one API call in the last 30 days |
| `total_personas` | int | Personas known to the system (max of distinct purchased IDs vs. used IDs) |
| `total_purchases` | int | Total non-deleted purchase records |
| `total_revenue_usd` | float | Sum of all `purchases.amount_usd` (stored as cents, returned as USD) |
| `mrr` | float | Monthly Recurring Revenue from active subscriptions (see [Revenue Tracking](#revenue-tracking)) |
| `top_personas` | list | Top 10 personas ranked by purchase count with revenue per persona |
| `recent_signups` | int | Users created in the last 24 hours |

### How Active Users Are Counted

Active users are counted from `api_key_usage.timestamp` using
`COUNT(DISTINCT user_id)` within the time window. This means a user is "active"
if they made at least one API call during the window — not just if they logged in.

### Example Response

```json
{
  "total_users": 1420,
  "active_users_7d": 312,
  "active_users_30d": 847,
  "total_personas": 495,
  "total_purchases": 2103,
  "total_revenue_usd": 18450.00,
  "mrr": 4261.50,
  "top_personas": [
    {"persona_id": "persona_napoleon", "purchases": 87, "revenue_usd": 1305.00},
    {"persona_id": "persona_darwin",   "purchases": 74, "revenue_usd": 1110.00}
  ],
  "recent_signups": 23
}
```

---

## Persona Popularity Metrics

### Top Personas

**Endpoint:** `GET /analytics/personas/top?limit=10&days=30`

Personas are ranked by **total API call volume** (`api_key_usage`) in the
specified window. If no usage data exists (fresh install), the fallback ranks
by **purchase count** instead.

For each persona the response includes:

| Field | Description |
|---|---|
| `total_conversations` | Estimated sessions (distinct user-day pairs in the window) |
| `total_messages` | Raw count of API calls with this `persona_id` |
| `unique_users` | Distinct `user_id` values that called this persona |
| `avg_session_length` | `total_messages / unique_users` (messages per user in window) |
| `revenue_usd` | All-time purchase revenue for this persona (not windowed) |

### Single Persona

**Endpoint:** `GET /analytics/personas/{persona_id}?days=30`

Same metrics as above but for a specific persona ID.

### Conversation Estimation

There is no explicit "session" or "conversation" table. Conversations are
estimated as **distinct (user_id, calendar-day) pairs** in `api_key_usage`
for the persona and time window. This is a conservative lower-bound — if a
user chats in the morning and evening, that still counts as one conversation.

---

## User Engagement Metrics

**Endpoint:** `GET /analytics/users/{user_id}`  
**Auth:** User can view own stats; admin can view any user

| Field | Description |
|---|---|
| `total_sessions` | Distinct calendar days with any API activity |
| `total_messages` | Total API calls from this user across all personas |
| `favorite_persona` | `persona_id` with the most API calls from this user |
| `avg_daily_messages` | `total_messages / total_sessions` |
| `retention_days` | Calendar days between first and last API activity |
| `tier` | Active subscription tier or `"free"` |

### Session Definition

A **session** is defined as a distinct calendar day on which the user made at
least one API call. This is a pragmatic approximation that works without
session-tracking infrastructure. For more granular session tracking, instrument
the WebSocket chat handler (`api/ws.py`) and add explicit session open/close
events to `api_key_usage`.

### Retention Days

`retention_days = (last_usage_timestamp - first_usage_timestamp).days`

This measures **engagement span** — how long the user has been actively using
the platform. It does not measure churn. A user with `retention_days = 365` but
no activity in the last 90 days may be churned; use the cohort analysis for
forward-looking churn signals.

---

## Revenue Tracking

### MRR Calculation

Monthly Recurring Revenue is computed from **active subscriptions** using the
pricing table in `SUBSCRIPTION_TIERS`:

| Tier | Price | Billing | Monthly Contribution |
|---|---|---|---|
| `basic_monthly` | $9.00 | monthly | $9.00 |
| `basic_annual` | $99.00 | annual | $8.25 |
| `pro_monthly` | $29.00 | monthly | $29.00 |
| `pro_annual` | $290.00 | annual | $24.17 |
| `basic` (legacy) | $9.00 | monthly | $9.00 |
| `pro` (legacy) | $29.00 | monthly | $29.00 |

MRR = sum over all active subscriptions of (monthly price for that tier).

Annual plans are normalised to monthly by dividing by 12. This is the standard
SaaS MRR definition.

### ARPU

Average Revenue Per User:

```
ARPU = MRR / active_subscriber_count
```

Only paying subscribers are included in the denominator — free users are
excluded. This gives a clean signal of monetisation efficiency among paying
customers.

### Churn

**Churned subscribers** in the revenue report are subscriptions whose `status`
is `"cancelled"` and whose `created_at` falls within the report period window.
This is an approximation: it captures subscriptions that were created **and**
cancelled within the window, not long-lived subscriptions that were cancelled
during the window. For production use, add a `cancelled_at` column to the
`subscriptions` table.

### Revenue Report Periods

| Period | Window |
|---|---|
| `daily` | Last 24 hours |
| `weekly` | Last 7 days |
| `monthly` | Last 30 days |

Note: "monthly" here means a rolling 30-day window, not a calendar month. For
calendar-month reports, use the cohort API with `month=YYYY-MM`.

### Revenue from One-Time Purchases vs. Subscriptions

`total_revenue_usd` in the revenue report sums **one-time persona purchases**
(`purchases.amount_usd`) within the window. Subscription revenue is captured
separately via `mrr`. To get combined revenue:

```
combined_revenue = total_revenue_usd + mrr
```

---

## Cohort Analysis Methodology

**Endpoint:** `GET /analytics/retention?month=2024-06`

Cohort analysis groups users by their **signup month** and tracks what fraction
remain active in each subsequent month.

### How It Works

1. **Define the cohort**: all users whose `users.created_at` falls within the
   specified calendar month.
2. **Measure retention per month**: for each subsequent month (0 through 12),
   count how many cohort members made at least one API call
   (`api_key_usage` activity).
3. **Calculate retention rate**: `active_users_in_month / cohort_size`.

Month 0 (the signup month) always has a retention rate of 1.0 (100%) — every
cohort member is counted as active in the month they signed up.

### Response Structure

```json
{
  "cohort_month": "2024-06",
  "cohort_size": 142,
  "retention": {
    "month_0": 142,
    "month_1": 98,
    "month_2": 71,
    "month_3": 55
  },
  "retention_rates": {
    "month_0": 1.0,
    "month_1": 0.6901,
    "month_2": 0.5,
    "month_3": 0.3873
  }
}
```

### Interpreting the Data

- **Month 1 retention > 0.5** is a healthy signal for a B2C SaaS product.
- **Flattening of the retention curve** (e.g. stabilising at 0.20 after month 3)
  indicates a retained core user base.
- **Drop to zero** in early months suggests onboarding friction.

### Limitations

- Activity is measured by API calls, not by logins or engagement depth.
- If a user buys a persona bundle but never uses the API, they appear churned.
- Cohort data is computed on the fly — for large user bases, consider
  materialising this into a `cohort_retention` summary table.

---

## DAU/MAU Tracking

**Endpoint:** `GET /analytics/dau?days=30`

Returns a day-by-day count of **Daily Active Users** (DAU), where a user is
"active" on a day if they made at least one API call.

### Response

```json
{
  "days": 30,
  "series": [
    {"date": "2024-06-01", "count": 34},
    {"date": "2024-06-02", "count": 41},
    ...
    {"date": "2024-06-30", "count": 58}
  ],
  "total_data_points": 31
}
```

Days with zero activity are included with `count: 0`.

### MAU Calculation

MAU is not a direct endpoint but can be derived:

```
MAU = active_users_30d  (from /analytics/dashboard)
```

### DAU/MAU Ratio (Stickiness)

```
stickiness = mean(dau_series) / mau
```

Industry benchmarks: 0.20–0.25 = healthy; > 0.50 = exceptional.

### Querying DAU with Postgres

The underlying query uses `DATE(timestamp)` to group by calendar day:

```sql
SELECT
    DATE(timestamp) AS day,
    COUNT(DISTINCT user_id) AS dau
FROM api_key_usage
WHERE timestamp >= NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp)
ORDER BY DATE(timestamp);
```

SQLite uses `strftime('%Y-%m-%d', timestamp)` as an equivalent.

---

## Export Formats

### CSV Export

**Endpoint:** `GET /analytics/export/csv?type=revenue&period=monthly`

Supported export types:

| type | description | key query params |
|---|---|---|
| `revenue` | Revenue report + top personas | `period` (daily/weekly/monthly) |
| `dau` | Daily active users time series | `days` (1-365) |
| `top_personas` | Top personas by usage | `days`, `limit` |

The response has `Content-Type: text/csv` and
`Content-Disposition: attachment; filename="<type>_<params>.csv"`.

#### Revenue CSV Layout

```
period,total_revenue_usd,new_subscribers,churned_subscribers,mrr,arpu
monthly,18450.00,34,8,4261.50,125.34

persona_id,revenue_usd,purchases
persona_napoleon,1305.00,87
persona_darwin,1110.00,74
```

#### DAU CSV Layout

```
date,active_users
2024-06-01,34
2024-06-02,41
...
```

#### Top Personas CSV Layout

```
persona_id,total_conversations,total_messages,unique_users,avg_session_length,revenue_usd
persona_napoleon,87,420,87,4.83,1305.00
persona_darwin,74,310,74,4.19,1110.00
```

### JSON (Default)

All endpoints return JSON by default. Clients that need structured data for
dashboard rendering should use JSON; CSV exports are intended for spreadsheet
analysis or data pipeline ingestion.

---

## Grafana Dashboard Integration

The analytics REST API can feed a Grafana instance via the
[JSON Datasource plugin](https://grafana.com/grafana/plugins/simpod-json-datasource/).

### Setup Steps

1. Install the SimpleJSON datasource plugin in Grafana.
2. Add a new datasource:
   - **URL**: `http://your-api-host:8000`
   - **Access**: Server (backend) or Browser
   - **Custom HTTP headers**: `X-API-Key: prs_<admin-key>`
3. Create a dashboard and add panels with queries against the analytics endpoints.

### Recommended Panels

| Panel | Endpoint | Visualization |
|---|---|---|
| DAU Trend (30d) | `/analytics/dau?days=30` | Time series |
| Revenue by Period | `/analytics/revenue?period=monthly` | Stat (MRR, ARPU) |
| Top 10 Personas | `/analytics/personas/top?limit=10` | Bar chart |
| New Signups | `/analytics/dashboard` → `recent_signups` | Gauge |
| Active Users | `/analytics/dashboard` → `active_users_7d` | Stat |
| Cohort Retention | `/analytics/retention?month=YYYY-MM` | Heatmap |

### Prometheus Scrape

For Prometheus-style metrics (counters, gauges, histograms), use the
existing `/observability/metrics` endpoint which emits structured metric
objects compatible with Prometheus scrape format. The analytics endpoints
are optimised for dashboard queries rather than time-series scraping.

### Alert Rules

Suggested Grafana alert conditions:

| Alert | Condition |
|---|---|
| Revenue drop | `total_revenue_usd` (weekly) falls > 30% vs. prior week |
| DAU drop | 7-day average DAU drops > 20% vs. prior 7-day average |
| Churn spike | `churned_subscribers` (weekly) > 2× new_subscribers |
| Inactive platform | `active_users_7d` < 10 |

---

## API Reference

All analytics endpoints are under the `/analytics` prefix and require a valid
API key (`X-API-Key: prs_...` or `Authorization: Bearer prs_...`). Most
endpoints are **admin-only** — set `users.role = 'admin'` on the calling user.

### GET /analytics/dashboard

Returns platform-wide KPIs.

**Auth:** Admin  
**Query params:** none

```bash
curl -H "X-API-Key: prs_YOUR_KEY" \
  http://localhost:8000/analytics/dashboard
```

---

### GET /analytics/personas/top

**Auth:** Admin  
**Query params:**
- `limit` (int, 1–100, default 10)
- `days` (int, 1–365, default 30)

```bash
curl -H "X-API-Key: prs_YOUR_KEY" \
  "http://localhost:8000/analytics/personas/top?limit=5&days=7"
```

---

### GET /analytics/personas/{persona_id}

**Auth:** Admin  
**Path params:** `persona_id` (string)  
**Query params:** `days` (int, 1–365, default 30)

```bash
curl -H "X-API-Key: prs_YOUR_KEY" \
  "http://localhost:8000/analytics/personas/persona_napoleon?days=30"
```

**Response:**
```json
{
  "persona_id": "persona_napoleon",
  "total_conversations": 87,
  "total_messages": 420,
  "unique_users": 87,
  "avg_session_length": 4.83,
  "revenue_usd": 1305.00,
  "days": 30
}
```

---

### GET /analytics/users/{user_id}

**Auth:** Own user or admin  
**Path params:** `user_id` (string)

```bash
# Self
curl -H "X-API-Key: prs_YOUR_KEY" \
  http://localhost:8000/analytics/users/me_user_id

# Admin querying another user
curl -H "X-API-Key: prs_ADMIN_KEY" \
  http://localhost:8000/analytics/users/other_user_id
```

**Response:**
```json
{
  "user_id": "abc123",
  "total_sessions": 14,
  "total_messages": 182,
  "favorite_persona": "persona_darwin",
  "avg_daily_messages": 13.0,
  "retention_days": 28,
  "tier": "pro_monthly"
}
```

---

### GET /analytics/revenue

**Auth:** Admin  
**Query params:** `period` (daily | weekly | monthly, default monthly)

```bash
curl -H "X-API-Key: prs_ADMIN_KEY" \
  "http://localhost:8000/analytics/revenue?period=weekly"
```

**Response:**
```json
{
  "period": "weekly",
  "total_revenue_usd": 3210.00,
  "new_subscribers": 12,
  "churned_subscribers": 3,
  "mrr": 4261.50,
  "arpu": 125.34,
  "top_personas": [
    {"persona_id": "persona_napoleon", "revenue_usd": 450.00, "purchases": 30}
  ]
}
```

---

### GET /analytics/dau

**Auth:** Admin  
**Query params:** `days` (int, 1–365, default 30)

```bash
curl -H "X-API-Key: prs_ADMIN_KEY" \
  "http://localhost:8000/analytics/dau?days=7"
```

**Response:**
```json
{
  "days": 7,
  "series": [
    {"date": "2024-06-04", "count": 41},
    {"date": "2024-06-05", "count": 38},
    {"date": "2024-06-06", "count": 0},
    {"date": "2024-06-07", "count": 52},
    {"date": "2024-06-08", "count": 59},
    {"date": "2024-06-09", "count": 67},
    {"date": "2024-06-10", "count": 61}
  ],
  "total_data_points": 7
}
```

---

### GET /analytics/retention

**Auth:** Admin  
**Query params:** `month` (string, YYYY-MM format, required)

```bash
curl -H "X-API-Key: prs_ADMIN_KEY" \
  "http://localhost:8000/analytics/retention?month=2024-06"
```

**Response:**
```json
{
  "cohort_month": "2024-06",
  "cohort_size": 142,
  "retention": {
    "month_0": 142,
    "month_1": 98,
    "month_2": 71
  },
  "retention_rates": {
    "month_0": 1.0,
    "month_1": 0.6901,
    "month_2": 0.5
  }
}
```

---

### GET /analytics/export/csv

**Auth:** Admin  
**Query params:**
- `type` (revenue | dau | top_personas, default revenue)
- `period` (daily | weekly | monthly, for revenue exports)
- `days` (int, for dau / top_personas exports)
- `limit` (int, for top_personas exports)

```bash
# Revenue report as CSV
curl -H "X-API-Key: prs_ADMIN_KEY" \
  "http://localhost:8000/analytics/export/csv?type=revenue&period=monthly" \
  -o revenue_monthly.csv

# DAU 30 days as CSV
curl -H "X-API-Key: prs_ADMIN_KEY" \
  "http://localhost:8000/analytics/export/csv?type=dau&days=30" \
  -o dau_30d.csv

# Top 20 personas over last 7 days as CSV
curl -H "X-API-Key: prs_ADMIN_KEY" \
  "http://localhost:8000/analytics/export/csv?type=top_personas&days=7&limit=20" \
  -o top_personas_7d.csv
```

---

## Notes on Database Compatibility

All queries are written to be compatible with both **SQLite** (development /
MVP) and **PostgreSQL** (production). The key difference is date truncation:

| Operation | SQLite | PostgreSQL |
|---|---|---|
| Cast to date | `cast(ts, Date)` (may fall back) | `cast(ts, Date)` |
| Group by day | `DATE(timestamp)` | `DATE(timestamp)` |

The `get_user_engagement` function uses a try/except block to handle edge cases
where `cast(ts, Date)` raises on older SQLite versions, falling back to a rough
approximation.

For production Postgres deployments, consider adding a **partial index** on
`api_key_usage(timestamp)` and `api_key_usage(persona_id, timestamp)` to
speed up the analytics window queries.

```sql
-- Recommended indexes for analytics performance
CREATE INDEX CONCURRENTLY ix_api_key_usage_ts_covering
    ON api_key_usage (timestamp DESC)
    INCLUDE (user_id, persona_id);

CREATE INDEX CONCURRENTLY ix_purchases_ts_persona
    ON purchases (purchased_at DESC, persona_id)
    WHERE deleted_at IS NULL;
```
