# Feature Flags (H92) — Server-Side A/B Testing

**Status:** Server-side feature flags with percentage-based rollouts and user targeting  
**API Endpoint:** `/flags`  
**Authentication:** X-API-Key (authenticated users)  
**Database:** PostgreSQL (feature_flags, flag_evaluations tables)

---

## Table of Contents

1. [Overview](#overview)
2. [Use Cases](#use-cases)
3. [Feature Flag Types](#feature-flag-types)
4. [Flag Evaluation Logic](#flag-evaluation-logic)
5. [API Reference](#api-reference)
6. [Examples](#examples)
7. [Best Practices](#best-practices)
8. [Analytics & Metrics](#analytics--metrics)
9. [Troubleshooting](#troubleshooting)

---

## Overview

**Feature flags** allow you to:
- **Gradually roll out** new features (10% → 50% → 100%)
- **Target specific users** or user segments
- **A/B test** multiple variants and measure performance
- **Kill switches** for failing features (disable instantly)
- **Soft launch** features to early adopters

**Key benefits:**
- ✅ Deploy code without releasing features
- ✅ A/B test new experiences with subset of users
- ✅ Instant rollback without redeployment
- ✅ Reduce risk of production issues
- ✅ Measure impact before full rollout

**Architecture:**
```
┌─────────────────────────────────┐
│ Admin creates/updates flag      │
│ POST /flags                     │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│ Flag stored in PostgreSQL       │
│ feature_flags table             │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│ User requests /flags/{name}/eval│
│ Server evaluates context:       │
│  - User ID                      │
│  - User segments                │
│  - User tier                    │
│  - Rollout percentage           │
│  - Target user list             │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│ Flag evaluation result          │
│ enabled: true/false             │
│ variant: "control"|"variant_a"  │
└────────────┬────────────────────┘
             │
┌────────────▼────────────────────┐
│ Log evaluation for analytics    │
│ flag_evaluations table          │
└─────────────────────────────────┘
```

---

## Use Cases

### 1. Gradual Feature Rollout (Canary)

```
Scenario: Launch new checkout UI
Rollout:  10% → 50% → 100% over 1 week

Day 1:  10% of users see new UI
        - Monitor: error rate, conversion rate
        - If healthy: proceed
        - If issues: disable instantly

Day 4:  50% of users see new UI
        - Further validation
        - Compare metrics: new vs old

Day 7:  100% of users on new UI
        - Old UI fully deprecated
```

### 2. Targeted Feature Release

```
Scenario: Early access to premium features
Targeting:
- Only users in "pro" tier
- Only users in ["beta_testers"] segment
- Only specific user IDs: ["usr_123", "usr_456"]
- Expires: 2024-12-31

Result: Feature available only to target users
```

### 3. A/B Testing

```
Scenario: Test two checkout flows
Variants: ["control", "variant_a"]
Rollout:  50% each (deterministic per user)

User usr_111: Gets "variant_a" (hash % 100 = 45)
User usr_222: Gets "control" (hash % 100 = 12)

Metrics collected:
- Variant A: 2.5% conversion rate
- Control: 2.0% conversion rate
- Conclusion: Variant A wins (statistically significant)
```

### 4. Emergency Kill Switch

```
Scenario: Bug discovered in production
Action: Disable flag immediately

Before:  enabled=true, rollout=100%
After:   enabled=false, rollout=0%

Result: Feature instantly disabled for all users
        (no redeployment needed)
```

---

## Feature Flag Types

### Boolean Flag

**Simple on/off flag** — Feature enabled or disabled.

```
name: "new_checkout_ui"
enabled: true
rollout_percentage: 50
variants: []  # Empty = boolean flag
```

**Evaluation:**
```
GET /flags/new_checkout_ui/evaluate
→ {
  "enabled": true,
  "variant": "enabled"  # String for API consistency
}
```

### Percentage Rollout

**Gradual rollout to percentage of users** — Deterministic (same user always gets same variant).

```
name: "new_compile_api"
enabled: true
rollout_percentage: 25  # 25% of users
variants: []
```

**How it works:**
```
user_id = "usr_abc123"
hash = MD5(user_id) % 100  # Deterministic 0-99
enabled = hash < 25  # If hash < 25%, user gets flag

User usr_abc123: hash=12 < 25 → ENABLED
User usr_def456: hash=87 > 25 → DISABLED
```

### A/B Test (Multi-Variant)

**Multiple variants for testing** — Users consistently assigned same variant.

```
name: "checkout_ui_test"
enabled: true
rollout_percentage: 100  # All users
variants: ["control", "variant_a", "variant_b"]
```

**Allocation:**
```
hash = MD5(user_id) % 100
variant_index = hash % 3  # Number of variants

If hash=10: 10 % 3 = 1 → "variant_a"
If hash=45: 45 % 3 = 0 → "control"
If hash=92: 92 % 3 = 2 → "variant_b"
```

### Segment Targeting

**Enable only for users in specific segments.**

```
name: "premium_features"
enabled: true
rollout_percentage: 100
target_segments: ["pro", "enterprise"]  # Only these tiers
variants: []
```

**Evaluation context:**
```
POST /flags/premium_features/evaluate
body: { "segments": ["pro", "beta_tester"] }

Evaluation:
1. Is flag enabled? Yes
2. User segments: ["pro", "beta_tester"]
3. Target segments: ["pro", "enterprise"]
4. Match: ["pro"] ∩ ["pro", "enterprise"] = YES
5. Result: ENABLED
```

### Tier-Based Targeting

**Enable only for users of specific pricing tiers.**

```
name: "priority_support"
enabled: true
rollout_percentage: 100
target_tiers: ["pro", "enterprise"]
```

**Evaluation:**
```
POST /flags/priority_support/evaluate
body: { "tier": "pro" }

Evaluation:
1. User tier: "pro"
2. Target tiers: ["pro", "enterprise"]
3. "pro" in ["pro", "enterprise"]? YES
4. Result: ENABLED
```

### Explicit User Targeting

**Enable for specific users (allowlist).**

```
name: "internal_testing"
enabled: true
rollout_percentage: 0  # Not rolled out yet
targeted_user_ids: ["usr_admin", "usr_qa", "usr_product"]
```

**Evaluation:**
```
user_id = "usr_admin"

Evaluation:
1. Is user in targeted list? YES
2. Result: ENABLED (regardless of rollout%)
```

---

## Flag Evaluation Logic

### Evaluation Order

```python
def should_enable_flag(flag, context):
    # 1. Must be enabled globally
    if not flag.enabled:
        return False
    
    # 2. Check expiration
    if flag.expires_at and now > expires_at:
        return False
    
    # 3. Always enable explicitly targeted users (allowlist)
    if context.user_id in flag.targeted_user_ids:
        return True
    
    # 4. Check segment targeting
    if flag.target_segments:
        if context.segments not in flag.target_segments:
            return False
    
    # 5. Check tier targeting
    if flag.target_tiers:
        if context.user_tier not in flag.target_tiers:
            return False
    
    # 6. Check percentage rollout
    hash = MD5(user_id) % 100
    return hash < flag.rollout_percentage
```

### Variant Allocation

For flags with variants (A/B tests):

```python
def get_variant_for_user(user_id, variants):
    hash = MD5(user_id) % 100
    variant_index = hash % len(variants)
    return variants[variant_index]
    # User always gets same variant (deterministic)
```

### Examples

**Example 1: Basic percentage rollout**
```
Flag: {
  name: "feature_x",
  enabled: true,
  rollout_percentage: 50,
  variants: [],
  target_segments: [],
  target_tiers: []
}

User: usr_abc123
Hash: MD5("usr_abc123") % 100 = 23
23 < 50? YES → ENABLED
```

**Example 2: Segment + tier targeting + rollout**
```
Flag: {
  name: "feature_y",
  enabled: true,
  rollout_percentage: 75,
  target_segments: ["beta"],
  target_tiers: ["pro", "enterprise"]
}

User: usr_def456
- User tier: "pro" ✓
- User segments: ["beta", "early_adopter"] ✓ (has "beta")
- Hash: 45 < 75? ✓
→ ENABLED

User: usr_ghi789
- User tier: "free" ✗ (not in ["pro", "enterprise"])
→ DISABLED (regardless of rollout%)
```

**Example 3: Explicit targeting overrides percentage**
```
Flag: {
  name: "vip_feature",
  enabled: true,
  rollout_percentage: 0,  # 0% rollout
  targeted_user_ids: ["usr_vip1", "usr_vip2"]
}

User: usr_vip1
- In targeted list? YES
→ ENABLED (overrides 0% rollout)

User: usr_other
- In targeted list? NO
- Hash: 50 < 0? NO
→ DISABLED
```

---

## API Reference

### List Flags

```
GET /flags
```

**Response:**
```json
{
  "flags": [
    {
      "id": "ff_abc123",
      "name": "new_ui",
      "description": "New checkout UI experiment",
      "enabled": true,
      "rollout_percentage": 50,
      "variants": ["control", "variant_a"],
      "target_user_ids": [],
      "target_segments": ["beta"],
      "target_tiers": ["pro"],
      "expires_at": "2024-12-31T23:59:59Z",
      "created_at": "2024-06-10T10:00:00Z",
      "updated_at": "2024-06-10T15:30:00Z"
    }
  ],
  "total": 1
}
```

### Get Flag

```
GET /flags/{flag_name}
```

**Response:**
```json
{
  "id": "ff_abc123",
  "name": "new_ui",
  "description": "New checkout UI experiment",
  "enabled": true,
  "rollout_percentage": 50,
  "variants": ["control", "variant_a"],
  "target_user_ids": [],
  "target_segments": ["beta"],
  "target_tiers": ["pro"],
  "expires_at": "2024-12-31T23:59:59Z",
  "created_at": "2024-06-10T10:00:00Z",
  "updated_at": "2024-06-10T15:30:00Z"
}
```

### Create Flag

```
POST /flags
```

**Request:**
```json
{
  "name": "new_ui",
  "description": "New checkout UI experiment",
  "enabled": false,
  "rollout_percentage": 0,
  "variants": ["control", "variant_a"],
  "target_segments": ["beta"],
  "target_tiers": ["pro"],
  "expires_at": "2024-12-31T23:59:59Z"
}
```

**Response:**
```json
{
  "id": "ff_abc123",
  "name": "new_ui",
  "message": "Feature flag created successfully",
  ...
}
```

### Update Flag

```
PATCH /flags/{flag_name}
```

**Request (partial):**
```json
{
  "enabled": true,
  "rollout_percentage": 25
}
```

**Response:**
```json
{
  "id": "ff_abc123",
  "name": "new_ui",
  "enabled": true,
  "rollout_percentage": 25,
  "message": "Feature flag updated successfully",
  ...
}
```

### Delete Flag

```
DELETE /flags/{flag_name}
```

**Response:**
```json
{
  "message": "Feature flag 'new_ui' deleted successfully"
}
```

### Evaluate Flag (Client-Side)

```
POST /flags/{flag_name}/evaluate
```

**Request:**
```json
{
  "segments": ["beta", "early_adopter"],
  "tier": "pro"
}
```

**Response:**
```json
{
  "flag_name": "new_ui",
  "user_id": "usr_abc123",
  "enabled": true,
  "variant": "variant_a",
  "context": {
    "segments": ["beta", "early_adopter"],
    "tier": "pro"
  }
}
```

### Get Flag Statistics

```
GET /flags/{flag_name}/stats?hours=24
```

**Response:**
```json
{
  "flag_name": "new_ui",
  "period_hours": 24,
  "total": 15240,
  "enabled": 7620,
  "disabled": 7620,
  "enabled_percent": 50.0,
  "variants": {
    "control": 7500,
    "variant_a": 7740
  }
}
```

---

## Examples

### Example 1: Gradual Rollout

```bash
# 1. Create flag (disabled)
curl -X POST http://localhost:8000/flags \
  -H "X-API-Key: prs_..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new_api_v2",
    "description": "New API v2 with performance improvements",
    "enabled": false,
    "rollout_percentage": 0
  }'

# 2. Enable for internal testing (specific users)
curl -X PATCH http://localhost:8000/flags/new_api_v2 \
  -H "X-API-Key: prs_..." \
  -d '{
    "enabled": true,
    "rollout_percentage": 0,
    "target_user_ids": ["usr_admin", "usr_qa"]
  }'
# Result: Only admins/QA can use new API

# 3. Roll out to 10% after internal testing passes
curl -X PATCH http://localhost:8000/flags/new_api_v2 \
  -H "X-API-Key: prs_..." \
  -d '{
    "rollout_percentage": 10,
    "target_user_ids": []  # Remove explicit targeting
  }'
# Result: 10% of all users see new API

# 4. Monitor metrics
curl http://localhost:8000/flags/new_api_v2/stats?hours=1 \
  -H "X-API-Key: prs_..."
# Check: error rate, latency, conversion

# 5. Increase to 50% if healthy
curl -X PATCH http://localhost:8000/flags/new_api_v2 \
  -H "X-API-Key: prs_..." \
  -d '{"rollout_percentage": 50}'

# 6. Finally roll out to 100%
curl -X PATCH http://localhost:8000/flags/new_api_v2 \
  -H "X-API-Key: prs_..." \
  -d '{"rollout_percentage": 100}'
```

### Example 2: A/B Testing

```bash
# 1. Create A/B test flag
curl -X POST http://localhost:8000/flags \
  -H "X-API-Key: prs_..." \
  -d '{
    "name": "checkout_ui_test",
    "description": "A/B test: new vs old checkout UI",
    "enabled": true,
    "rollout_percentage": 100,
    "variants": ["control", "variant_a"]
  }'

# 2. Client evaluates flag
curl -X POST http://localhost:8000/flags/checkout_ui_test/evaluate \
  -H "X-API-Key: prs_..." \
  -d '{"segments": ["premium"], "tier": "pro"}'

# Response:
# {
#   "enabled": true,
#   "variant": "control",  # or "variant_a"
#   "flag_name": "checkout_ui_test"
# }

# 3. Render appropriate UI based on variant
if response.variant == "control":
  # Render old checkout UI
else if response.variant == "variant_a":
  # Render new checkout UI

# 4. Track conversion metrics for each variant
# POST /track_conversion { flag: "checkout_ui_test", variant: "variant_a", conversion: true }

# 5. Get statistics after 1 week
curl http://localhost:8000/flags/checkout_ui_test/stats?hours=168 \
  -H "X-API-Key: prs_..."

# Analyze:
# - Variant A: 51% conversion
# - Control: 48% conversion
# - Conclusion: Variant A wins, roll out to 100%
```

### Example 3: Emergency Kill Switch

```bash
# Feature causing errors in production
# Disable instantly (no redeployment needed)

curl -X PATCH http://localhost:8000/flags/problematic_feature \
  -H "X-API-Key: prs_..." \
  -d '{"enabled": false}'

# Result: Feature instantly disabled for all users
# Server returns: enabled: false for all evaluations
# Application can gracefully degrade

# Later, after fix deployed:
curl -X PATCH http://localhost:8000/flags/problematic_feature \
  -H "X-API-Key: prs_..." \
  -d '{"enabled": true, "rollout_percentage": 50}'
```

---

## Best Practices

### 1. Naming Conventions

```
✅ Good names:
- new_checkout_ui
- payment_retry_logic_v2
- premium_analytics_dashboard
- bugfix_duplicate_charges

❌ Bad names:
- feature1
- new_thing
- experiment
- test123
```

### 2. Documentation

Always include descriptive `description` field:

```json
{
  "name": "advanced_analytics",
  "description": "New analytics dashboard with real-time metrics (jira-123)",
  "enabled": true,
  "rollout_percentage": 25
}
```

### 3. Expiration

Set `expires_at` for temporary flags:

```json
{
  "name": "black_friday_sale",
  "expires_at": "2024-11-30T23:59:59Z",
  "enabled": true,
  "rollout_percentage": 100
}
```

### 4. Gradual Rollout Sequence

```
Day 1: rollout_percentage: 1     (catch obvious bugs)
Day 2: rollout_percentage: 5     (monitor metrics)
Day 3: rollout_percentage: 25    (expand to larger group)
Day 4: rollout_percentage: 50    (half users)
Day 5: rollout_percentage: 100   (full rollout)
```

### 5. Monitoring Checkpoints

Before each rollout increase, check:
- ✅ Error rate (should be < 0.5%)
- ✅ Response latency (p95 < 500ms)
- ✅ Business metrics (conversions, engagement)
- ✅ Database query performance

### 6. Cleanup

After successful rollout, cleanup:
```bash
# Option 1: Delete flag (if fully rolled out)
DELETE /flags/old_feature

# Option 2: Keep for historical reference
# Set expires_at to past date, mark as deprecated
PATCH /flags/old_feature
{
  "expires_at": "2024-06-01T00:00:00Z",
  "description": "DEPRECATED: Rolled out 100% on 2024-06-15"
}
```

---

## Analytics & Metrics

### Evaluation Logs

All flag evaluations logged to `flag_evaluations` table:

```sql
SELECT 
  flag_id,
  variant,
  COUNT(*) as count,
  SUM(CASE WHEN enabled THEN 1 ELSE 0 END) as enabled_count
FROM flag_evaluations
WHERE evaluated_at >= NOW() - INTERVAL '24 hours'
GROUP BY flag_id, variant
ORDER BY count DESC;
```

**Sample result:**
```
flag_id      | variant    | count | enabled_count
───────────────────────────────────────────────────
ff_checkout  | control    | 5000  | 5000
ff_checkout  | variant_a  | 5100  | 5100
ff_new_api   | enabled    | 1200  | 1200
```

### Variant Performance

```sql
SELECT 
  flag_id,
  variant,
  COUNT(*) as evaluations,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY flag_id), 1) as percent
FROM flag_evaluations
WHERE evaluated_at >= NOW() - INTERVAL '7 days'
GROUP BY flag_id, variant;
```

---

## Troubleshooting

### Issue: Flag not enabling for expected users

```bash
# 1. Verify flag exists
curl http://localhost:8000/flags/my_flag \
  -H "X-API-Key: prs_..."

# 2. Check flag status
# enabled: true?
# expires_at: not in past?
# rollout_percentage > 0?

# 3. Test evaluation with specific context
curl -X POST http://localhost:8000/flags/my_flag/evaluate \
  -H "X-API-Key: prs_..." \
  -d '{"segments": ["test"], "tier": "pro"}'

# 4. Check database directly
psql $DATABASE_URL -c \
  "SELECT enabled, rollout_percentage, target_segments FROM feature_flags WHERE name = 'my_flag';"

# 5. Review evaluation logs
psql $DATABASE_URL -c \
  "SELECT * FROM flag_evaluations WHERE flag_id = 'ff_xxx' ORDER BY evaluated_at DESC LIMIT 5;"
```

### Issue: Performance impact from flag evaluations

```bash
# Flag evaluation is O(1) operation (hash + comparison)
# Logging evaluations is async in production

# If concerned about write throughput:
# 1. Batch evaluations: log every 100th evaluation
# 2. Use separate analytics database
# 3. Archive old logs: DELETE FROM flag_evaluations WHERE evaluated_at < NOW() - INTERVAL '90 days'
```

---

## References

- [Feature Flags Best Practices](https://martinfowler.com/articles/feature-toggles.html)
- [Canary Deployments](CANARY_DEPLOYMENTS.md)
- [API Documentation](API_DOCS.md)
