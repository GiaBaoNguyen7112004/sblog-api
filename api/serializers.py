from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from .models import SocialMediaLink, Category, Post, Comment, CommentLike, PostLike, UserFollower
from django.contrib.auth.hashers import make_password
from rest_framework.validators import UniqueValidator
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiResponse
from rest_framework import status

User = get_user_model()
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'bio', 
                 'avatar', 'date_joined', 'last_login', 'password')
        read_only_fields = ('id', 'date_joined', 'last_login')
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8},
            'email': {'required': True, 'validators': [UniqueValidator(queryset=User.objects.all())]}
        }

    def create(self, validated_data):
        validated_data['username'] = validated_data.get('email')  # Set username to email
        validated_data['password'] = make_password(validated_data.get('password'))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'email' in validated_data:
            validated_data['username'] = validated_data.get('email')  # Update username when email changes
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data.get('password'))
        return super().update(instance, validated_data)

class SocialMediaLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaLink
        fields = ('id', 'link')  # Only expose id and link, hide user field

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class UserDetailSerializer(serializers.ModelSerializer):
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    followers = UserSerializer(many=True, read_only=True)
    following = UserSerializer(many=True, read_only=True)
    social_links = SocialMediaLinkSerializer(many=True, read_only=True)  # Add this line

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'bio', 'avatar',
                 'followers', 'following', 'followers_count', 'following_count',
                 'total_likes', 'is_following', 'social_links')  # Add social_links to fields
        read_only_fields = ('id', 'email')

    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()

    def get_total_likes(self, obj):
        return PostLike.objects.filter(post__user=obj).count()

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserFollower.objects.filter(
                follower=request.user,
                following=obj
            ).exists()
        return False

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'bio', 'avatar')

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        validated_data['username'] = validated_data['email']  # Use email as username
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ('id', 'user', 'content', 'created_at', 'post',
                 'likes_count', 'is_liked', 'replies')
        read_only_fields = ('user', 'created_at')

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_replies(self, obj):
        if obj.parent is None:  # Only get replies for parent comments
            replies = obj.replies.all()
            return CommentSerializer(replies, many=True, context=self.context).data
        return []

class PostSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(source='user.id', read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ('id', 'author_id', 'status', 'category', 'title', 'subtitle', 
                 'content', 'featured_image', 'created_at', 'updated_at', 
                 'likes_count', 'comments_count', 'is_liked', 'watch_count')
        read_only_fields = ('author_id', 'created_at', 'updated_at', 'watch_count')


    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

class PostDetailSerializer(PostSerializer):
    comments = serializers.SerializerMethodField()

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields + ('comments',)

    def get_comments(self, obj):
        # Only get parent comments
        comments = obj.comments.filter(parent=None)
        return CommentSerializer(comments, many=True, context=self.context).data

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(username=email, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                data['user'] = user
                return data
            raise serializers.ValidationError("Unable to log in with provided credentials.")
        raise serializers.ValidationError("Must include 'email' and 'password'.")

class LoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    user = UserSerializer()  # Dùng UserSerializer đã có

class PaginationSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    limit = serializers.IntegerField()

class PostPaginationSerializer(serializers.Serializer):
    pagination = PaginationSerializer()
    blogs = PostSerializer(many=True)

class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)

class ImageUploadSerializer(serializers.Serializer):
    image = serializers.ImageField()

class CategoryDetailSerializer(serializers.ModelSerializer):
    posts_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ('id', 'name', 'posts_count')

    def get_posts_count(self, obj):
        return obj.posts.count()

class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': "Passwords don't match"})
        return data

