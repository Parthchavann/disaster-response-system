# Disaster Response System API Documentation

## Overview

The Disaster Response System provides a comprehensive REST API for real-time disaster detection, classification, and response coordination. The API supports multimodal input processing (text, images, weather data, geospatial data) and real-time WebSocket connections for alerts.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.disaster-response.com`

## Authentication

The API uses JWT (JSON Web Token) based authentication with role-based access control.

### Authentication Endpoints

#### Login
```http
POST /auth/login
```

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "user_id": "string",
    "username": "string",
    "email": "string",
    "role": "string",
    "permissions": ["string"]
  }
}
```

#### Logout
```http
POST /auth/logout
Authorization: Bearer <token>
```

#### Refresh Token
```http
POST /auth/refresh
```

**Request Body:**
```json
{
  "refresh_token": "string"
}
```

### User Roles and Permissions

| Role | Permissions |
|------|-------------|
| `admin` | All permissions |
| `emergency_responder` | `read:events`, `predict:disasters`, `search:events`, `view:stats`, `create:alerts`, `update:events` |
| `analyst` | `read:events`, `search:events`, `view:stats`, `predict:disasters`, `export:data` |
| `public` | `read:public_events`, `view:public_stats` |

## Core Endpoints

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "ml_classifier": "healthy",
    "vector_store": "healthy",
    "redis": "healthy"
  }
}
```

### Disaster Prediction
```http
POST /predict
Authorization: Bearer <token>
Permission Required: predict:disasters
```

**Request Body:**
```json
{
  "text": "Flash flood warning downtown area evacuate immediately",
  "image_data": "base64_encoded_image_data",
  "weather_data": {
    "wind_speed": 75.0,
    "precipitation": 25.0,
    "temperature": 22.0,
    "pressure": 990.0,
    "humidity": 85.0
  },
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "source": "api",
  "metadata": {
    "user_id": "user123",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

**Response:**
```json
{
  "event_id": "uuid-string",
  "predictions": {
    "flood": 0.92,
    "fire": 0.03,
    "earthquake": 0.02,
    "hurricane": 0.01,
    "tornado": 0.01,
    "other_disaster": 0.01,
    "no_disaster": 0.00
  },
  "top_prediction": "flood",
  "confidence_score": 0.92,
  "severity": "high",
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "processing_time_ms": 245.6
}
```

### Event Search
```http
POST /search
Authorization: Bearer <token>
Permission Required: search:events
```

**Request Body:**
```json
{
  "query": "earthquake",
  "event_type": "earthquake",
  "severity": "high",
  "location": {
    "latitude": 37.7749,
    "longitude": -122.4194
  },
  "radius_km": 50.0,
  "limit": 10
}
```

**Response:**
```json
{
  "query": "earthquake",
  "total_results": 15,
  "results": [
    {
      "id": "event_123",
      "event_type": "earthquake",
      "severity": "high",
      "confidence": 0.88,
      "text": "Major earthquake detected magnitude 6.2",
      "location": {
        "latitude": 37.8,
        "longitude": -122.4
      },
      "timestamp": "2024-01-15T09:45:00Z",
      "score": 0.95,
      "distance_km": 5.2
    }
  ]
}
```

### Get Event by ID
```http
GET /events/{event_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "event_123",
  "event_type": "earthquake",
  "severity": "high",
  "confidence": 0.88,
  "text": "Major earthquake detected magnitude 6.2",
  "location": {
    "latitude": 37.8,
    "longitude": -122.4
  },
  "timestamp": "2024-01-15T09:45:00Z",
  "source": "social_media",
  "metadata": {
    "user": "emergency_user",
    "platform": "twitter"
  }
}
```

### System Statistics
```http
GET /stats
Authorization: Bearer <token>
Permission Required: view:stats
```

**Response:**
```json
{
  "system_status": "operational",
  "timestamp": "2024-01-15T10:30:00Z",
  "active_connections": 25,
  "active_subscriptions": 8,
  "total_events": 1542,
  "events_last_24h": 89,
  "disaster_type_distribution": {
    "flood": 45,
    "fire": 23,
    "earthquake": 12,
    "hurricane": 6,
    "tornado": 3
  },
  "average_confidence": 0.78,
  "redis": {
    "connected_clients": 12,
    "used_memory_human": "2.5MB"
  }
}
```

### Recent Events
```http
GET /recent-events?limit=20
Authorization: Bearer <token>
```

**Response:**
```json
{
  "total": 15,
  "events": [
    {
      "event_id": "uuid-1",
      "top_prediction": "flood",
      "confidence_score": 0.89,
      "severity": "high",
      "timestamp": "2024-01-15T10:25:00Z"
    }
  ]
}
```

## WebSocket API

### Real-time Alerts
```websocket
WS /ws/{client_id}
```

#### Subscribe to Alerts
Send message:
```json
{
  "type": "subscribe_alerts",
  "subscription": {
    "location": {
      "latitude": 40.7128,
      "longitude": -74.0060
    },
    "radius_km": 50.0,
    "severity_threshold": "medium",
    "event_types": ["flood", "fire", "earthquake"]
  }
}
```

Receive confirmation:
```json
{
  "type": "subscription_confirmed",
  "client_id": "client_123"
}
```

#### Receive Disaster Alerts
```json
{
  "type": "disaster_alert",
  "event": {
    "event_id": "uuid-123",
    "top_prediction": "flood",
    "confidence_score": 0.92,
    "severity": "high",
    "location": {
      "latitude": 40.7128,
      "longitude": -74.0060
    },
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "subscription_id": "client_123",
  "alert_reason": "Event meets criteria: flood with high severity"
}
```

#### Ping/Pong
Send ping:
```json
{
  "type": "ping"
}
```

Receive pong:
```json
{
  "type": "pong",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Data Models

### Disaster Event Request
```typescript
interface DisasterEventRequest {
  text?: string;                    // Text description
  image_data?: string;              // Base64 encoded image
  weather_data?: WeatherData;       // Weather information
  location?: Location;              // Geographic coordinates
  source: string;                   // Data source identifier
  metadata?: Record<string, any>;   // Additional metadata
}
```

### Weather Data
```typescript
interface WeatherData {
  wind_speed: number;      // Wind speed in mph
  precipitation: number;   // Precipitation in mm
  temperature: number;     // Temperature in Celsius
  pressure: number;        // Atmospheric pressure in hPa
  humidity: number;        // Humidity percentage
}
```

### Location
```typescript
interface Location {
  latitude: number;   // Latitude coordinate
  longitude: number;  // Longitude coordinate
}
```

### Alert Subscription
```typescript
interface AlertSubscription {
  location: Location;               // Center point for alerts
  radius_km: number;               // Alert radius in kilometers
  severity_threshold: string;      // Minimum severity: "low", "medium", "high", "critical"
  event_types?: string[];          // Filter by disaster types
}
```

## Error Responses

### Authentication Errors
```json
{
  "detail": "Invalid or expired token",
  "status_code": 401
}
```

### Permission Errors
```json
{
  "detail": "Insufficient permissions. Required: predict:disasters",
  "status_code": 403
}
```

### Validation Errors
```json
{
  "detail": "Invalid request format",
  "status_code": 400
}
```

### Server Errors
```json
{
  "detail": "Internal server error",
  "status_code": 500
}
```

## Rate Limiting

- **Default**: 1000 requests per minute per user
- **Burst**: 100 requests
- **WebSocket**: 50 connections per user

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1642239600
```

## SDKs and Examples

### Python Example
```python
import requests
import json

# Login
login_response = requests.post(
    "http://localhost:8000/auth/login",
    json={"username": "analyst1", "password": "analyst123"}
)
token = login_response.json()["access_token"]

# Predict disaster
headers = {"Authorization": f"Bearer {token}"}
prediction_data = {
    "text": "Flash flood emergency downtown",
    "location": {"latitude": 40.7128, "longitude": -74.0060}
}

response = requests.post(
    "http://localhost:8000/predict",
    headers=headers,
    json=prediction_data
)

print(response.json())
```

### JavaScript Example
```javascript
// Login
const loginResponse = await fetch('/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'analyst1',
    password: 'analyst123'
  })
});

const { access_token } = await loginResponse.json();

// WebSocket connection
const ws = new WebSocket(`ws://localhost:8000/ws/client_123`);

ws.onopen = () => {
  // Subscribe to alerts
  ws.send(JSON.stringify({
    type: 'subscribe_alerts',
    subscription: {
      location: { latitude: 40.7128, longitude: -74.0060 },
      radius_km: 50.0,
      severity_threshold: 'medium'
    }
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

## API Versioning

Current API version: `v1`

Future versions will be available at:
- `/v2/predict`
- `/v2/search`

Version headers:
```
API-Version: v1
Accept: application/json
```