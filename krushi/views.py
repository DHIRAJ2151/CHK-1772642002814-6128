from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.db.models import Q
from django.core.paginator import Paginator
from django.conf import settings
import json
import os
import pickle
from threading import Lock
import numpy as np
import re
import base64
import requests
# Prefer the new package `google.genai`; fall back to the deprecated
# `google.generativeai` if the environment hasn't been updated yet.
try:
    import google.genai as genai
    _GENAI_PKG = 'google.genai'
except Exception:
    try:
        import google.generativeai as genai
        _GENAI_PKG = 'google.generativeai'  # deprecated
    except Exception:
        genai = None
        _GENAI_PKG = None
from typing import Any, Dict, Optional
from django.views.decorators.http import require_POST,require_GET
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import pandas as pd
# TEMPORARILY DISABLED REAL PAYMENT GATEWAY
# To re-enable Razorpay, uncomment the following import and the marked blocks below.
# import razorpay

from .models import User, Category, Product, Review, Feedback, Cart, CartItem, Order, OrderItem, NewsletterSubscription
from .forms import (
    CustomUserCreationForm,
    CustomAuthenticationForm,
    FeedbackForm,
    ReviewForm,
    ContactForm,
    SellProductForm,
    FertilizerListingForm,
    ForgotPasswordForm,
    VerifyOTPForm,
    ResetPasswordForm,
)
from .services.crop_planner import generate_crop_plan, get_available_crops
from .models import PasswordResetOTP

"""
Gemini initialization for multimodal (image+text) analysis
"""
# Configure GenAI client (prefer new package, fallback handled above)
try:
    if getattr(settings, 'GOOGLE_API_KEY', None):
        if genai is not None and getattr(genai, 'configure', None):
            genai.configure(api_key=settings.GOOGLE_API_KEY)
        else:
            # Some installations may require setting the env var instead
            os.environ.setdefault('GOOGLE_API_KEY', settings.GOOGLE_API_KEY)
    else:
        print("GOOGLE_API_KEY not configured; image analysis will fail.")
except Exception as e:
    print(f"Error configuring Google GenAI client ({_GENAI_PKG}): {e}")

# --- Crop recommendation model (pretrained pickle) ---
_crop_model = None
_crop_model_lock = Lock()

def _load_crop_model():
    global _crop_model
    if _crop_model is not None:
        return _crop_model
    with _crop_model_lock:
        if _crop_model is None:
            try:
                # Model path: Crop_Pridiction/crop_recommendation_model.pkl
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                model_path = os.path.join(base_dir, 'Crop_Pridiction', 'crop_recommendation_model.pkl')
                # In case the structure differs when running from project root
                if not os.path.exists(model_path):
                    project_root = os.path.dirname(base_dir)
                    alt_path = os.path.join(project_root, 'Crop_Pridiction', 'crop_recommendation_model.pkl')
                    if os.path.exists(alt_path):
                        model_path = alt_path
                with open(model_path, 'rb') as f:
                    _crop_model = pickle.load(f)
            except Exception as e:
                print(f"Crop model load failed: {e}")
                _crop_model = None
    return _crop_model

def _predict_crop(n: float, p: float, k: float, temperature: float, humidity: float, ph: float, rainfall: float):
    """Predict crop label using the pretrained model. Returns string or None."""
    model = _load_crop_model()
    if model is None:
        print("❌ Model is None in _predict_crop")
        return None
        
    try:
        # Log input values for debugging
        input_data = [float(n), float(p), float(k), float(temperature), float(humidity), float(ph), float(rainfall)]
        print(f"🔍 Model input values: {input_data}")
        
        # Create input array with feature names if available
        X = np.array([input_data], dtype=float)
        
        # Log model type and available methods
        print(f"🔍 Model type: {type(model).__name__}")
        if hasattr(model, 'predict'):
            print("✅ Model has predict method")
        
        # Make prediction
        try:
            # First try with feature names if model was trained with them
            if hasattr(model, 'feature_names_in_'):

                X_df = pd.DataFrame(X, columns=model.feature_names_in_)
                pred = model.predict(X_df)
            else:
                pred = model.predict(X)
                
            print(f"🔍 Raw prediction: {pred}")
            
            # Handle different prediction output formats
            if hasattr(pred, 'shape'):
                print(f"🔍 Prediction shape: {pred.shape}")
                
            if isinstance(pred, (np.ndarray, list)) and len(pred) > 0:
                label = pred[0] if not isinstance(pred[0], (np.ndarray, list)) else pred[0][0]
                print(f"✅ Prediction successful. Label: {label}, Type: {type(label)}")
                return str(label).strip()
                
            return str(pred).strip()
            
        except Exception as pred_error:
            print(f"⚠️ First prediction attempt failed: {pred_error}")
            # Fallback to simple prediction if feature names cause issues
            try:
                pred = model.predict(X)
                if isinstance(pred, (np.ndarray, list)) and len(pred) > 0:
                    label = pred[0] if not isinstance(pred[0], (np.ndarray, list)) else pred[0][0]
                    print(f"✅ Fallback prediction successful. Label: {label}")
                    return str(label).strip()
                return str(pred).strip()
            except Exception as fallback_error:
                print(f"❌ Fallback prediction also failed: {fallback_error}")
                raise fallback_error
        
    except Exception as e:
        import traceback
        print(f"❌ Crop prediction failed: {e}")
        print("Stack trace:")
        traceback.print_exc()
        return None

def _safe_json_from_text(text: str) -> Dict[str, Any]:
    """Try to parse JSON from model output, with fallback to extracting the first JSON block."""
    try:
        return json.loads(text)
    except Exception:
        pass
    # Extract first {...} block
    try:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return {
        "species": None,
        "health_status": "Unknown",
        "detected_diseases": [],
        "pests": [],
        "care_tips": [],
        "fertilizer_recommendations": []
    }

def _as_string_list(value) -> list[str]:
    """Normalize mixed lists (strings/objects) to a list of human-readable strings.

    This prevents frontend rendering issues like "[object Object]" by converting
    any objects into concise strings using common fields or key:value pairs.
    """
    out: list[str] = []
    if isinstance(value, list):
        for x in value:
            if isinstance(x, str):
                s = x.strip()
            elif isinstance(x, dict):
                # Prefer common text-bearing fields if present
                s = (
                    str(x.get('text') or x.get('recommendation') or x.get('note') or x.get('summary')
                        or x.get('description') or x.get('tip') or '').strip()
                )
                if not s:
                    # Fallback: join key:value pairs
                    parts = []
                    for k, v in x.items():
                        if v is None or v == '':
                            continue
                        parts.append(f"{k}: {v}")
                    s = ", ".join(parts).strip()
            else:
                s = str(x).strip()

            if s:
                out.append(s)
    elif isinstance(value, dict) or isinstance(value, str):
        out = _as_string_list([value])
    else:
        out = []
    return out

def _plantid_analyze_image(image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
    """Call Plant.id Health Assessment API and return a normalized structure.

    Expects settings.PLANT_ID_API_KEY and settings.PLANT_ID_BASE_URL.
    """
    api_key: Optional[str] = getattr(settings, 'PLANT_ID_API_KEY', None)
    base_url: str = getattr(settings, 'PLANT_ID_BASE_URL', 'https://plant.id/api/v3')
    if not api_key:
        return {"error": "PLANT_ID_API_KEY not configured."}

    # Request more detailed analysis; some deployments require query flags
    url = f"{base_url.rstrip('/')}/health_assessment?details=1&language=en"
    img_b64 = base64.b64encode(image_bytes).decode('utf-8')

    # Payload with explicit health analysis for diseases and pests
    payload = {
        "images": [img_b64],
        "health": {"analyze": True, "diseases": True, "pests": True},
        "modifiers": ["similar_images"],
        # Some accounts expect this block; harmless otherwise
        "classification": {"include": ["diseases"]}
    }

    headers = {
        "Content-Type": "application/json",
        "Api-Key": api_key,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=45)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return {"error": f"Plant.id request failed: {e}"}

    # Normalize into our schema
    species_name = None
    health_status = "unknown"
    detected_diseases = []
    pests = []

    try:
        # Extract species if available
        result = (data.get("result") or {})
        suggestions = result.get("classification", {}).get("suggestions", [])
        if suggestions:
            species_name = suggestions[0].get("name")

        # Health status
        health = result.get("is_healthy") or result.get("health", {}).get("is_healthy")
        if isinstance(health, bool):
            health_status = "Healthy" if health else "Diseased"

        # Diseases list
        diseases = result.get("diseases")
        if diseases is None:
            diseases = result.get("health", {}).get("diseases", [])
        for d in diseases:
            details = d.get("details") or d.get("disease_details") or {}
            # treatment may be list/str/dict -> normalize to list[str]
            treatment_raw = details.get("treatment")
            treatments: list[str] = []
            if isinstance(treatment_raw, list):
                treatments = [str(x) for x in treatment_raw]
            elif isinstance(treatment_raw, str):
                treatments = [treatment_raw]
            elif isinstance(treatment_raw, dict):
                # merge values arrays or strings
                for v in treatment_raw.values():
                    if isinstance(v, list):
                        treatments.extend([str(x) for x in v])
                    elif isinstance(v, str):
                        treatments.append(v)
            detected_diseases.append({
                "name": d.get("name"),
                "confidence": d.get("probability"),
                "description": details.get("description") or details.get("long_description"),
                "recommended_treatments": treatments
            })
        # Pests if present (not always provided)
        pests_list = result.get("pests") or result.get("health", {}).get("pests", [])
        for p in pests_list:
            p_details = p.get("details") or {}
            ctrl = p_details.get("treatment")
            ctrl_list: list[str] = []
            if isinstance(ctrl, list):
                ctrl_list = [str(x) for x in ctrl]
            elif isinstance(ctrl, str):
                ctrl_list = [ctrl]
            elif isinstance(ctrl, dict):
                for v in ctrl.values():
                    if isinstance(v, list):
                        ctrl_list.extend([str(x) for x in v])
                    elif isinstance(v, str):
                        ctrl_list.append(v)
            pests.append({
                "name": p.get("name"),
                "confidence": p.get("probability"),
                "control": ctrl_list
            })
    except Exception as e:
        # Light debug print to help during integration/testing only
        print(f"Plant.id normalization warning: {e}")

    return {
        "species": species_name,
        "health_status": health_status,
        "detected_diseases": detected_diseases,
        "pests": pests,
        "care_tips": [],
        "fertilizer_recommendations": []
    }

def _gemini_analyze_image(image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
    """Call Gemini to analyze plant image and return structured JSON."""
    if not getattr(settings, 'GOOGLE_API_KEY', None):
        return {"error": "GOOGLE_API_KEY not configured."}

    prompt = (
        "You are an expert agronomy assistant. Analyze the plant/crop image and return STRICT JSON only with keys: "
        "species (string), health_status (string among ['Healthy','Stressed','Diseased','Unknown']), "
        "detected_diseases (array of objects with name, confidence (0-1), description, recommended_treatments (array)), "
        "pests (array of objects with name, confidence (0-1), control (array)), "
        "care_tips (array of strings), "
        "fertilizer_recommendations (array of strings specific to species and condition). "
        "Output JSON only, no prose."
    )

    # Use a vision-capable model and request JSON directly
    # Use a vision-capable model and request JSON directly
    try:
        # Check if using the new google.genai V1 client
        if _GENAI_PKG == 'google.genai':
            client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            
            # The new SDK takes Part objects for non-text data
            from google.genai import types
            
            resp = client.models.generate_content(
                model='gemini-2.5-flash', 
                contents=[
                    types.Part.from_text(text=prompt),
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                ],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json"
                )
            )
        else:
            # Fallback to the old google.generativeai SDK
            model = genai.GenerativeModel('gemini-2.5-flash')
            resp = model.generate_content(
                [
                    prompt,
                    {"mime_type": mime_type, "data": image_bytes},
                ],
                generation_config={
                    "temperature": 0.2,
                    "response_mime_type": "application/json"
                }
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Gemini API Error: {str(e)}"}

    # Extract JSON from response
    try:
        if _GENAI_PKG == 'google.genai':
            # google.genai 0.3+ exposes .parsed if JSON schema was requested? 
            # Or just .text which we parse manually.
            text = resp.text
        else:
            # google.generativeai (legacy)
            text = resp.text
    except Exception:
        text = ""

    return _safe_json_from_text(text)

def home(request):
    """Home page view"""
    # Get featured products
    featured_products = Product.objects.filter(is_active=True).order_by('-rating')[:4]
    
    # Get categories
    categories = Category.objects.all()[:6]
    
    context = {
        'featured_products': featured_products,
        'categories': categories,
    }
    return render(request, 'index.html', context)

def shop(request):
    """Shop page view with products from database"""
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    category_filter = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'newest')
    
    # Base queryset
    products = Product.objects.filter(is_active=True)
    
    # Apply search filter
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Apply category filter
    if category_filter and category_filter != 'all':
        products = products.filter(category__name=category_filter)
    
    # Apply sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'rating':
        products = products.order_by('-rating')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:  # newest
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all categories for filter
    categories = Category.objects.all()
    
    context = {
        'products': page_obj,
        'categories': categories,
        'search_query': search_query,
        'category_filter': category_filter,
        'sort_by': sort_by,
    }
    return render(request, 'shop.html', context)


@login_required
def sell_product(request):
    """Allow authenticated users to list a product for sale."""
    if request.method == 'POST':
        form = SellProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            # User-submitted products require admin approval
            product.is_approved = False
            product.save()
            messages.success(request, 'Product listed successfully and is pending approval.')
            return redirect('my_products')
    else:
        form = SellProductForm()
    return render(request, 'sell_product.html', {'form': form})


@login_required
def my_products(request):
    products = Product.objects.filter(seller=request.user).order_by('-created_at')
    total_count = products.count()
    active_count = products.filter(is_active=True).count()
    context = {'products': products, 'total_count': total_count, 'active_count': active_count}
    return render(request, 'my_products.html', context)


@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    if request.method == 'POST':
        form = SellProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('my_products')
    else:
        form = SellProductForm(instance=product)
    return render(request, 'edit_product.html', {'form': form, 'product': product})


@login_required
def delete_product(request, product_id):
    try:
        product = Product.objects.get(id=product_id, seller=request.user)
    except Product.DoesNotExist:
        messages.error(request, 'Product not found.')
        return redirect('my_products')

    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully.')
        return redirect('my_products')

    # If not POST, just redirect back
    return redirect('my_products')


@login_required
def create_fertilizer_listing(request):
    if request.method == 'POST':
        form = FertilizerListingForm(request.POST)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user
            listing.save()
            messages.success(request, 'Fertilizer listing created successfully.')
            return redirect('shop')
    else:
        form = FertilizerListingForm()
    return render(request, 'sell_fertilizer.html', {'form': form})


@login_required
def user_profile(request):
    return render(request, 'user_profile.html')


def forgot_password(request):
    if request.method == 'POST':
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, 'No account found for that email.')
                return redirect('forgot_password')

            # Create OTP record
            import random
            otp = ''.join(random.choices('0123456789', k=6))
            expires_at = None
            try:
                from django.utils import timezone
                expires_at = timezone.now() + timezone.timedelta(minutes=10)
            except Exception:
                expires_at = None

            PasswordResetOTP.objects.create(user=user, otp=otp, expires_at=expires_at)
            # Note: Email sending is intentionally omitted here; assume background task or dev prints
            messages.success(request, 'OTP sent to your registered email (development mode).')
            request.session['reset_email'] = email
            return redirect('verify_otp')
    else:
        form = ForgotPasswordForm()
    return render(request, 'forgot_password.html', {'form': form})


def verify_otp(request):
    if request.method == 'POST':
        form = VerifyOTPForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            email = request.session.get('reset_email')
            try:
                user = User.objects.get(email=email)
            except Exception:
                messages.error(request, 'Session expired. Please try again.')
                return redirect('forgot_password')

            try:
                record = PasswordResetOTP.objects.filter(user=user, otp=otp, is_used=False).order_by('-created_at').first()
                if record and record.is_valid():
                    record.is_used = True
                    record.save()
                    request.session['reset_user_id'] = user.id
                    return redirect('reset_password')
                else:
                    messages.error(request, 'Invalid or expired OTP.')
            except Exception:
                messages.error(request, 'Invalid OTP.')
    else:
        form = VerifyOTPForm()
    return render(request, 'verify_otp.html', {'form': form})


def reset_password(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Session expired. Please request a new OTP.')
        return redirect('forgot_password')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('forgot_password')

    if request.method == 'POST':
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user.set_password(new_password)
            user.save()
            # Cleanup session
            request.session.pop('reset_user_id', None)
            request.session.pop('reset_email', None)
            messages.success(request, 'Password reset successfully. You can now log in.')
            return redirect('login')
    else:
        form = ResetPasswordForm()
    return render(request, 'reset_password.html', {'form': form})


def resend_otp(request):
    email = request.POST.get('email') or request.session.get('reset_email')
    if not email:
        return JsonResponse({'success': False, 'message': 'Email not provided'}, status=400)
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'No account for this email'}, status=400)

    import random
    otp = ''.join(random.choices('0123456789', k=6))
    from django.utils import timezone
    expires_at = timezone.now() + timezone.timedelta(minutes=10)
    PasswordResetOTP.objects.create(user=user, otp=otp, expires_at=expires_at)
    # Not sending email here; return success for dev
    return JsonResponse({'success': True, 'message': 'OTP resent (development mode)'} )


@require_POST
def generate_crop_plan_api(request):
    try:
        data = json.loads(request.body.decode('utf-8') or '{}')
        lat = float(data.get('latitude') or data.get('lat'))
        lon = float(data.get('longitude') or data.get('lon'))
        crop = str(data.get('crop_name') or data.get('crop') or '')
    except Exception:
        return JsonResponse({'error': 'Invalid request payload'}, status=400)

    result = generate_crop_plan(lat, lon, crop)
    return JsonResponse(result)


def get_available_crops_api(request):
    crops = get_available_crops()
    return JsonResponse({'crops': crops})


def crop_planning_page(request):
    crops = get_available_crops()
    return render(request, 'crop_planning.html', {'available_crops': crops})

def disease(request):
    """Disease detection page"""
    return render(request, 'disease.html')

def soil(request):
    """Legacy Soil URL that redirects to the new dedicated page."""
    return render(request, 'soil.html')

@ensure_csrf_cookie
def soil_analysis(request):
    """Dedicated Soil Analysis & Recommendations page"""
    return render(request, 'soil_analysis.html')

@require_POST
def ocr_extract_soil_pdf(request):
    """Extract N, P, K, Temperature, Humidity, Rainfall from an uploaded PDF via OCR.space.

    Expects multipart/form-data with field 'file' (PDF). Returns JSON with keys:
    { n, p, k, temperature, humidity, rainfall, error? }
    """
    try:
        uploaded = request.FILES.get('file')
        if not uploaded:
            return JsonResponse({'error': 'No file uploaded.'}, status=400)
        if not str(uploaded.content_type).lower().endswith('pdf') and uploaded.name.lower().endswith('.pdf') is False:
            # Allow even if content_type missing; rely on extension
            return JsonResponse({'error': 'Please upload a PDF file.'}, status=400)

        api_key = getattr(settings, 'OCR_SPACE_API_KEY', '')
        if not api_key:
            return JsonResponse({'error': 'OCR API key is not configured on the server.'}, status=500)

        # Call OCR.space
        url = 'https://api.ocr.space/parse/image'
        files = {
            'file': (uploaded.name, uploaded.read(), uploaded.content_type or 'application/pdf')
        }
        data = {
            'apikey': api_key,
            'language': 'eng',
            # 'isOverlayRequired': False
        }

        try:
            resp = requests.post(url, files=files, data=data, timeout=60)
            resp.raise_for_status()
            ocr_json = resp.json()
        except Exception as e:
            return JsonResponse({'error': f'OCR request failed: {e}'}, status=502)

        # Validate OCR response
        parsed_text = ''
        try:
            if ocr_json.get('IsErroredOnProcessing'):
                msg = ocr_json.get('ErrorMessage') or ocr_json.get('ErrorDetails') or 'OCR processing error.'
                if isinstance(msg, list):
                    msg = "; ".join([str(x) for x in msg])
                return JsonResponse({'error': str(msg)}, status=502)
            results = ocr_json.get('ParsedResults') or []
            if results:
                parsed_text = results[0].get('ParsedText') or ''
        except Exception:
            parsed_text = ''

        # Normalize text for regex
        text = parsed_text.replace('\r', ' ').replace('\t', ' ')
        # Lower copy for label matching while capturing numbers from original too
        lower = text.lower()

        # Helper to search patterns and return first captured number as float string
        def find_number(patterns):
            for pat in patterns:
                m = re.search(pat, text, flags=re.IGNORECASE | re.MULTILINE)
                if m:
                    val = m.group(1)
                    # Remove commas and stray characters
                    val = val.replace(',', ' ').strip()
                    # Pick the first number in the capture
                    num_m = re.search(r"-?\d+(?:\.\d+)?", val)
                    if num_m:
                        return num_m.group(0)
            return None

        # Patterns for N, P, K (ppm values typically). Accept labels Nitrogen/N, Phosphorus/P, Potassium/K
        n_patterns = [
            r"(?:\bN\b|Nitrogen)\s*[:=\-]?\s*([\d.,]+)\s*(?:ppm|mg/?kg)?",
            r"Nitrogen\s*\(N\)\s*[:=\-]?\s*([\d.,]+)"
        ]
        p_patterns = [
            r"(?:\bP\b|Phosphorus)\s*[:=\-]?\s*([\d.,]+)\s*(?:ppm|mg/?kg)?",
            r"Phosphorus\s*\(P\)\s*[:=\-]?\s*([\d.,]+)"
        ]
        k_patterns = [
            r"(?:\bK\b|Potassium)\s*[:=\-]?\s*([\d.,]+)\s*(?:ppm|mg/?kg)?",
            r"Potassium\s*\(K\)\s*[:=\-]?\s*([\d.,]+)"
        ]

        # pH: values between 0-14 typically, labels like pH / pH Level
        ph_patterns = [
            r"\bpH\s*(?:Level)?\s*[:=\-]?\s*([\d.,]+)\b",
            r"\bPH\s*(?:Level)?\s*[:=\-]?\s*([\d.,]+)\b",
        ]

        # Temperature: may include °C or C; OCR may misread '°' as 'o'
        t_patterns = [
            r"(?:Soil\s*Temperature|Temp(?:erature)?)\s*[:=\-]?\s*([\-\d.,]+)\s*[°o]?\s*C\b",
            r"\b([\-\d]{1,3}(?:\.\d+)?)\s*[°o]?\s*C\b"
        ]

        # Humidity: often percentage
        h_patterns = [
            r"(?:Humidity|RH)\s*[:=\-]?\s*([\d.,]+)\s*%",
            r"\b([\d]{1,3}(?:\.\d+)?)\s*%\b"
        ]

        # Rainfall: mm or cm
        r_patterns = [
            r"(?:Rainfall|Rain)\s*[:=\-]?\s*([\d.,]+)\s*(?:mm|cm)\b",
            r"\b([\d]{1,5}(?:\.\d+)?)\s*(?:mm|cm)\b"
        ]

        n_val = find_number(n_patterns)
        p_val = find_number(p_patterns)
        k_val = find_number(k_patterns)
        ph_val = find_number(ph_patterns)
        t_val = find_number(t_patterns)
        # Heuristic correction: OCR sometimes reads '28°C' as '280 C' (° -> 0)
        # Convert to float first, then correct unrealistic values.
        if t_val is not None:
            try:
                t_num = float(str(t_val).strip())
                # If value is implausibly high but dividing by 10 makes it plausible, fix it.
                # Examples: 280 -> 28.0, 300 -> 30.0, 185 -> 18.5
                if t_num > 60:
                    # If divisible by 10 exactly and within range after division
                    if (t_num % 10 == 0) and (t_num / 10.0) <= 60:
                        t_num = t_num / 10.0
                    # Handle cases like 185 -> 18.5 (common OCR decimal drop)
                    elif (t_num / 10.0) <= 60 and (t_num / 10.0) >= -10:
                        # Prefer division by 10 if it yields a plausible Celsius
                        t_num = t_num / 10.0
                # Clamp to reasonable soil temp range if still out-of-range
                if t_num < -10:
                    t_num = -10.0
                elif t_num > 60:
                    t_num = 60.0
                t_val = t_num
            except Exception:
                # leave as-is (string) if conversion fails
                pass
        h_val = find_number(h_patterns)
        r_val = find_number(r_patterns)

        return JsonResponse({
            'n': n_val,
            'p': p_val,
            'k': k_val,
            'ph': ph_val,
            'temperature': t_val,
            'humidity': h_val,
            'rainfall': r_val,
            'raw_text_preview': (text[:500] if text else '')
        })
    except Exception as e:
        return JsonResponse({'error': f'Unexpected server error: {str(e)}'}, status=500)

def about(request):
    """About us page"""
    return render(request, 'about.html')

def contact(request):
    """Contact page"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_msg = form.save(commit=False)
            if request.user.is_authenticated:
                contact_msg.user = request.user
            contact_msg.save()
            messages.success(request, 'Your message has been sent successfully!   ')
            return redirect('contact')
    else:
        form = ContactForm()
    
    context = {'form': form}
    return render(request, 'contact.html', context)

def rating(request):
    """Rating/feedback page"""
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            if request.user.is_authenticated:
                feedback.user = request.user
            feedback.save()
            messages.success(request, 'Thank you for your feedback!   ')
            return redirect('rating')
    else:
        form = FeedbackForm()
    
    # Get recent feedback
    recent_feedback = Feedback.objects.filter(is_active=True).order_by('-created_at')[:6]
    
    context = {
        'form': form,
        'recent_feedback': recent_feedback,
    }
    return render(request, 'rating.html', context)
def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Try to authenticate with username
            user = authenticate(username=username, password=password)
            if user is None:
                # Try to authenticate with email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                # Optional: Add an error message if login fails entirely
                messages.error(request, "Invalid username or password.  ")
    else:
        form = CustomAuthenticationForm()
    
    context = {'form': form}
    return render(request, 'login.html', context)

def register(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            if username and User.objects.filter(username=username).exists():
                form.add_error('username', 'This username is already taken. Please choose another one.')
            else:
                try:
                    user = form.save()
                except Exception as e:
                    # Handle race-condition duplicates or other DB constraint errors gracefully
                    if 'username' in str(e).lower() and 'unique' in str(e).lower():
                        form.add_error('username', 'This username is already taken. Please choose another one.')
                    else:
                        form.add_error(None, 'Unable to create account right now. Please try again.')
                else:
                    # FIX IS HERE: Explicitly specify the backend
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    
                    messages.success(request, 'Account created successfully!   ')
                    return redirect('home')
    else:
        form = CustomUserCreationForm()
    
    context = {'form': form}
    return render(request, 'register.html', context)
    
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully!   ')
    return redirect('home')

@login_required
def add_to_cart(request, product_id):
    """Add product to cart"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id, is_active=True)
        quantity = int(request.POST.get('quantity', 1))
        
        # Get or create cart for user
        cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Check if product already in cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        messages.success(request, f'{product.name} added to cart!')
        return JsonResponse({'success': True, 'message': 'Product added to cart!'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def view_cart(request):
    """View shopping cart"""
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all()
    except Cart.DoesNotExist:
        cart = None
        cart_items = []
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
    }
    return render(request, 'cart.html', context)

@login_required
def update_cart(request, item_id):
    """Update cart item quantity"""
    if request.method == 'POST':
        try:
            cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
            quantity = int(request.POST.get('quantity', 1))
            
            if quantity > 0:
                cart_item.quantity = quantity
                cart_item.save()
            else:
                cart_item.delete()
            
            return JsonResponse({'success': True})
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Item not found'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    try:
        cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
        cart_item.delete()
        messages.success(request, 'Item removed from cart!  ')
    except CartItem.DoesNotExist:
        messages.error(request, 'Item not found!  ')
    
    return redirect('view_cart')

@login_required
def checkout(request):
    """Checkout process with Razorpay payment initialization via AJAX.

    GET: Render checkout page.
    POST (AJAX): TEMP MODE creates order directly (payment bypass).
    """
    try:
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all()

        if not cart_items.exists():
            messages.warning(request, 'Your cart is empty!   ')
            return redirect('shop')

        if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
            shipping_address = request.POST.get('shipping_address', '').strip()
            phone = request.POST.get('phone', '').strip()
            notes = request.POST.get('notes', '').strip()

            if not shipping_address or not phone:
                return JsonResponse({'success': False, 'message': 'Shipping address and phone are required.'}, status=400)

            # REAL PAYMENT MODE (Razorpay): Uncomment this block and comment out the TEMP PAYMENT block below
            # ------------------------------------------------------------------------------------------------
            # key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
            # key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
            # if not key_id or not key_secret:
            #     return JsonResponse({'success': False, 'message': 'Payment gateway not configured.'}, status=500)
            # try:
            #     client = razorpay.Client(auth=(key_id, key_secret))
            #     amount_paise = int(round(float(cart.total_amount) * 100))
            #     if amount_paise <= 0:
            #         return JsonResponse({'success': False, 'message': 'Cart total must be greater than 0.'}, status=400)
            #     order_data = {
            #         'amount': amount_paise,
            #         'currency': 'INR',
            #         'payment_capture': 1,
            #     }
            #     rp_order = client.order.create(order_data)
            # except Exception as e:
            #     return JsonResponse({'success': False, 'message': f'Razorpay init failed: {str(e)}'}, status=500)
            # request.session['checkout'] = {
            #     'shipping_address': shipping_address,
            #     'phone': phone,
            #     'notes': notes,
            #     'razorpay_order_id': rp_order.get('id'),
            #     'amount_paise': amount_paise,
            # }
            # request.session.modified = True
            # return JsonResponse({
            #     'success': True,
            #     'razorpay_order_id': rp_order.get('id'),
            #     'amount': amount_paise,
            #     'currency': 'INR',
            #     'key_id': key_id,
            #     'user': {
            #         'name': request.user.get_full_name() or request.user.username,
            #         'email': request.user.email,
            #         'contact': phone,
            #     }
            # })

            # TEMP PAYMENT MODE: Directly create order without gateway
            try:
                if cart.total_amount <= 0:
                    return JsonResponse({'success': False, 'message': 'Cart total must be greater than 0.'}, status=400)

                order = Order.objects.create(
                    user=request.user,
                    total_amount=cart.total_amount,
                    shipping_address=shipping_address,
                    phone=phone,
                    notes=notes,
                    status='confirmed',
                )
                for cart_item in cart_items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.price,
                    )

                cart.delete()
                # Ensure any previous checkout session info is cleared
                if 'checkout' in request.session:
                    del request.session['checkout']
                    request.session.modified = True

                return JsonResponse({'success': True, 'order_id': order.id})
            except Exception as e:
                return JsonResponse({'success': False, 'message': str(e)}, status=500)

        context = {
            'cart': cart,
            'cart_items': cart_items,
            # 'razorpay_key_id': getattr(settings, 'RAZORPAY_KEY_ID', ''),  # REAL PAYMENT: uncomment when re-enabling Razorpay
        }
        return render(request, 'checkout.html', context)

    except Cart.DoesNotExist:
        messages.warning(request, 'Your cart is empty!')
        return redirect('shop')

@login_required
@require_POST
def payment_verify(request):
    """TEMP MODE: Payment verification disabled."""
    return JsonResponse({'success': False, 'message': 'Payment verification is disabled in temporary payment mode.'}, status=400)
    
    # REAL PAYMENT: Uncomment this block to re-enable Razorpay verification
    # ---------------------------------------------------------------
    # key_id = getattr(settings, 'RAZORPAY_KEY_ID', '')
    # key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')
    # if not key_id or not key_secret:
    #     return JsonResponse({'success': False, 'message': 'Payment gateway not configured.'}, status=500)
    #
    # rp_order_id = request.POST.get('razorpay_order_id')
    # rp_payment_id = request.POST.get('razorpay_payment_id')
    # rp_signature = request.POST.get('razorpay_signature')
    #
    # if not (rp_order_id and rp_payment_id and rp_signature):
    #         return JsonResponse({'success': False, 'message': 'Missing payment parameters.'}, status=400)
    #
    # try:
    #     client = razorpay.Client(auth=(key_id, key_secret))
    #     params_dict = {
    #         'razorpay_order_id': rp_order_id,
    #         'razorpay_payment_id': rp_payment_id,
    #         'razorpay_signature': rp_signature,
    #     }
    #     client.utility.verify_payment_signature(params_dict)
    #
    #     checkout_info = request.session.get('checkout') or {}
    #     if checkout_info.get('razorpay_order_id') != rp_order_id:
    #         return JsonResponse({'success': False, 'message': 'Session expired or mismatched order.'}, status=400)
    #
    #     cart = Cart.objects.get(user=request.user)
    #     cart_items = cart.items.all()
    #     if not cart_items.exists():
    #         return JsonResponse({'success': False, 'message': 'Cart is empty.'}, status=400)
    #
    #     order = Order.objects.create(
    #         user=request.user,
    #         total_amount=cart.total_amount,
    #         shipping_address=checkout_info.get('shipping_address', ''),
    #         phone=checkout_info.get('phone', ''),
    #         notes=checkout_info.get('notes', ''),
    #         status='confirmed',
    #     )
    #     for cart_item in cart_items:
    #         OrderItem.objects.create(
    #             order=order,
    #             product=cart_item.product,
    #             quantity=cart_item.quantity,
    #             price=cart_item.product.price,
    #         )
    #
    #     cart.delete()
    #     if 'checkout' in request.session:
    #         del request.session['checkout']
    #         request.session.modified = True
    #
    #     return JsonResponse({'success': True, 'order_id': order.id})
    # except Cart.DoesNotExist:
    #     return JsonResponse({'success': False, 'message': 'Cart not found.'}, status=400)
    # except razorpay.errors.SignatureVerificationError:
    #     return JsonResponse({'success': False, 'message': 'Payment verification failed.'}, status=400)
    # except Exception as e:
    #     return JsonResponse({'success': False, 'message': str(e)}, status=500)

@login_required
def payment_cancelled(request):
    """User closed Razorpay modal or payment failed on client-side."""
    messages.warning(request, 'Payment was cancelled. You can try again from checkout.')
    return render(request, 'payment_cancelled.html')

@csrf_exempt
def razorpay_webhook(request):
    """TEMP MODE: Webhook disabled."""
    return JsonResponse({'status': 'disabled', 'message': 'Webhook is disabled in temporary payment mode.'}, status=200)

    # REAL PAYMENT: Uncomment this block to re-enable Razorpay webhook handling
    # ------------------------------------------------------------------------
    # webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    # if request.method != 'POST' or not webhook_secret:
    #     return JsonResponse({'status': 'ignored'}, status=200)
    #
    # try:
    #     body = request.body
    #     received_sig = request.headers.get('X-Razorpay-Signature')
    #     client = razorpay.Client(auth=(getattr(settings, 'RAZORPAY_KEY_ID', ''), getattr(settings, 'RAZORPAY_KEY_SECRET', '')))
    #     client.utility.verify_webhook_signature(body, received_sig, webhook_secret)
    #     payload = json.loads(body.decode('utf-8'))
    #     return JsonResponse({'status': 'ok'})
    # except razorpay.errors.SignatureVerificationError:
    #     return JsonResponse({'status': 'invalid signature'}, status=400)
    # except Exception as e:
    #     return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def order_confirmation(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {'order': order}
    return render(request, 'order_confirmation.html', context)

@login_required
def my_orders(request):
    """User's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {'orders': orders}
    return render(request, 'my_orders.html', context)

@login_required
@require_POST
def cancel_order(request, order_id):
    """Cancel an order"""
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Only allow cancellation of pending or confirmed orders
        if order.status in ['pending', 'confirmed']:
            order.status = 'cancelled'
            order.save()
            messages.success(request, f'Order #{order.order_number} has been cancelled successfully.')
        else:
            messages.error(request, f'Order #{order.order_number} cannot be cancelled. It is already {order.get_status_display()}.')
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
    
    return redirect('my_orders')

@require_POST
def newsletter_subscribe(request):
    """Subscribe an email to the newsletter.

    Expects 'email' in POST form data. Returns JSON.
    """
    email = (request.POST.get('email') or '').strip()
    if not email:
        return JsonResponse({'success': False, 'message': 'Email is required.'}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'success': False, 'message': 'Please enter a valid email address.'}, status=400)

    try:
        obj, created = NewsletterSubscription.objects.get_or_create(email=email)
        if created:
            return JsonResponse({'success': True, 'message': 'Subscribed successfully!', 'created': True})
        else:
            return JsonResponse({'success': True, 'message': 'You are already subscribed.', 'created': False})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Failed to subscribe: {str(e)}'}, status=500)

@login_required
def add_review(request, product_id):
    """Add product review"""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id, is_active=True)
        form = ReviewForm(request.POST)
        
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            
            messages.success(request, 'Review submitted successfully!   ')
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@csrf_exempt
def analyze_disease(request):
    """API endpoint for disease analysis.

    Uses Gemini for disease prediction and recommendations.
    Accepts multipart/form-data with field 'image' (file) or JSON with 'image_base64'. Returns structured JSON.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Support both multipart (preferred) and base64 in JSON (legacy)
        if 'image' in request.FILES:
            image_file = request.FILES['image']
            image_bytes = image_file.read()
            mime_type = image_file.content_type or 'image/jpeg'
        else:
            body = request.body.decode('utf-8') or '{}'
            data = json.loads(body)
            if 'image_base64' in data:
                image_bytes = base64.b64decode(data['image_base64'].split(',')[-1])
                mime_type = data.get('mime_type', 'image/jpeg')
            else:
                return JsonResponse({'error': 'No image provided'}, status=400)

        # Direct Gemini Analysis (Skipping Plant.id)
        # Note: _gemini_analyze_image is defined above in this file
        ai_result = _gemini_analyze_image(image_bytes, mime_type)
        
        # Extract fields
        care_tips = ai_result.get('care_tips', [])
        fertilizer_recs = ai_result.get('fertilizer_recommendations', [])

        # Normalize to arrays of strings to avoid "[object Object]" in the UI
        care_tips = _as_string_list(care_tips)
        fertilizer_recs = _as_string_list(fertilizer_recs)

        result = {
            'species': ai_result.get('species'),
            'health_status': ai_result.get('health_status', 'Unknown'),
            'detected_diseases': ai_result.get('detected_diseases', []),
            'pests': ai_result.get('pests', []),
            'care_tips': care_tips,
            'fertilizer_recommendations': fertilizer_recs,
        }
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def analyze_soil(request):
    """Crop recommendation only (no Gemini).

    Expects JSON body with exactly the 7 numeric features used by the local ML model:
    - nitrogen, phosphorus, potassium, temperature, humidity, ph_level, rainfall
    Returns JSON with only: {"recommended_crop": str} or {"prediction_error": str}
    """
    print("\n=== Soil Analysis Request ===")
    print(f"Method: {request.method}")
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Log raw request body for debugging
        payload_raw = request.body.decode('utf-8') or '{}'
        print(f"Raw request body: {payload_raw}")
        
        try:
            data = json.loads(payload_raw)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON: {str(e)}"
            print(f"❌ {error_msg}")
            return JsonResponse({'prediction_error': 'Invalid JSON format'}, status=400)
            
        print(f"Parsed JSON data: {data}")

        # Pull only the 7 required features
        def _to_float(x, name):
            try:
                if x is None or x == '':
                    print(f"⚠️ Missing or empty value for {name}")
                    return None
                return float(x)
            except (ValueError, TypeError) as e:
                print(f"⚠️ Could not convert {name} to float: {x}")
                return None

        feats = {
            'nitrogen': _to_float(data.get('nitrogen'), 'nitrogen'),
            'phosphorus': _to_float(data.get('phosphorus'), 'phosphorus'),
            'potassium': _to_float(data.get('potassium'), 'potassium'),
            # Divide temperature by 10 before sending to frontend
            'temperature': _to_float(data.get('temperature'), 'temperature') ,
            'humidity': _to_float(data.get('humidity'), 'humidity'),
            'ph_level': _to_float(data.get('ph_level'), 'ph_level'),
            'rainfall': _to_float(data.get('rainfall'), 'rainfall'),
        }

        # Check for missing or invalid values
        missing = [k for k, v in feats.items() if v is None]
        if missing:
            error_msg = f"Missing or invalid values for: {', '.join(missing)}"
            print(f"❌ {error_msg}")
            return JsonResponse({
                'prediction_error': f'Please provide valid numeric values for all fields. Issues with: {", ".join(missing)}'
            }, status=200)
            
        print(f"✅ All input values valid: {feats}")

        # Make prediction (top-1)
        rec_crop = _predict_crop(
            feats['nitrogen'],
            feats['phosphorus'],
            feats['potassium'],
            feats['temperature'],
            feats['humidity'],
            feats['ph_level'],
            feats['rainfall'],
        )
        # Attempt to compute top-3 recommendations (if model supports probabilities)
        top_recs = []
        try:
            model = _load_crop_model()
            if model is not None and hasattr(model, 'predict_proba') and hasattr(model, 'classes_'):
                import numpy as np
                X = np.array([[
                    float(feats['nitrogen']),
                    float(feats['phosphorus']),
                    float(feats['potassium']),
                    float(feats['temperature']),
                    float(feats['humidity']),
                    float(feats['ph_level']),
                    float(feats['rainfall']),
                ]], dtype=float)
                probs = model.predict_proba(X)
                if probs is not None and len(probs.shape) == 2 and probs.shape[0] == 1:
                    prob_row = probs[0]
                    class_labels = list(getattr(model, 'classes_', []))
                    pairs = list(zip(class_labels, prob_row))
                    # Sort by probability descending
                    pairs.sort(key=lambda t: t[1], reverse=True)
                    for lbl, p in pairs[:3]:
                        top_recs.append({
                            'crop': str(lbl),
                            'score': float(p)
                        })
        except Exception as e:
            # Non-fatal; just log and continue with top-1 only
            print(f"Top-3 computation skipped due to error: {e}")

        if rec_crop:
            print(f"✅ Recommended crop: {rec_crop}")
            # Ensure top_recs contains the top-1 as first; if empty, synthesize from rec_crop
            if not top_recs:
                top_recs = [{ 'crop': str(rec_crop), 'score': None }]
            return JsonResponse({'recommended_crop': rec_crop, 'top_recommendations': top_recs})
            
        print("❌ No prediction returned from model")
        return JsonResponse({
            'prediction_error': 'Could not determine a suitable crop. Please check your input values and try again.'
        }, status=200)
        
    except Exception as e:
        import traceback
        error_msg = f"Unexpected error: {str(e)}"
        print(f"❌ {error_msg}")
        print("Stack trace:")
        traceback.print_exc()
        return JsonResponse({
            'prediction_error': 'An unexpected error occurred. Please try again later.'
        }, status=500)



def nearest_lab_page(request):
    return render(request, 'nearest_lab.html')

@csrf_exempt
def get_nearby_labs(request):
    """Return nearby laboratories within 10km using OpenStreetMap Overpass API.

    Accepts lat/lon via GET query params. Returns JSON: {"labs": [{name, lat, lon, address}, ...]}
    """
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')

    if not lat or not lon:
        return JsonResponse({'error': 'Missing lat or lon query params'}, status=400)
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'lat and lon must be valid numbers'}, status=400)

    if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
        return JsonResponse({'error': 'lat/lon out of range'}, status=400)

    # Use a 100km radius around the provided coordinates
    radii = [10000]
    data = None
    elements = []
    for radius_m in radii:
        query = f"""
        [out:json];
        (
          node["amenity"="laboratory"](around:{radius_m},{lat_f},{lon_f});
          node["healthcare"="laboratory"](around:{radius_m},{lat_f},{lon_f});
          node["amenity"="diagnostic_centre"](around:{radius_m},{lat_f},{lon_f});
          node["amenity"="hospital"]["laboratory"="yes"](around:{radius_m},{lat_f},{lon_f});
          node["amenity"="clinic"]["laboratory"="yes"](around:{radius_m},{lat_f},{lon_f});
        );
        out;
        """

        try:
            response = requests.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            elements = data.get('elements') or []
        except requests.exceptions.Timeout:
            return JsonResponse({'error': 'Upstream timeout querying Overpass API'}, status=504)
        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': f'Upstream error: {str(e)}'}, status=502)
        except ValueError:
            return JsonResponse({'error': 'Invalid JSON from Overpass API'}, status=502)

        if elements:
            break

    def _addr_from_tags(tags: dict) -> str:
        if not isinstance(tags, dict):
            return 'Address not available'
        full = tags.get('addr:full')
        if full:
            return full
        parts = [
            tags.get('addr:housenumber'),
            tags.get('addr:street'),
            tags.get('addr:city') or tags.get('addr:town') or tags.get('addr:village'),
            tags.get('addr:state'),
            tags.get('addr:postcode'),
        ]
        composed = ", ".join([p for p in parts if p])
        return composed or 'Address not available'

    # If still no elements after querying, return a not-found error for clearer UX
    if not elements:
        return JsonResponse({'error': 'No labs found within 100km of the provided location'}, status=404)

    import math

    def _haversine_km(lat1, lon1, lat2, lon2) -> float:
        R = 6371.0  # Earth radius in km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    labs = []
    for el in elements:
        if not isinstance(el, dict):
            continue
        tags = el.get('tags') or {}
        lat_v = el.get('lat')
        lon_v = el.get('lon')
        if lat_v is None or lon_v is None:
            continue
        # Extract optional contact details with sensible fallbacks
        phone = tags.get('contact:phone') or tags.get('phone') or 'Not available'
        email = tags.get('contact:email') or 'Not available'
        website = tags.get('website') or 'Not available'

        # Compute straight-line distance and enforce max 100 km
        distance_km = _haversine_km(lat_f, lon_f, float(lat_v), float(lon_v))
        if distance_km > 100.0:
            continue

        labs.append({
            'name': tags.get('name', 'Unknown Lab'),
            'lat': lat_v,
            'lon': lon_v,
            'address': _addr_from_tags(tags),
            'phone': phone,
            'email': email,
            'website': website,
            'distance_km': round(distance_km, 2),
        })
    # Sort by nearest first
    labs.sort(key=lambda x: x.get('distance_km', 0))

    return JsonResponse({'labs': labs})


def govsites(request):
    return render(request, 'gov_sites.html')


@require_GET
def weather_api(request):
    """Return current weather using API Ninjas by latitude/longitude.

    Query params:
    - lat: latitude (-90..90)
    - lon: longitude (-180..180)

    Response: JSON passthrough from API Ninjas with selected fields, or error.
    """
    lat = request.GET.get('lat')
    lon = request.GET.get('lon')
    if not lat or not lon:
        return JsonResponse({'error': 'Missing lat or lon query params'}, status=400)
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'lat and lon must be valid numbers'}, status=400)
    if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
        return JsonResponse({'error': 'lat/lon out of range'}, status=400)

    api_key = getattr(settings, 'API_NINJAS_API_KEY', '')
    if not api_key:
        return JsonResponse({'error': 'API_NINJAS_API_KEY not configured on server'}, status=500)

    url = 'https://api.api-ninjas.com/v1/weather'
    headers = {"X-Api-Key": api_key}
    params = {"lat": lat_f, "lon": lon_f}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code != 200:
            return JsonResponse({'error': f'Upstream error {resp.status_code}', 'detail': resp.text[:500]}, status=502)
        data = resp.json()
    except requests.exceptions.Timeout:
        return JsonResponse({'error': 'Weather provider timeout'}, status=504)
    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'Weather provider error: {str(e)}'}, status=502)
    except ValueError:
        return JsonResponse({'error': 'Invalid JSON from weather provider'}, status=502)

    # Optionally, ensure expected keys exist; otherwise just passthrough
    return JsonResponse(data)
