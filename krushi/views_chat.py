from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.shortcuts import render
import json
import os
try:
    import google.genai as genai
    _GENAI_PKG = 'google.genai'
except Exception:
    try:
        import google.generativeai as genai
        _GENAI_PKG = 'google.generativeai'
    except Exception:
        genai = None
        _GENAI_PKG = None
from .local_model import generate_local_response
import re
from typing import List
import string
from spellchecker import SpellChecker

# Initialize Gemini client if available
if getattr(settings, 'GOOGLE_API_KEY', None):
    try:
        if genai is not None and getattr(genai, 'configure', None):
            genai.configure(api_key=settings.GOOGLE_API_KEY)
        else:
            # Some installs require env var instead of SDK configure
            os.environ.setdefault('GOOGLE_API_KEY', settings.GOOGLE_API_KEY)
    except Exception as e:
        print(f"Error initializing Gemini ({_GENAI_PKG}): {e}")

def generate_chat_response(prompt):
    """Generate response by KrushiBot."""
    if not hasattr(settings, 'GOOGLE_API_KEY') or not settings.GOOGLE_API_KEY:
        return "Error: API key not configured. Please contact support."

    if genai is None:
        return "Error: GenAI client not available. Please install 'google-genai' or 'google-generativeai'."

    try:
        # Check if using the new google.genai V1 client
        if _GENAI_PKG == 'google.genai':
            client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            response = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=prompt
            )
            return getattr(response, 'text', '') or "(no response)"
        else:
            # Fallback to the old google.generativeai SDK
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            return getattr(response, 'text', '') or "(no response)"

    except Exception as e:
        return f"Error connecting to AI service: {str(e)}"


def _normalize_text(text: str) -> str:
    """Lowercase and strip extra whitespace/punctuation around words."""
    if not text:
        return ""
    text = text.strip().lower()
    # Replace punctuation with spaces except within numbers/percent like 20% npk
    table = str.maketrans({ch: " " for ch in string.punctuation})
    text = text.translate(table)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def _correct_spelling(text: str) -> str:
    """General spelling correction using pyspellchecker.
    Keeps short tokens and non-alpha tokens unchanged.
    """
    sp = SpellChecker()
    tokens = _normalize_text(text).split()
    corrected: List[str] = []
    for w in tokens:
        if len(w) <= 2 or not w.isalpha():
            corrected.append(w)
            continue
        suggestion = sp.correction(w)
        corrected.append(suggestion if suggestion else w)
    return " ".join(corrected)

def _shape_single_word_query(text: str) -> str:
    """If user entered a single word, expand into a short agri-specific query."""
    t = _normalize_text(text)
    tokens = t.split()
    if len(tokens) == 1:
        w = tokens[0]
        return (
            f"Briefly explain '{w}' in an agriculture context: key uses, cultivation tip, or common issue in 1-2 sentences."
        )
    return text



def generate_response_with_fallback(prompt: str, *, use_local: bool = False, temperature: float = 0.6, max_new_tokens: int = 128) -> str:
    """Decide between API vs local model and fallback to local on API failure.
    Priority:
    - If use_local=True or settings.USE_LOCAL_MODEL=True: use local model.
    - Else try API. If it fails and settings.FALLBACK_TO_LOCAL=True: use local model.
    """
    instruction = (
        "You are KrushiBot, an expert agriculture-focused assistant designed to help farmers, students, and agri-professionals. You must respond only to questions that are clearly related to agriculture, farming, crops, soil, irrigation, pests, fertilizers, weather impact on farming, agricultural technology, or livestock. If the user’s question is not related to agriculture, reply exactly with: ‘I'm sorry, KrushiBot can't assist with that.’ Always reply in the same language used by the user. Keep responses concise, limited to 2–3 short sentences, clear, practical, and descriptive. Do not use bullet points, numbering, emojis, markdown, or unnecessary explanations. Do not answer unrelated, fictional, or hypothetical questions outside agriculture." )
    pref_prompt = f"{instruction}\n\nUser: {prompt}"
    # Force local if requested globally or per-call
    if use_local or getattr(settings, 'USE_LOCAL_MODEL', False):
        return generate_local_response(pref_prompt, max_new_tokens=max_new_tokens, temperature=temperature)

    # If API key missing and fallback allowed, route to local directly
    if not getattr(settings, 'GOOGLE_API_KEY', None):
        if getattr(settings, 'FALLBACK_TO_LOCAL', True) or getattr(settings, 'USE_LOCAL_MODEL', False):
            try:
                return generate_local_response(pref_prompt, max_new_tokens=max_new_tokens, temperature=temperature)
            except Exception as local_err:
                return f"Error: API key missing and local model failed ({local_err})."
        return "Error: API key not configured. Please contact support."

    # Try API first
    try:
        return generate_chat_response(pref_prompt)
    except Exception as api_err:
        # Optional fallback to local
        if getattr(settings, 'FALLBACK_TO_LOCAL', True):
            try:
                return generate_local_response(pref_prompt, max_new_tokens=max_new_tokens, temperature=temperature)
            except Exception as local_err:
                return f"Error: API failed ({api_err}) and local model failed ({local_err})."
        return f"Error generating response via API: {str(api_err)}"

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def chat_api(request):
    """
    API endpoint for handling chat messages.
    Accepts POST requests with JSON body containing 'message' field.
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = JsonResponse({}, status=200)
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken'
        response['Access-Control-Max-Age'] = '86400'  # 24 hours
        return response
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            use_local = bool(data.get('use_local', False))
            temperature = float(data.get('temperature', 0.6))
            max_new_tokens = int(data.get('max_new_tokens', 128))
            
            if not user_message:
                resp = JsonResponse({'error': 'Empty message', 'success': False}, status=400)
                resp['Access-Control-Allow-Origin'] = '*'
                return resp
            
            # Spelling correction + single-word shaping
            corrected = _correct_spelling(user_message)
            shaped = _shape_single_word_query(corrected)

            # Generate response using API or local with fallback
            response_text = generate_response_with_fallback(
                shaped,
                use_local=use_local,
                temperature=temperature,
                max_new_tokens=max_new_tokens,
            )
            
            response = JsonResponse({
                'response': response_text,
                'success': True,
                'meta': {
                    'original': user_message,
                    'corrected': corrected
                }
            })
            response['Access-Control-Allow-Origin'] = '*'
            return response
            
        except json.JSONDecodeError:
            resp = JsonResponse({'error': 'Invalid JSON', 'success': False}, status=400)
            resp['Access-Control-Allow-Origin'] = '*'
            return resp
        except Exception as e:
            resp = JsonResponse({'error': str(e), 'success': False}, status=500)
            resp['Access-Control-Allow-Origin'] = '*'
            return resp
    
    resp = JsonResponse({'error': 'Method not allowed', 'success': False}, status=405)
    resp['Access-Control-Allow-Origin'] = '*'
    return resp
