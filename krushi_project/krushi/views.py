from django.shortcuts import render
import joblib
import numpy as np
from django.shortcuts import render
from .forms import CropForm
import joblib
import os
from django.conf import settings
from django.shortcuts import render,redirect
from .forms import RegisterForm,LoginForm
from .models import User

import numpy as np
from django.shortcuts import render
from django.core.files.storage import default_storage
from PIL import Image
import io


model = joblib.load(r"C:\Users\Welcome\Desktop\krushimitra\krushi_project\crop_model.pkl")

model_path = os.path.join(settings.BASE_DIR, "crop_model.pkl")
model = joblib.load(model_path)
def home(request):

    prediction = None

    if request.method == "POST":
        form = CropForm(request.POST)

        if form.is_valid():

            data = [
                form.cleaned_data['nitrogen'],
                form.cleaned_data['phosphorus'],
                form.cleaned_data['potassium'],
                form.cleaned_data['temperature'],
                form.cleaned_data['humidity'],
                form.cleaned_data['ph'],
                form.cleaned_data['rainfall']
            ]

            prediction = model.predict([data])[0]

    else:
        form = CropForm()

    return render(request, "index.html", {"form": form, "prediction": prediction})
def home(request):
    return render(request, 'home.html')


def register(request):

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('login')

    else:
        form = RegisterForm()

    return render(request,"register.html",{'form':form})


def login_view(request):

    error = None

    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            try:
                user = User.objects.get(email=email,password=password)
                request.session['user'] = user.name
                return redirect('home')
            except:
                error = "Invalid Credentials"

    else:
        form = LoginForm()

    return render(request,"login.html",{'form':form,'error':error})

 
# Load your Random Forest model and Label Encoder
# Assuming they are in your root directory
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'leaf_model.pkl')
ENCODER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'label_encoder.pkl')

model = joblib.load(MODEL_PATH)
encoder = joblib.load(ENCODER_PATH)

def predict_disease(request):
    if request.method == 'POST' and request.FILES['image']:
        # 1. Get the uploaded image
        file = request.FILES['image']
        
        # 2. Preprocess (Must match your training: e.g., grayscale + resize)
        img = Image.open(file).convert('L') 
        img = img.resize((64, 64)) 
        img_array = np.array(img).flatten() / 255.0
        features = img_array.reshape(1, -1)
        
        # 3. Predict
        prediction_idx = model.predict(features)[0]
        disease = encoder.inverse_transform([prediction_idx])[0]
        
        return render(request, 'frontend/home.html', {'prediction': disease})
    
    return render(request, 'frontend/home.html')