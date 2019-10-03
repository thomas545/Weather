from django.shortcuts import render
from rest_framework.response import Response
from django.conf import settings
from rest_framework import status, permissions, exceptions, views, generics
from rest_auth.registration.views import RegisterView
from rest_auth.views import LoginView
from rest_auth.app_settings import JWTSerializer
from rest_auth.utils import jwt_encode
from allauth.account.models import EmailAddress, EmailConfirmationHMAC

from .serializers import WeatherSerializer
from .models import Weather

class WeatherView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WeatherSerializer

    def get_queryset(self):
        queryset = Weather.objects.all()
        return queryset

    def create(self, request, *args, **kwargs):
        # from django.contrib.auth.models import User
        # user = User.objects.get(pk=1)
        
        user = request.user
        # TODO weather Api here.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)



class CustomRegisterView(RegisterView):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(self.get_response_data(user),
                        status=status.HTTP_201_CREATED,
                        headers=headers)

    def perform_create(self, serializer):
        user = serializer.save(self.request)
        if getattr(settings, 'REST_USE_JWT', False):
            self.token = jwt_encode(user)

        email = EmailAddress.objects.get(email=user.email, user=user)
        email.verified = True
        email.primary = True
        email.save()
        return user

class CustomLoginView(LoginView):
    queryset = ''

    def get_response(self):
        serializer_class = self.get_response_serializer()

        if getattr(settings, 'REST_USE_JWT', False):
            data = {
                'user': self.user,
                'token': self.token
            }
            serializer = serializer_class(instance=data,
                                          context={'request': self.request})
        else:
            serializer = serializer_class(instance=self.token,
                                          context={'request': self.request})

        response = Response(serializer.data, status=status.HTTP_200_OK)
        
        if getattr(settings, 'REST_USE_JWT', False):
            from rest_framework_jwt.settings import api_settings as jwt_settings
            if jwt_settings.JWT_AUTH_COOKIE:
                from datetime import datetime
                expiration = (datetime.utcnow() + jwt_settings.JWT_EXPIRATION_DELTA)
                response.set_cookie(jwt_settings.JWT_AUTH_COOKIE,
                                    self.token,
                                    expires=expiration,
                                    httponly=True)
        return response

    def post(self, request, *args, **kwargs):
        self.request = request
        self.serializer = self.get_serializer(data=self.request.data,
                                              context={'request': request})
        self.serializer.is_valid(raise_exception=True)

        self.login()
        return self.get_response()