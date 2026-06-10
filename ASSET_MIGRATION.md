# Asset Access Migration Guide

## Overview

Persona images are now protected by authentication. This guide helps you migrate from public asset URLs to the authenticated endpoint.

## Changes

### Before: Public Access (DEPRECATED)
```bash
GET /assets/personas/{persona_id}.png
# No authentication required
# Anyone could enumerate and download all persona images
```

### After: Authenticated Access (REQUIRED)
```bash
GET /api/v1/personas/{persona_id}/image
# Requires: X-API-Key header
# Enforces: User must have purchased persona
# Returns: 403 Forbidden if not authorized
```

## Migration Steps

### 1. Update Image URLs in Client Code

**Old (public, no longer works for personas):**
```javascript
const imageUrl = `/assets/personas/${personaId}.png`;
const img = new Image();
img.src = imageUrl;  // ❌ Will return 404 or public assets only
```

**New (authenticated, secured):**
```javascript
const imageUrl = `/api/v1/personas/${personaId}/image`;
const headers = {
    'X-API-Key': userApiKey  // Include user's API key
};

// Fetch with authentication
fetch(imageUrl, { headers })
    .then(response => {
        if (!response.ok) {
            if (response.status === 403) {
                // User hasn't purchased this persona
                console.error('Not authorized to access this persona');
            } else if (response.status === 404) {
                // Image not available
                console.error('Image not found');
            }
            throw new Error(`HTTP ${response.status}`);
        }
        return response.blob();
    })
    .then(blob => {
        const img = document.createElement('img');
        img.src = URL.createObjectURL(blob);
        // use img...
    });
```

### 2. Server-Side Migration

**Node.js / JavaScript:**
```javascript
// Old way (deprecated)
// const url = `${baseUrl}/assets/personas/${personaId}.png`;

// New way (required)
const apiUrl = `${baseUrl}/api/v1/personas/${personaId}/image`;
const response = await fetch(apiUrl, {
    headers: {
        'X-API-Key': apiKey
    }
});

if (response.status === 403) {
    // Handle: user hasn't purchased
}
if (response.status === 404) {
    // Handle: image not available
}
const buffer = await response.buffer();
```

**Python:**
```python
import requests

# Old way (deprecated)
# url = f"{base_url}/assets/personas/{persona_id}.png"

# New way (required)
api_url = f"{base_url}/api/v1/personas/{persona_id}/image"
response = requests.get(
    api_url,
    headers={'X-API-Key': api_key}
)

if response.status_code == 403:
    # Handle: user hasn't purchased
    pass
elif response.status_code == 404:
    # Handle: image not available
    pass
elif response.status_code == 200:
    image_data = response.content
    # use image_data...
```

### 3. Fallback / Degradation

If image request fails, display fallback:
```javascript
const fallbackImageUrl = 'https://via.placeholder.com/200?text=Persona';

async function getPersonaImage(personaId, apiKey) {
    try {
        const response = await fetch(
            `/api/v1/personas/${personaId}/image`,
            { headers: { 'X-API-Key': apiKey } }
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return URL.createObjectURL(await response.blob());
    } catch (error) {
        console.warn(`Failed to load persona image: ${error}`);
        return fallbackImageUrl;  // Fallback to placeholder
    }
}
```

## Public Assets (Non-Persona)

The `/assets` directory continues to serve non-persona-specific assets:
- `/assets/styles/main.css` — Public CSS
- `/assets/js/app.js` — Public JavaScript
- `/assets/icons/...` — Public icons
- etc.

**Only persona-specific images require authentication.**

## Timeline

| Phase | Status | Persona Images Access |
|-------|--------|------------------------|
| Phase 1 | Current | `/api/v1/personas/{id}/image` (authenticated) |
| | | `/assets/personas/{id}.png` (deprecated, may be removed) |
| Phase 2 | Future | `/api/v1/personas/{id}/image` only |

## Troubleshooting

### 403 Forbidden
**Cause**: User API key is invalid or user hasn't purchased the persona.
**Solution**:
1. Verify API key is correct and not expired
2. Check user has purchased persona (via `/me/purchases` endpoint)
3. Verify persona_id is spelled correctly

### 404 Not Found
**Cause**: Persona ID doesn't exist or image hasn't been unpacked.
**Solution**:
1. Verify persona_id from `/api/v1/personas/` listing
2. Contact support if image is missing for existing persona

### Connection/Timeout
**Cause**: API server unreachable.
**Solution**:
1. Check BASE_URL is correct
2. Verify API server is running
3. Check firewall/network connectivity
4. Use fallback image while investigating

## Support

For questions or issues with the migration:
- Check `/api/v1/personas/` endpoint for available personas
- Review API documentation at `GET /api/v1/personas/{id}/image`
- Contact: support@example.com
