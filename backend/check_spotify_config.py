#!/usr/bin/env python
"""
Quick diagnostic script to check Spotify OAuth configuration.
Run this to verify your Spotify app settings match your local configuration.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load environment variables
from decouple import config

print("=" * 70)
print("SPOTIFY OAUTH CONFIGURATION CHECKER")
print("=" * 70)
print()

# Check environment variables
print("📋 Environment Variables:")
print(f"  SPOTIFY_CLIENT_ID:     {config('SPOTIFY_CLIENT_ID')}")
print(f"  SPOTIFY_CLIENT_SECRET: {'*' * 20} (hidden)")
print(f"  SPOTIFY_REDIRECT_URI:  {config('SPOTIFY_REDIRECT_URI')}")
print(f"  OAUTHLIB_INSECURE:     {config('OAUTHLIB_INSECURE_TRANSPORT', 'Not Set')}")
print()

# Check system environment
print("🔧 System Environment:")
print(f"  OAUTHLIB_INSECURE_TRANSPORT: {os.environ.get('OAUTHLIB_INSECURE_TRANSPORT', 'NOT SET!')}")
print()

# Expected configuration
print("✅ Expected Spotify Developer Dashboard Settings:")
print()
print("  App Name: SongScope (or whatever you named it)")
print(f"  Client ID: {config('SPOTIFY_CLIENT_ID')}")
print()
print("  Redirect URIs (must include EXACTLY):")
print(f"    {config('SPOTIFY_REDIRECT_URI')}")
print()
print("  ⚠️  CRITICAL: The redirect URI MUST:")
print("     1. Match EXACTLY (including trailing slash)")
print("     2. Be added in Spotify Developer Dashboard")
print("     3. Use http:// for local development")
print()

# Instructions
print("=" * 70)
print("📝 NEXT STEPS:")
print("=" * 70)
print()
print("1. Go to: https://developer.spotify.com/dashboard")
print("2. Select your app (Client ID above)")
print("3. Click 'Settings' or 'Edit Settings'")
print("4. Under 'Redirect URIs', add:")
print(f"   {config('SPOTIFY_REDIRECT_URI')}")
print("5. Click 'Add' then 'Save'")
print("6. Wait 1-2 minutes for changes to propagate")
print("7. Restart your Django server")
print()

# Test OAuth flow
print("=" * 70)
print("🧪 TEST YOUR CONFIGURATION:")
print("=" * 70)
print()
print("After updating Spotify Dashboard, test with:")
print(f"  curl -I 'http://localhost:8000/spotify-login/'")
print()
print("Expected: 302 redirect to accounts.spotify.com")
print("If you get 400 error, the redirect URI is not properly configured.")
print()

# Check if server is running
import socket
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 8000))
    sock.close()
    if result == 0:
        print("✅ Django server is running on port 8000")
    else:
        print("❌ Django server is NOT running on port 8000")
        print("   Start it with: python manage.py runserver")
except Exception as e:
    print(f"⚠️  Could not check server status: {e}")

print()
print("=" * 70)
