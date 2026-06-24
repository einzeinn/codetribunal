# Example Files

This directory contains sample code used for demonstrating CodeTribunal's multi-agent code review capabilities.

## vulnerable_auth.py

A deliberately insecure authentication module packed with common vulnerabilities:
- SQL injection (string interpolation in queries)
- Hardcoded secrets (DB password, API keys, JWT secret)
- Plaintext password storage
- MD5 hashing for admin credentials
- Unsafe pickle deserialization
- Command injection via `os.system()`
- XSS via unescaped HTML concatenation
- O(n²) algorithm for duplicate detection

**Purpose**: Use this file as a test case to showcase how CodeTribunal's agents identify, debate, and rule on security issues through adversarial multi-agent review.

### Try it:
```bash
curl -X POST http://your-backend-url/submit/ \
  -H "Content-Type: application/json" \
  -d @examples/vulnerable_auth.json
```

Or upload it through the frontend UI at `/file`.
