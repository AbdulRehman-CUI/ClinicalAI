# ClinicalAI
## API Response Standards

Version: 1.0

---

# Purpose

Every API endpoint must return responses in a consistent format.

No endpoint may return raw SQLAlchemy models or inconsistent JSON.

---

# Success Response

```json
{
  "success": true,
  "message": "Patient created successfully.",
  "data": {}
}
```

---

# Error Response

```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": {
    "field": [
      "Error message"
    ]
  }
}
```

---

# Pagination

```json
{
  "success": true,
  "message": "",
  "data": [],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 100,
    "total_pages": 5
  }
}
```

---

# HTTP Status Codes

200 OK

201 Created

204 No Content

400 Bad Request

404 Not Found

409 Conflict

422 Validation Error

500 Internal Server Error

---

# Validation

All requests must be validated using Pydantic.

Validation failures must return HTTP 422.

---

# Logging

Errors must be logged internally.

Sensitive information must never be returned to the client.

---

# API Versioning

All endpoints use

/api/v1/

Future breaking changes require

/api/v2/

---

# File Upload

Accepted

PDF

PNG

JPEG

JPG

Maximum file size

20 MB

---

# AI Responses

AI responses returned by the backend must always include:

- findings
- confidence
- evidence
- missing_information
- suggested_next_steps

The backend must validate the AI response before returning it.