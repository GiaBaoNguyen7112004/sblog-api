from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model, authenticate
from django.db.models import Q
from .models import SocialMediaLink, Category, Post, Comment, CommentLike, PostLike
from .serializers import (
    UserSerializer, SocialMediaLinkSerializer, CategorySerializer,
    PostSerializer, PostDetailSerializer, CommentSerializer, LoginSerializer
)
from .utils import (
    create_response, create_success_response, create_validation_error_response,
    create_not_found_response, create_created_response
)
from .constants import ResponseMessage, EntityNames
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.auth.hashers import make_password


User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing users.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = User.objects.all()
        username = self.request.query_params.get('username', None)
        if username:
            queryset = queryset.filter(username__icontains=username)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return create_success_response(
            data=serializer.data,
            message=ResponseMessage.LIST_SUCCESS.format(EntityNames.USER)
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return create_success_response(
            data=serializer.data,
            message=ResponseMessage.GET_SUCCESS.format(EntityNames.USER)
        )

    # def create(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data)
    #     if not serializer.is_valid():
    #         return create_validation_error_response(serializer.errors)
    #     self.perform_create(serializer)
    #     return create_created_response(
    #         data=serializer.data,
    #         entity_name=EntityNames.USER
    #     )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return create_validation_error_response(serializer.errors)
        
        # Hash password trước khi lưu
        serializer.validated_data['password'] = make_password(serializer.validated_data['password'])

        self.perform_create(serializer)
        return create_created_response(
            data=serializer.data,
            entity_name=EntityNames.USER
        )


    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None):
        user_to_follow = self.get_object()
        if request.user == user_to_follow:
            return create_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=ResponseMessage.CANNOT_FOLLOW_SELF
            )
        request.user.following.add(user_to_follow)
        return create_success_response(message=ResponseMessage.FOLLOW_SUCCESS)


    @action(detail=True, methods=['post'])
    def unfollow(self, request, pk=None):
        user_to_unfollow = self.get_object()
        request.user.following.remove(user_to_unfollow)
        return create_success_response(message=ResponseMessage.UNFOLLOW_SUCCESS)

    @action(detail=True)
    def followers(self, request, pk=None):
        user = self.get_object()
        followers = user.followers.all()
        serializer = UserSerializer(followers, many=True)
        return create_success_response(
            data=serializer.data,
            message=ResponseMessage.GET_SUCCESS.format("followers")
        )

    @action(detail=True)
    def following(self, request, pk=None):
        user = self.get_object()
        following = user.following.all()
        serializer = UserSerializer(following, many=True)
        return create_success_response(
            data=serializer.data,
            message=ResponseMessage.GET_SUCCESS.format("following users")
        )

class SocialMediaLinkViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing social media links.
    """
    serializer_class = SocialMediaLinkSerializer

    def get_queryset(self):
        return SocialMediaLink.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing post categories.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class PostViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing blog posts.
    """

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer
        return PostSerializer

    def get_queryset(self):
        queryset = Post.objects.all()
        if self.request.user.is_authenticated:
            queryset = queryset.filter(
                Q(status='public') | Q(user=self.request.user)
            )
        else:
            queryset = queryset.filter(status='public')
        
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__name=category)
        
        return queryset.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return create_success_response(
            data=serializer.data,
            message=ResponseMessage.LIST_SUCCESS.format(EntityNames.POST)
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return create_success_response(
            data=serializer.data,
            message=ResponseMessage.GET_SUCCESS.format(EntityNames.POST)
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return create_validation_error_response(serializer.errors)
        self.perform_create(serializer)
        return create_created_response(
            data=serializer.data,
            entity_name=EntityNames.POST
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        post = self.get_object()
        like, created = PostLike.objects.get_or_create(
            user=request.user,
            post=post
        )
        if not created:
            like.delete()
            return create_success_response(
                message=ResponseMessage.UNLIKE_SUCCESS.format(EntityNames.POST)
            )
        return create_success_response(
            message=ResponseMessage.LIKE_SUCCESS.format(EntityNames.POST)
        )

class CommentViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing comments.
    """
    serializer_class = CommentSerializer


    def get_queryset(self):
        return Comment.objects.filter(parent=None)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return create_success_response(
            data=serializer.data,
            message=ResponseMessage.LIST_SUCCESS.format(EntityNames.COMMENT)
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return create_success_response(
            data=serializer.data,
            message=ResponseMessage.GET_SUCCESS.format(EntityNames.COMMENT)
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return create_validation_error_response(serializer.errors)
            
        post_id = request.data.get('post')
        parent_id = request.data.get('parent')
        
        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            return create_not_found_response(EntityNames.POST)
            
        parent = None
        if parent_id:
            try:
                parent = Comment.objects.get(id=parent_id)
                if parent.parent:
                    return create_response(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message=ResponseMessage.MAX_DEPTH_REACHED
                    )
            except Comment.DoesNotExist:
                return create_not_found_response(EntityNames.COMMENT)
        
        comment = serializer.save(
            user=request.user,
            post=post,
            parent=parent
        )
        
        return create_created_response(
            data=serializer.data,
            entity_name=EntityNames.COMMENT
        )

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        comment = self.get_object()
        like, created = CommentLike.objects.get_or_create(
            user=request.user,
            comment=comment
        )
        if not created:
            like.delete()
            return create_success_response(
                message=ResponseMessage.UNLIKE_SUCCESS.format(EntityNames.COMMENT)
            )
        return create_success_response(
            message=ResponseMessage.LIKE_SUCCESS.format(EntityNames.COMMENT)
        )

class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return create_validation_error_response({
                "error": "Please provide both username and password"
            })

        user = authenticate(username=username, password=password)
        
        if user is None:
            return create_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="Invalid username or password"
            )

        if not user.is_active:
            return create_response(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="User account is disabled"
            )

        refresh = RefreshToken.for_user(user)
        user_serializer = UserSerializer(user)

        return create_success_response(
            message="Login successful",
            data={
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': user_serializer.data
            }
        )

class LogoutView(APIView):
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return create_success_response(message="Logout successful")
        except Exception:
            return create_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid refresh token"
            )

class RegisterView(APIView):
    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if not serializer.is_valid():
            return create_validation_error_response(serializer.errors)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        
        return create_created_response(
            data={
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': serializer.data
            },
            entity_name=EntityNames.USER
        )
