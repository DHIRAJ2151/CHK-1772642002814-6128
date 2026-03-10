from django.contrib import admin
from django.urls import path
from krushi import views

urlpatterns = [
   path('admin/', admin.site.urls),
    path('', views.home, name="home"),
    path('register/', views.register, name="register"),
    path('login/', views.login_view, name="login"),
    path('detect/', views.predict_disease, name='detect_disease'),

]