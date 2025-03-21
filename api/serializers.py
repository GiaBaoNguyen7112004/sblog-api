from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from .models import SocialMediaLink, Category, Post, Comment, CommentLike, PostLike
from django.contrib.auth.hashers import make_password
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'bio', 'avatar', 'date_joined', 'last_login', 'password')
        read_only_fields = ('id', 'date_joined', 'last_login')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data.get('password'))
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data.get('password'))
        return super().update(instance, validated_data)

class SocialMediaLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialMediaLink
        fields = '__all__'
        read_only_fields = ('user',)

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ('id', 'user', 'content', 'created_at', 'likes_count', 'is_liked', 'replies')
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
    user = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = ('id', 'user', 'category', 'title', 'subtitle', 'content', 
                 'featured_image', 'status', 'auto_post', 'post_time', 
                 'created_at', 'updated_at', 'likes_count', 'comments_count', 'is_liked')
        read_only_fields = ('user', 'created_at', 'updated_at')

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
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            print(user)
            print(username)
            print(password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                data['user'] = user
                return data
            raise serializers.ValidationError("Unable to log in with provided credentials.")
        raise serializers.ValidationError("Must include 'username' and 'password'.") 