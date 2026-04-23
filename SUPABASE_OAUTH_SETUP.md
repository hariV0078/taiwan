# Supabase OAuth Setup Guide

This app now uses **Supabase OAuth** for user authentication instead of email/password. Users can sign in with Google, GitHub, Microsoft, or other providers.

## 1) Enable OAuth in Supabase Console

### Step 1: Go to Supabase Dashboard
1. Open [https://app.supabase.com](https://app.supabase.com)
2. Select your project
3. Go to **Authentication** → **Providers**

### Step 2: Enable Google OAuth (recommended for hackathon)

1. Click **Google**
2. Toggle to **Enabled**
3. Enter your Google OAuth credentials:
   - **Client ID**: From Google Cloud Console
   - **Client Secret**: From Google Cloud Console
4. Click **Save**

#### Getting Google OAuth Credentials:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Go to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth 2.0 Client ID**
5. Choose **Web application**
6. Add authorized redirect URIs:
   - `https://yvpyazoizinxvdyegxlo.supabase.co/auth/v1/callback`
   - `http://localhost:3000/auth/callback` (for local testing)
7. Copy **Client ID** and **Client Secret** → paste into Supabase

### Step 3: (Optional) Enable GitHub OAuth

1. Click **GitHub** in Supabase Providers
2. Toggle to **Enabled**
3. Enter GitHub OAuth App credentials:
   - **Client ID**: From GitHub Developer Settings
   - **Client Secret**: From GitHub Developer Settings
4. Click **Save**

#### Getting GitHub OAuth Credentials:
1. Go to GitHub Settings → **Developer settings** → **OAuth Apps**
2. Click **New OAuth App**
3. Fill in:
   - **Application name**: CircularX
   - **Homepage URL**: `https://yvpyazoizinxvdyegxlo.supabase.co`
   - **Authorization callback URL**: `https://yvpyazoizinxvdyegxlo.supabase.co/auth/v1/callback`
4. Copy **Client ID** and **Client Secret** → paste into Supabase

## 2) Update Frontend OAuth Redirect URL

In your `.env` file (or frontend config):

```env
SUPABASE_URL=https://yvpyazoizinxvdyegxlo.supabase.co
SUPABASE_KEY=sb_publishable_heTk4-2361y4lAJnqpG36w_KDjcgsIm
FRONTEND_CALLBACK_URL=http://localhost:3000/auth/callback
```

## 3) Frontend OAuth Flow

The OAuth flow works like this:

```
1. User clicks "Sign in with Google"
   ↓
2. Frontend calls POST /auth/oauth/login with provider="google"
   ↓
3. Backend returns Supabase OAuth URL
   ↓
4. Frontend redirects to Supabase OAuth URL
   ↓
5. User signs in with Google (handled by Google)
   ↓
6. Supabase redirects back to frontend with session
   ↓
7. Frontend calls POST /auth/oauth/callback with OAuth tokens
   ↓
8. Backend creates/updates user and returns JWT token
   ↓
9. Frontend stores JWT token, uses it for all API requests
```

## 4) Backend API Usage

### Initiate OAuth Login

```bash
curl -X POST http://localhost:8000/auth/oauth/login \
  -H "Content-Type: application/json" \
  -d '{"provider": "google"}'
```

**Response:**
```json
{
  "url": "https://yvpyazoizinxvdyegxlo.supabase.co/auth/v1/authorize?..."
}
```

Redirect user to this URL.

### Handle OAuth Callback

After user signs in and Supabase redirects back, extract the OAuth session and call:

```bash
curl -X POST http://localhost:8000/auth/oauth/callback \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "user": {
      "id": "user-uuid",
      "email": "user@gmail.com",
      "user_metadata": {"name": "John Doe"}
    },
    "role": "manufacturer",
    "company": "Company Ltd",
    "country": "IN"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

Store this JWT token in localStorage and include it in all API requests:

```bash
Authorization: Bearer eyJhbGc...
```

## 5) Testing Locally

### Test Google Sign-in Locally

1. In Supabase → Authentication → Providers → Google, add redirect URI:
   ```
   http://localhost:3000/auth/callback
   ```

2. Run your backend:
   ```bash
   python main.py
   ```

3. Create a simple test frontend (Next.js example):
   ```jsx
   import { useEffect, useState } from 'react'
   
   export default function Login() {
     const [token, setToken] = useState(null)
     
     const handleGoogleLogin = async () => {
       // Get OAuth URL
       const res = await fetch('http://localhost:8000/auth/oauth/login', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ provider: 'google' })
       })
       const { url } = await res.json()
       
       // Redirect user
       window.location.href = url
     }
     
     useEffect(() => {
       // After redirect back, handle callback
       const handleCallback = async () => {
         // Get OAuth session from Supabase client
         const { data: { session } } = await supabase.auth.getSession()
         
         if (session) {
           const res = await fetch('http://localhost:8000/auth/oauth/callback', {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify({
               access_token: session.access_token,
               refresh_token: session.refresh_token,
               user: session.user,
               role: 'manufacturer',
               company: 'My Company',
               country: 'IN'
             })
           })
           const { access_token } = await res.json()
           setToken(access_token)
           localStorage.setItem('token', access_token)
         }
       }
       
       handleCallback()
     }, [])
     
     return (
       <button onClick={handleGoogleLogin}>
         Sign in with Google
       </button>
     )
   }
   ```

## 6) Supported Providers

Supabase supports OAuth with:
- Google
- GitHub
- Microsoft
- Discord
- Twitch
- GitLab
- Bitbucket
- Apple
- And more...

Enable any provider in Supabase → Authentication → Providers.

## 7) Troubleshooting

**Issue**: OAuth URL is empty
- **Solution**: Check that SUPABASE_URL and SUPABASE_KEY are set correctly in `.env`

**Issue**: "Invalid redirect URI"
- **Solution**: Make sure your callback URL is registered in Supabase AND in the OAuth provider (Google/GitHub)

**Issue**: User not created in database
- **Solution**: Make sure `role`, `company`, `country` are included in the OAuth callback request

**Issue**: JWT token is invalid
- **Solution**: Make sure you're using the token returned from `/auth/oauth/callback`, not the Supabase token

## 8) Security Notes

- Never expose `SUPABASE_KEY` (public key) in frontend — only use it in the browser
- Store the JWT token securely (httpOnly cookie recommended)
- Always validate JWT tokens on the backend (app already does this)
- User passwords are managed by OAuth provider, not your app

