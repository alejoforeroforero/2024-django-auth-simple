from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import (
    UserSerializer,
    ExtendedUserSerializer
)


User = get_user_model()


class RegisterView(APIView):

    def post(self, request):

        email = request.data.get('email')

        if User.objects.filter(email=email).exists():
            return Response({'success': False, 'message': 'Email already exists'}, status=status.HTTP_200_OK)

        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():

            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            response = Response({
                'success': True,
                'message': 'Check your email for verification',
                'access': str(refresh.access_token),
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)
            response.set_cookie(
                'refresh_token',
                str(refresh),
                httponly=True,
                samesite='Strict',
                secure=False,
                max_age=24 * 60 * 60
            )
            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = ExtendedUserSerializer(user)
        data = serializer.data

        return Response({'success': True, 'data': data}, status=status.HTTP_200_OK)

    def put(self, request):
        user = request.user
        serializer = ExtendedUserSerializer(
            user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            data = serializer.data

            return Response({'success': True, 'data': data, }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            response = Response(
                {"message": "Successfully logged out."}, status=status.HTTP_200_OK)
            response.delete_cookie('refresh_token')
            response.delete_cookie('access_token')
            return response
        except TokenError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')

        if not User.objects.filter(email=email).exists():
            return Response(
                {'success': False, 'message': 'The credentials you entered are incorrect. Please try again.'},
                status=status.HTTP_200_OK
            )

        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            data = response.data if hasattr(response, 'data') else {}
            data['message'] = "Login successful! You are now logged in"
            data['success'] = True

            refresh_token = response.data['refresh']
            response.set_cookie(
                'refresh_token',
                refresh_token,
                httponly=True,
                samesite='Strict',
                secure=False,
                max_age=24 * 60 * 60
            )
            del response.data['refresh']

            access_token = response.data['access']
            response.set_cookie(
                'access_token',
                access_token,
                samesite='Strict',
                secure=False,
                max_age=5 * 60
            )
        return response


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            request.data['refresh'] = refresh_token
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            new_refresh_token = response.data.get('refresh')
            if new_refresh_token:
                response.set_cookie(
                    'refresh_token',
                    new_refresh_token,
                    httponly=True,
                    samesite='Strict',
                    secure=False,  # set to True if using HTTPS
                    max_age=24 * 60 * 60  # 1 day in seconds
                )
                # Remove new refresh token from response body
                del response.data['refresh']
        return response
