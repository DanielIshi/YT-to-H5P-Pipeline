#!/usr/bin/env python3
"""Find YouTube URLs with subtitles"""
import os
import sys
from supabase import create_client

# Cloud Supabase (not self-hosted)
url = "https://lfwvxsgwmmfrlxcsxyds.supabase.co"
# Use anon key for read operations
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxmd3Z4c2d3bW1mcmx4Y3N4eWRzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjE0OTc5NDMsImV4cCI6MjAzNzA3Mzk0M30.TKAXBdwWBWKuUqJcZBIuJCb1xzxpNB_DF9ZW0PL5n5o"

client = create_client(url, key)
result = client.table("youtube_urls").select("id,title").not_.is_("subtitles", "null").limit(5).execute()

for row in result.data:
    title = row.get("title", "No title") or "No title"
    print(f"{row['id']}: {title[:60]}")
