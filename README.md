# Authentication System from Scratch

Production-grade authentication system built from scratch in Python with FastAPI. No external auth services, no shortcuts.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env and set SESSION_SECRET_KEY to a random value

# Run the application
python -m app.main

# Or with uvicorn directly
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Authentication

**POST /auth/signup**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```
Response: `201 Created` with user object and session cookie

**POST /auth/login**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```
Response: `200 OK` with user object and session cookie

**POST /auth/logout**

Response: `200 OK` with confirmation message, clears session cookie

**GET /auth/me**

Response: `200 OK` with current user object (requires authentication)

### Protected Routes

**GET /protected**

Example protected route. Returns `401 Unauthorized` if not authenticated.

## Architecture

### Authentication Strategy: HTTP-only Session Cookies

This system uses **server-side sessions** with HTTP-only cookies rather than JWTs.

**Why sessions over JWT?**

1. **Immediate revocation**: Sessions can be invalidated server-side instantly. Critical for logout, password changes, or security incidents.
2. **Smaller cookie size**: Session ID is ~32 bytes vs JWT ~200+ bytes. Reduces bandwidth on every request.
3. **State control**: Server maintains auth state. No token replay after logout.
4. **Simplicity**: No signing/verification complexity, no key rotation concerns for this use case.

**Tradeoff**: Sessions require database lookup on every request. For high-traffic systems, cache sessions in Redis.

### Authentication Flow

```
┌─────────┐                ┌──────────┐                ┌──────────┐
│ Client  │                │   API    │                │ Database │
└────┬────┘                └────┬─────┘                └────┬─────┘
     │                          │                           │
     │  POST /auth/signup       │                           │
     ├─────────────────────────>│                           │
     │  {email, password}       │                           │
     │                          │  Hash password            │
     │                          ├──────────┐                │
     │                          │          │                │
     │                          │<─────────┘                │
     │                          │                           │
     │                          │  INSERT user              │
     │                          ├──────────────────────────>│
     │                          │                           │
     │                          │  User created             │
     │                          │<──────────────────────────┤
     │                          │                           │
     │                          │  Generate session_id      │
     │                          ├──────────┐                │
     │                          │          │                │
     │                          │<─────────┘                │
     │                          │                           │
     │                          │  INSERT session           │
     │                          ├──────────────────────────>│
     │                          │                           │
     │  201 Created             │                           │
     │  Set-Cookie: session_id  │                           │
     │<─────────────────────────┤                           │
     │                          │                           │
     │  GET /protected          │                           │
     │  Cookie: session_id      │                           │
     ├─────────────────────────>│                           │
     │                          │                           │
     │                          │  SELECT session, user     │
     │                          ├──────────────────────────>│
     │                          │                           │
     │                          │  User data                │
     │                          │<──────────────────────────┤
     │                          │                           │
     │  200 OK                  │                           │
     │  {protected_data}        │                           │
     │<─────────────────────────┤                           │
     │                          │                           │
     │  POST /auth/logout       │                           │
     │  Cookie: session_id      │                           │
     ├─────────────────────────>│                           │
     │                          │                           │
     │                          │  DELETE session           │
     │                          ├──────────────────────────>│
     │                          │                           │
     │  200 OK                  │                           │
     │  Clear Cookie            │                           │
     │<─────────────────────────┤                           │
     │                          │                           │
```

### Database Schema

**users**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email (email)
);
```

**sessions**
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    session_id VARCHAR(64) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_expires_at (expires_at),
    INDEX idx_session_lookup (session_id, expires_at)
);
```

## Security Decisions

### Password Storage

**Argon2id hashing**
- Winner of Password Hashing Competition (2015)
- Memory-hard algorithm: Resists GPU/ASIC attacks
- Automatic salt generation and parameter storage
- Better than bcrypt for new systems

**No pepper implementation**
- Simplifies key rotation
- Minimal benefit if database is compromised (attacker likely has entire system)
- Argon2's memory-hardness provides sufficient protection

### Session Management

**Session IDs**
- 32 bytes (256 bits) of cryptographically secure randomness
- Generated using `secrets.token_hex()` from Python stdlib
- Hex encoded: 64 characters in cookie

**Session lifetime**
- Default 24 hours (configurable)
- Balance between security and user experience
- Shorter for sensitive applications (banking: 15 minutes)
- Longer for low-risk applications (social media: 30 days)

**Session storage**
- Database backed for simplicity
- For high traffic: Use Redis with database fallback
- Composite index on (session_id, expires_at) for fast lookups

### Cookie Security

**HTTP-only flag**: `httponly=True`
- Prevents JavaScript access to cookie
- Protects against XSS attacks stealing session tokens
- Even if attacker injects script, cannot read session_id

**Secure flag**: `secure=True` (production only)
- Cookie only sent over HTTPS
- Prevents session theft via network sniffing
- Set to false in development for localhost testing

**SameSite attribute**: `samesite="lax"`
- Prevents CSRF attacks
- Allows cookie on normal navigation (GET)
- Blocks cookie on cross-site POST/PUT/DELETE
- "Strict" would be more secure but breaks legitimate flows

**Cookie contents**
- Only contains opaque session_id
- No user data, no claims, no metadata
- All sensitive data stays server-side

### Input Validation

**Email validation**
- RFC-compliant validation via `email-validator` library
- Normalized to lowercase to prevent duplicate accounts
- Maximum length enforced (255 chars)

**Password validation**
- Minimum 8 characters (NIST SP 800-63B)
- Maximum 128 characters (prevent DOS)
- No complexity requirements (modern best practice)
- Length > character variety for security

**Error messages**
- Generic "Invalid credentials" on login failure
- Prevents email enumeration attacks
- No timing differences (verify even if user not found)
- 409 Conflict on signup with existing email (acceptable leak)

## Tradeoffs

### Sessions vs JWTs

**Chose sessions because:**
- Immediate revocation critical for security
- Database lookup cost acceptable for most applications
- Simpler implementation and debugging
- Smaller cookie size

**When to use JWTs instead:**
- Microservices with distributed auth
- Mobile apps with offline functionality
- API gateways validating without database access
- Very high request volume where DB calls are bottleneck

### Database: SQLite vs Postgres

**Currently using SQLite for simplicity**

**Switch to Postgres for production:**
- Better concurrent write performance
- Connection pooling
- JSON column types for session metadata
- Stronger constraint enforcement
- Built-in full-text search for audit logs

### Password Requirements

**Only enforcing length minimum:**
- Length is most important factor
- Complexity rules lead to predictable patterns
- Users choose weak "complex" passwords: `Password1!`
- Modern guidance: Encourage passphrases

**Could add:**
- Have I Been Pwned API check
- Dictionary word detection
- Leaked password database check

### Session Storage Location

**Current: Database table**

**Alternatives:**
- **Redis**: Much faster, but requires separate service
- **In-memory**: Fast but doesn't survive restarts
- **Hybrid**: Redis with database fallback for persistence

**Production recommendation**: Use Redis for active sessions, database for audit trail.

## Extensions for Production

### Critical Additions

1. **Rate Limiting**
   - Prevent brute force attacks on `/auth/login`
   - Per-IP and per-email limits
   - Progressive delays after failed attempts

2. **Email Verification**
   - Send confirmation email on signup
   - Generate verification token with expiration
   - Activate account only after verification

3. **Password Reset**
   - Secure token-based flow
   - One-time use tokens
   - Short expiration (15-30 minutes)
   - Invalidate on password change

4. **Multi-Factor Authentication**
   - TOTP (Time-based One-Time Password)
   - SMS codes (less secure but better than nothing)
   - WebAuthn for hardware keys

5. **Account Security**
   - Temporary lockout after N failed attempts
   - Require re-authentication for sensitive actions
   - Password change invalidates all sessions
   - "Logout all devices" functionality

### Monitoring and Observability

1. **Audit Logging**
   - Log all authentication events
   - Include: timestamp, IP, user agent, outcome
   - Store in append-only table
   - Retention policy for compliance

2. **Metrics**
   - Login success/failure rates
   - Session duration distribution
   - Failed attempt patterns
   - API response times

3. **Alerting**
   - Spike in failed login attempts
   - Unusual geographic login patterns
   - Credential stuffing detection
   - Session fixation attempts

### Performance Optimizations

1. **Caching**
   - Cache user objects in Redis after session validation
   - Cache TTL matches session lifetime
   - Invalidate on password change or logout

2. **Database**
   - Connection pooling (SQLAlchemy handles this)
   - Read replicas for session validation
   - Partition sessions table by date
   - Background job to cleanup expired sessions

3. **API**
   - Compress responses
   - HTTP/2 or HTTP/3
   - CDN for static content
   - Async database queries

### Security Hardening

1. **Advanced Threat Detection**
   - Device fingerprinting
   - Behavioral analysis (login times, locations)
   - Velocity checks (too many accounts from same IP)
   - Known bot detection

2. **Compliance**
   - GDPR: Right to erasure, data export
   - SOC 2: Audit trails, access controls
   - PCI DSS: If handling payments
   - HIPAA: If handling health data

3. **Additional Validations**
   - Check passwords against breach databases
   - Detect credential stuffing patterns
   - Anomaly detection for account takeover
   - Require CAPTCHA after failed attempts

## Testing the API

### Using curl

**Signup**
```bash
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  -c cookies.txt
```

**Login**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}' \
  -c cookies.txt
```

**Access protected route**
```bash
curl http://localhost:8000/protected \
  -b cookies.txt
```

**Get current user**
```bash
curl http://localhost:8000/auth/me \
  -b cookies.txt
```

**Logout**
```bash
curl -X POST http://localhost:8000/auth/logout \
  -b cookies.txt \
  -c cookies.txt
```

### Using Python requests

```python
import requests

BASE_URL = "http://localhost:8000"
session = requests.Session()

# Signup
response = session.post(
    f"{BASE_URL}/auth/signup",
    json={"email": "test@example.com", "password": "password123"}
)
print(response.json())

# Access protected route
response = session.get(f"{BASE_URL}/protected")
print(response.json())

# Logout
response = session.post(f"{BASE_URL}/auth/logout")
print(response.json())
```

## Configuration

All configuration via environment variables (see `.env.example`):

- `SESSION_SECRET_KEY`: Cryptographically random key (generate with `secrets.token_urlsafe(32)`)
- `SESSION_EXPIRE_HOURS`: Session lifetime (default: 24)
- `DATABASE_URL`: SQLite or Postgres connection string
- `COOKIE_SECURE`: Set to `true` in production with HTTPS
- `ENVIRONMENT`: `development` or `production`

## Authour

Caleb Wodi
