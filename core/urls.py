from django.urls import path, include
from . import views






urlpatterns = [
    path('registration/', views.CustomRegisterView.as_view(), name='rest_register'),
    path('login/', views.CustomLoginView.as_view(), name='rest_login'),
    path('rest-auth/', include('rest_auth.urls')),
    path('rest-auth/registration/', include('rest_auth.registration.urls')),

    path('weather/', views.WeatherView.as_view()),
]
