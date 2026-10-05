"""Test different LLM models for DJ script engagement"""
import requests
import json
import time

ENDPOINT = "https://ai.tamandata.com/v1/chat/completions"
API_KEY = "9r_live_86yOfZYSP8amvms6--GqxB6AuCBQNgVg"

# Test models - creative/engaging ones
MODELS = [
    "cx/gpt-6.1-sol",          # Current
    "deepseek-v4-flash",       # Latest DeepSeek
    "gemini-3.8-flash",        # Latest Gemini
    "qwen-3.8-max",            # Qwen Max
    "step-3.7-flash",          # Step AI
    "deepseek-direct",         # DeepSeek direct
]

# Test prompt - typical DJ transition
PROMPT = """You are a radio DJ for Experiment FM 105.9. Write a 15-20 second transition between two Bollywood songs.

Current song: "Dil To Pagal Hai" by Lata Mangeshkar from *Dil To Pagal Hai*
Next song: "Tum Hi Ho" by Arijit Singh from *Aashiqui 2*

Requirements:
- Natural spoken language (not written essay)
- Song titles in quotes: "Title"
- Movie names in asterisks: *Movie*
- Keep it conversational and warm
- Be engaging and personal (not robotic)

Just the script, no stage directions:"""

print("=" * 80)
print("TESTING LLM MODELS FOR DJ SCRIPT ENGAGEMENT")
print("=" * 80)

results = {}

for model in MODELS:
    print(f"\n{'='*80}")
    print(f"MODEL: {model}")
    print(f"{'='*80}")
    
    try:
        start = time.time()
        
        response = requests.post(
            ENDPOINT,
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": PROMPT}],
                "max_tokens": 200,
                "temperature": 0.8,
                "stream": False
            },
            timeout=30
        )
        
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            script = data['choices'][0]['message']['content'].strip()
            
            # Strip <thinking> tags if present
            if '<thinking>' in script:
                parts = script.split('</thinking>')
                script = parts[-1].strip() if len(parts) > 1 else script
            
            results[model] = {
                'script': script,
                'time': elapsed,
                'success': True
            }
            
            print(f"⏱️  Response time: {elapsed:.1f}s")
            print(f"\n📻 SCRIPT:\n{script}\n")
            
        else:
            print(f"❌ Error {response.status_code}: {response.text[:200]}")
            results[model] = {'success': False, 'error': response.status_code}
    
    except Exception as e:
        print(f"❌ Exception: {e}")
        results[model] = {'success': False, 'error': str(e)}
    
    time.sleep(1)  # Rate limit courtesy

# Summary
print("\n" + "="*80)
print("SUMMARY - RANK BY ENGAGEMENT")
print("="*80)

successful = [(m, r) for m, r in results.items() if r.get('success')]

for i, (model, result) in enumerate(successful, 1):
    print(f"\n{i}. {model}")
    print(f"   Time: {result['time']:.1f}s")
    print(f"   Preview: {result['script'][:100]}...")

print("\n" + "="*80)
print("🎯 RECOMMENDATION: Read all scripts above and pick the most engaging one!")
print("    Then update .env with: LLM_MODEL=<model_name>")
print("="*80)
