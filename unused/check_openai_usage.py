#!/usr/bin/env python3
"""
Check OpenAI API usage and remaining credits
Run: python3 check_openai_usage.py
"""

from openai import OpenAI
from django.conf import settings
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webSchedule.settings')
django.setup()

client = OpenAI(api_key=settings.OPENAI_API_KEY)

print("\n" + "="*50)
print("OpenAI API Usage Check")
print("="*50 + "\n")

try:
    # Note: The OpenAI Python library doesn't have a direct method to check usage/billing
    # You need to use the web dashboard or make a simple test call to verify the key works
    
    print("🔑 API Key Status: Connected")
    print(f"🔐 Key (masked): ...{settings.OPENAI_API_KEY[-8:]}")
    
    # Make a minimal test call to verify the key works
    print("\n⏳ Testing API connection...")
    test_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=5
    )
    
    print("✅ API Connection: Working")
    print(f"\n📊 Last Test Call Usage:")
    print(f"   • Prompt tokens: {test_response.usage.prompt_tokens}")
    print(f"   • Completion tokens: {test_response.usage.completion_tokens}")
    print(f"   • Total tokens: {test_response.usage.total_tokens}")
    
    print("\n" + "-"*50)
    print("💡 To check detailed usage and billing:")
    print("   Visit: https://platform.openai.com/usage")
    print("   Or: https://platform.openai.com/account/billing/overview")
    print("-"*50 + "\n")
    
    # Estimated cost for gpt-4o-mini (approximate pricing)
    input_cost_per_1m = 0.150  # $0.150 per 1M input tokens
    output_cost_per_1m = 0.600  # $0.600 per 1M output tokens
    
    estimated_input_cost = (test_response.usage.prompt_tokens / 1_000_000) * input_cost_per_1m
    estimated_output_cost = (test_response.usage.completion_tokens / 1_000_000) * output_cost_per_1m
    estimated_total = estimated_input_cost + estimated_output_cost
    
    print(f"💰 Estimated cost for test call:")
    print(f"   • Input: ${estimated_input_cost:.6f}")
    print(f"   • Output: ${estimated_output_cost:.6f}")
    print(f"   • Total: ${estimated_total:.6f}")
    
    print("\n📝 Current Configuration:")
    print(f"   • Model: gpt-4o-mini")
    print(f"   • Max tokens per request: 300")
    print(f"   • Response word limit: 40 words")
    print(f"   • Smart context loading: Enabled")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("\n💡 Possible issues:")
    print("   • Invalid API key")
    print("   • No credits remaining")
    print("   • Network connection issue")

print("\n" + "="*50 + "\n")
