import requests
import time, uuid
from urllib.parse import quote, urlencode
from urllib.request import urlopen, Request
import hmac, hashlib
from base64 import b64encode
import codecs
import json

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
        # weather Api 
        city = request.data.get('city')
        url = 'https://weather-ydn-yql.media.yahoo.com/forecastrss'
        method = 'GET'
        app_id = 'pMZPOy50'
        consumer_key = 'dj0yJmk9Qkdxbm1ZNjVZUXJJJmQ9WVdrOWNFMWFVRTk1TlRBbWNHbzlNQS0tJnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PTJi'
        consumer_secret = '14e6cf3f85f18098d47bcc929368943730cb0a99'
        concat = '&'
        query = {'location': city, 'format': 'json'}
        oauth = {
            'oauth_consumer_key': consumer_key,
            'oauth_nonce': uuid.uuid4().hex,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_version': '1.0'
        }
        merged_params = query.copy()
        merged_params.update(oauth)
        sorted_params = [k + '=' + quote(merged_params[k], safe='') for k in sorted(merged_params.keys())]
        signature_base_str =  method + concat + quote(url, safe='') + concat + quote(concat.join(sorted_params), safe='')

        composite_key = quote(consumer_secret, safe='') + concat
        key = codecs.encode(composite_key)
        msg = codecs.encode(signature_base_str)
        oauth_signature = b64encode(hmac.new(key, msg, hashlib.sha1).digest())

        oauth['oauth_signature'] = oauth_signature
        auth_header = 'OAuth ' + ', '.join(['{}="{}"'.format(k,v) for k,v in oauth.items()])

        url = url + '?' + urlencode(query)
        print(url)
        r = requests.get(url).status_code
        if bool(r == 401) or bool(r == 400) or bool(r == 500):
            response = None

        if bool(r == 200):
            request = Request(url)
            request.add_header('Authorization', auth_header)
            request.add_header('X-Yahoo-App-Id', app_id)
            response = urlopen(request).read()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        data = {
            "data": serializer.data,
            "weather": response
        }
        return Response(data, status=status.HTTP_201_CREATED)



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