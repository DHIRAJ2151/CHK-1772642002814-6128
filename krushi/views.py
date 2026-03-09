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