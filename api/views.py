from django.shortcuts import render
from rest_framework import viewsets, status, permissions 
from rest_framework.permissions import IsAuthenticated, AllowAny  # Thêm AllowAny vào đây
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model, authenticate
from django.db.models import Q, Count
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import permission_classes
from drf_yasg import openapi
from .renderers import StandardJSONRenderer
from .models import SocialMediaLink, Category, Post, Comment, CommentLike, PostLike, UserFollower
from .serializers import ( ChangePasswordSerializer,
    UserSerializer, SocialMediaLinkSerializer, CategorySerializer, CategoryDetailSerializer,
    PostSerializer, PostDetailSerializer, CommentSerializer, LoginSerializer,
    UserDetailSerializer, UserUpdateSerializer, RegisterSerializer, LoginResponseSerializer,
    PostPaginationSerializer, ImageUploadSerializer, RefreshTokenSerializer # Add this import
)
from drf_spectacular.utils import OpenApiResponse, OpenApiParameter, OpenApiRequest
from drf_spectacular.utils import OpenApiTypes, OpenApiExample
from .utils import (
    create_response, create_success_response, create_validation_error_response,
    create_not_found_response, create_created_response, CustomResponse
)
from .constants import ResponseMessage, EntityNames
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import LogoutSerializer
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
import cloudinary.uploader
from .serializers import ImageUploadSerializer
from rest_framework.permissions import AllowAny

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing users.
    """
    queryset = User.objects.all()
    # permission_classes = [permissions.AllowAny]
    renderer_classes = [StandardJSONRenderer] 

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserDetailSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = User.objects.all()
        email = self.request.query_params.get('email', None)
        if email:
            queryset = queryset.filter(email__icontains=email)
        return queryset


    def list(self, request):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return CustomResponse(
                data=serializer.data,
                status=status.HTTP_200_OK,
                message=ResponseMessage.LIST_SUCCESS.format(EntityNames.USER)
            )

        serializer = self.get_serializer(queryset, many=True)
        return CustomResponse(
            data=serializer.data,
            status=status.HTTP_200_OK,
            message=ResponseMessage.LIST_SUCCESS.format(EntityNames.USER)
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomResponse(serializer.data, status=status.HTTP_200_OK, message=ResponseMessage.GET_SUCCESS.format(EntityNames.USER))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(data=serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY, message=ResponseMessage.VALIDATION_ERROR)
        self.perform_create(serializer)
        return CustomResponse(data=serializer.data, status=status.HTTP_201_CREATED, message=ResponseMessage.CREATE_SUCCESS.format(EntityNames.USER))


    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return CustomResponse(data=serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY, message=ResponseMessage.VALIDATION_ERROR)
        self.perform_update(serializer)
        return CustomResponse(data=serializer.data, status=status.HTTP_200_OK, message=ResponseMessage.UPDATE_SUCCESS.format(EntityNames.USER))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return CustomResponse(status=status.HTTP_204_NO_CONTENT, message=ResponseMessage.DELETE_SUCCESS.format(EntityNames.USER))

    @permission_classes(permissions.IsAuthenticated)
    @extend_schema(request=None, responses={
        200: OpenApiResponse(description="Follow successful"),
        400: OpenApiResponse(description="Cannot follow yourself"),
        404: OpenApiResponse(description="User not found")
    })
    @action(detail=True, methods=['post'])
    def follow(self, request, pk=None):
        try:
            user_to_follow = self.get_object()
            
            # Check if trying to follow self
            if request.user.id == user_to_follow.id:
                return CustomResponse(
                    status=status.HTTP_400_BAD_REQUEST,
                    message=ResponseMessage.CANNOT_FOLLOW_SELF
                )

            # Create follow relationship
            _, created = UserFollower.objects.get_or_create(
                follower=request.user,
                following=user_to_follow
            )

            if created:
                message = ResponseMessage.FOLLOW_SUCCESS
            else:
                message = "You are already following this user"

            return CustomResponse(
                status=status.HTTP_200_OK,
                message=message
            )
            
        except User.DoesNotExist:
            return CustomResponse(
                status=status.HTTP_404_NOT_FOUND,
                message=ResponseMessage.USER_NOT_FOUND
            )

    @permission_classes(permissions.IsAuthenticated)
    @extend_schema(request =None, responses=None)
    @action(detail=True, methods=['post'])
    def unfollow(self, request, pk=None):
        user_to_unfollow = self.get_object()
        deleted = UserFollower.objects.filter(
            follower=request.user,
            following=user_to_unfollow
        ).delete()
        
        if deleted[0] > 0:
            return CustomResponse(status=status.HTTP_200_OK, message=ResponseMessage.UNFOLLOW_SUCCESS.format(EntityNames.USER))
        return CustomResponse(status=status.HTTP_400_BAD_REQUEST, message=ResponseMessage.UNFOLLOW_NOT_FOLLOWING.format(EntityNames.USER))


    @extend_schema(request =None, responses={200: OpenApiResponse(response=UserSerializer(many=True))})
    @action(detail=True)
    def followers(self, request, pk=None):
        user = self.get_object()
        followers = user.followers.all()
        serializer = UserSerializer(followers, many=True)
        return CustomResponse(data=serializer.data, status=status.HTTP_200_OK, message=ResponseMessage.LIST_SUCCESS.format(EntityNames.USER))


    @extend_schema(request =None, responses={200: OpenApiResponse(response=UserSerializer(many=True))})
    @action(detail=True)
    def following(self, request, pk=None):
        user = self.get_object()
        following = user.following.all()
        serializer = UserSerializer(following, many=True)
        return CustomResponse(data=serializer.data, status=status.HTTP_200_OK, message=ResponseMessage.LIST_SUCCESS.format(EntityNames.USER))

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='username',
                description='Username của user cần tìm',
                required=True,
                type=OpenApiTypes.STR
            )
        ],
        responses={
            200: OpenApiResponse(response=UserDetailSerializer),
            404: OpenApiResponse(description='User not found')
        }
    )
    @action(detail=False, methods=['get'], url_path='by-username')
    def by_username(self, request):
        username = request.query_params.get('username')
        if not username:
            return CustomResponse(
                status=status.HTTP_400_BAD_REQUEST,
                message="Username parameter is required"
            )
            
        try:
            user = User.objects.get(username=username)
            serializer = UserDetailSerializer(user, context={'request': request})
            return CustomResponse(
                data=serializer.data,
                status=status.HTTP_200_OK,
                message=ResponseMessage.GET_SUCCESS.format(EntityNames.USER)
            )
        except User.DoesNotExist:
            return CustomResponse(
                status=status.HTTP_404_NOT_FOUND,
                message=ResponseMessage.USER_NOT_FOUND
            )

class SocialMediaLinkViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing social media links.
    """
    serializer_class = SocialMediaLinkSerializer
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [StandardJSONRenderer] 
    def get_queryset(self):
        return SocialMediaLink.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    @extend_schema(
        request=SocialMediaLinkSerializer,
        responses={200: OpenApiResponse(response=SocialMediaLinkSerializer)}
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return CustomResponse(data=serializer.data, status=status.HTTP_200_OK, message=ResponseMessage.LIST_SUCCESS.format(EntityNames.SOCIAL_MEDIA_LINK))
        
    @extend_schema(
        request=SocialMediaLinkSerializer,
        responses={200: OpenApiResponse(response=SocialMediaLinkSerializer)}
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return CustomResponse(data=serializer.data, status=status.HTTP_200_OK, message=ResponseMessage.GET_SUCCESS.format(EntityNames.SOCIAL_MEDIA_LINK))

    @extend_schema(
        request=SocialMediaLinkSerializer,
        responses={201: OpenApiResponse(response=SocialMediaLinkSerializer)}
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(data=serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY, message=ResponseMessage.VALIDATION_ERROR)
        self.perform_create(serializer)
        return CustomResponse(data=serializer.data, status=status.HTTP_201_CREATED, message=ResponseMessage.CREATE_SUCCESS.format(EntityNames.SOCIAL_MEDIA_LINK))

    @extend_schema(
        request=SocialMediaLinkSerializer,
        responses={200: OpenApiResponse(response=SocialMediaLinkSerializer)}
    )
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return CustomResponse(data=serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY, message=ResponseMessage.VALIDATION_ERROR)
        self.perform_update(serializer)
        return CustomResponse(data=serializer.data, status=status.HTTP_200_OK, message=ResponseMessage.UPDATE_SUCCESS.format(EntityNames.SOCIAL_MEDIA_LINK))

    @extend_schema(
        request=SocialMediaLinkSerializer,
        responses={200: OpenApiResponse(response=SocialMediaLinkSerializer)}
    )
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return CustomResponse(status=status.HTTP_204_NO_CONTENT, message=ResponseMessage.DELETE_SUCCESS.format(EntityNames.SOCIAL_MEDIA_LINK))


# Tạo serializer cho response pagination
# class PostPaginationSerializer(serializers.Serializer):
#     total = serializers.IntegerField()
#     page = serializers.IntegerField()
#     total_pages = serializers.IntegerField()
#     limit = serializers.IntegerField()
#     results = PostSerializer(many=True)

class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing post categories.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    renderer_classes = [StandardJSONRenderer]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CategoryDetailSerializer
        return CategorySerializer

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return CustomResponse(
            data=serializer.data,
            status=status.HTTP_200_OK,
            message=ResponseMessage.LIST_SUCCESS.format(EntityNames.CATEGORY)
        )
        
    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return CustomResponse(
                data=serializer.data,
                status=status.HTTP_200_OK,
                message=ResponseMessage.GET_SUCCESS.format(EntityNames.CATEGORY)
            )
        except Category.DoesNotExist:
            return CustomResponse(
                status=status.HTTP_404_NOT_FOUND,
                message=ResponseMessage.CATEGORY_NOT_FOUND
            )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                data=serializer.errors,
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=ResponseMessage.VALIDATION_ERROR
            )
        self.perform_create(serializer)
        return CustomResponse(
            data=serializer.data,
            status=status.HTTP_201_CREATED,
            message=ResponseMessage.CREATE_SUCCESS.format(EntityNames.CATEGORY)
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if not serializer.is_valid():
            return CustomResponse(
                data=serializer.errors,
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=ResponseMessage.VALIDATION_ERROR
            )
        self.perform_update(serializer)
        return CustomResponse(
            data=serializer.data,
            status=status.HTTP_200_OK,
            message=ResponseMessage.UPDATE_SUCCESS.format(EntityNames.CATEGORY)
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return CustomResponse(
            status=status.HTTP_204_NO_CONTENT,
            message=ResponseMessage.DELETE_SUCCESS.format(EntityNames.CATEGORY)
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='page',
                description='Số trang muốn hiển thị',
                required=False,
                type=OpenApiTypes.INT,
                default=1
            ),
            OpenApiParameter(
                name='limit',
                description='Số lượng bài viết mỗi trang',
                required=False,
                type=OpenApiTypes.INT,
                default=10
            ),
            OpenApiParameter(
                name='sort_by',
                description='Trường để sắp xếp',
                required=False,
                type=OpenApiTypes.STR,
                enum=['title', 'created_at', 'updated_at', 'like_count', 'comment_count'],
                default='created_at'
            ),
            OpenApiParameter(
                name='order',
                description='Thứ tự sắp xếp',
                required=False,
                type=OpenApiTypes.STR,
                enum=['asc', 'desc'],
                default='desc'
            ),
            OpenApiParameter(
                name='author',
                description='ID của tác giả để lọc bài viết',
                required=False,
                type=OpenApiTypes.INT
            ),
            OpenApiParameter(
                name='liked',
                description='Chỉ hiển thị bài viết mà người dùng hiện tại đã like',
                required=False,
                type=OpenApiTypes.BOOL
            ),
        ],
        responses={
            # 200: PostPaginationSerializer,
            500: OpenApiTypes.OBJECT,
        },    
    )
    @action(detail=True, methods=['get'])
    def posts(self, request, pk=None):
        """
        Lấy danh sách bài viết theo category với các tùy chọn lọc và sắp xếp
        """
        try:
            category = self.get_object()
            
            # Lấy tham số từ query params
            page = int(request.query_params.get('page', 1))
            limit = int(request.query_params.get('limit', 10))
            sort_by = request.query_params.get('sort_by', 'created_at')
            order = request.query_params.get('order', 'desc')
            author_id = request.query_params.get('author')
            liked = request.query_params.get('liked')
            
            # Xây dựng queryset cơ bản
            queryset = category.posts.all()
            
            # Lọc theo author nếu được chỉ định
            if author_id:
                queryset = queryset.filter(user_id=author_id)
            
            # Lọc theo bài viết user đã like nếu được chỉ định và user đã đăng nhập
            if liked and request.user.is_authenticated:
                queryset = queryset.filter(likes__user=request.user)
            
            # Xác định thứ tự sắp xếp
            order_prefix = '-' if order.lower() == 'desc' else ''
            order_by = f"{order_prefix}{sort_by}"
            
            # Kiểm tra trường sort_by có hợp lệ không
            valid_sort_fields = ['title', 'created_at', 'updated_at', 'like_count', 'comment_count']
            if sort_by == 'like_count':
                queryset = queryset.annotate(like_count=Count('likes')).order_by(order_by)
            elif sort_by == 'comment_count':
                queryset = queryset.annotate(comment_count=Count('comments')).order_by(order_by)
            elif sort_by in valid_sort_fields:
                queryset = queryset.order_by(order_by)
            else:
                # Mặc định sắp xếp theo created_at nếu trường không hợp lệ
                queryset = queryset.order_by('-created_at')
            
            # Phân trang
            paginator = Paginator(queryset, limit)
            
            if page > paginator.num_pages:
                page = 1
            
            page_obj = paginator.get_page(page)
            
            # Serialize dữ liệu
            serializer = PostSerializer(page_obj, many=True, context={'request': request})
            
            # Cấu trúc response
            response_data = {
                'pagination': {
                    'total': paginator.count,
                    'page': page,
                    'total_pages': paginator.num_pages,
                    'limit': limit
                },
                'blogs': serializer.data
            }

            return CustomResponse(data=response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return CustomResponse(
                data={'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PostViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing blog posts.
    """
    renderer_classes = [StandardJSONRenderer] 

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PostDetailSerializer
        return PostSerializer

    def get_queryset(self):
        queryset = Post.objects.all()
        
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__name=category)
        
        return queryset.order_by('-created_at')

    # @extend_schema(
    #     request=PostSerializer,
    #     responses={200: OpenApiResponse(response=PostSerializer)}
    # )
    # def list(self, request, *args, **kwargs):
    #     queryset = self.get_queryset()
    #     serializer = self.get_serializer(queryset, many=True)
    #     return Response(serializer.data, status=status.HTTP_200_OK, message=ResponseMessage.LIST_SUCCESS.format(EntityNames.POST))

    @extend_schema(
        request=PostDetailSerializer,
        responses={200: OpenApiResponse(response=PostDetailSerializer)}
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Tăng watch_count lên 1 đơn vị
        instance.watch_count = instance.watch_count + 1
        instance.save(update_fields=['watch_count'])
        
        serializer = self.get_serializer(instance)
        return CustomResponse(
            data=serializer.data, 
            status=status.HTTP_200_OK, 
            message=ResponseMessage.GET_SUCCESS.format(EntityNames.POST)
        )

    @extend_schema(
        request=PostSerializer,
        responses={201: OpenApiResponse(response=PostSerializer)}
    )
    @permission_classes(permissions.IsAuthenticated)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        # Kiểm tra category có được gửi lên không
        if 'category' not in request.data:
            return CustomResponse(
                data={"category": ["Trường này là bắt buộc."]}, 
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        # Kiểm tra category có tồn tại không
        if not serializer.is_valid():
            return CustomResponse(data=serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        self.perform_create(serializer)
        return CustomResponse(
            data=serializer.data,
            status=status.HTTP_201_CREATED,
            message=ResponseMessage.CREATE_SUCCESS.format(EntityNames.POST)
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        request=PostSerializer,
        responses={200: OpenApiResponse(response=PostSerializer)}
    )
    @permission_classes(permissions.IsAuthenticated)
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        post = self.get_object()
        like, created = PostLike.objects.get_or_create(
            user=request.user,
            post=post
        )
        if not created:
            like.delete()
            return CustomResponse(
                message=ResponseMessage.UNLIKE_SUCCESS.format(EntityNames.POST),
                status=status.HTTP_200_OK
            )
        return CustomResponse(
            message=ResponseMessage.LIKE_SUCCESS.format(EntityNames.POST),
            status=status.HTTP_200_OK
        )
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='page',
                description='Số trang muốn hiển thị',
                required=False,
                type=OpenApiTypes.INT,
                default=1
            ),
            OpenApiParameter(
                name='limit',
                description='Số lượng bài viết mỗi trang',
                required=False,
                type=OpenApiTypes.INT,
                default=10
            ),
            OpenApiParameter(
                name='sort_by',
                description='Trường để sắp xếp',
                required=False,
                type=OpenApiTypes.STR,
                enum=['title', 'created_at', 'updated_at', 'like_count', 'comment_count'],
                default='created_at'
            ),
            OpenApiParameter(
                name='order',
                description='Thứ tự sắp xếp',
                required=False,
                type=OpenApiTypes.STR,
                enum=['asc', 'desc'],
                default='desc'
            ),
            OpenApiParameter(
                name='author',
                description='ID của tác giả để lọc bài viết',
                required=False,
                type=OpenApiTypes.INT
            ),
            OpenApiParameter(
                name='liked',
                description='Chỉ hiển thị bài viết mà người dùng hiện tại đã like',
                required=False,
                type=OpenApiTypes.BOOL
            ),
        ],
        responses={
            200: PostPaginationSerializer,
            500: OpenApiTypes.OBJECT,
        },    
    )
    def list(self, request, pk=None):
        """
        Lấy danh sách bài viết theo category với các tùy chọn lọc và sắp xếp
        """
        try:
            # Lấy tham số từ query params
            page = int(request.query_params.get('page', 1))
            limit = int(request.query_params.get('limit', 10))
            sort_by = request.query_params.get('sort_by', 'created_at')
            order = request.query_params.get('order', 'desc')
            author_id = request.query_params.get('author')
            liked = request.query_params.get('liked')
            category_id = request.query_params.get('category')
            
            # Xây dựng queryset cơ bản
            queryset = Post.objects.all()
            if category_id :
                queryset = queryset.filter(category__id=category_id)

            # Lọc theo author nếu được chỉ định
            if author_id:
                queryset = queryset.filter(user_id=author_id)
            
            # Lọc theo bài viết user đã like nếu được chỉ định và user đã đăng nhập
            if liked and request.user.is_authenticated:
                queryset = queryset.filter(likes__user=request.user)
            
            # Xác định thứ tự sắp xếp
            order_prefix = '-' if order.lower() == 'desc' else ''
            order_by = f"{order_prefix}{sort_by}"
            
            # Kiểm tra trường sort_by có hợp lệ không
            valid_sort_fields = ['title', 'created_at', 'updated_at', 'like_count', 'comment_count']
            if sort_by == 'like_count':
                queryset = queryset.annotate(like_count=Count('likes')).order_by(order_by)
            elif sort_by == 'comment_count':
                queryset = queryset.annotate(comment_count=Count('comments')).order_by(order_by)
            elif sort_by in valid_sort_fields:
                queryset = queryset.order_by(order_by)
            else:
                # Mặc định sắp xếp theo created_at nếu trường không hợp lệ
                queryset = queryset.order_by('-created_at')
            
            # Phân trang
            paginator = Paginator(queryset, limit)
            
            if page > paginator.num_pages:
                page = 1
            
            page_obj = paginator.get_page(page)
            
            # Serialize dữ liệu
            serializer = PostSerializer(page_obj, many=True, context={'request': request})
            
            # Cấu trúc response
            response_data = {
                'pagination': {
                    'total': paginator.count,
                    'page': page,
                    'total_pages': paginator.num_pages,
                    'limit': limit
                },
                'blogs': serializer.data
            }
            
            return CustomResponse(data=response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return CustomResponse(
                data={'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    
    def get_queryset(self):
        queryset = Comment.objects.filter(parent=None)  # Chỉ lấy các comment gốc
        
        # Lọc theo post_id nếu được cung cấp
        post_id = self.request.query_params.get('post')
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        
        # Lọc theo user_id nếu được cung cấp
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
            
        # Thêm số lượng likes vào mỗi comment
        queryset = queryset.annotate(likes_count=Count('likes'))
        
        # Kiểm tra xem user hiện tại đã like comment chưa
        if self.request.user.is_authenticated:
            queryset = queryset.annotate(
                is_liked=Count(
                    'likes',
                    filter=Q(likes__user=self.request.user)
                )
            )
        
        return queryset
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='post',
                description='ID của bài viết để lọc comment',
                required=False,
                type=OpenApiTypes.INT
            ),
            OpenApiParameter(
                name='user',
                description='ID của người dùng để lọc comment',
                required=False,
                type=OpenApiTypes.INT
            ),
        ],
        description="Lấy danh sách các comment (chỉ comment gốc, không bao gồm replies)"
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return CustomResponse(data=serializer.data)
    
    @extend_schema(
        description="Tạo một comment mới"
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return CustomResponse(data=serializer.data, status=status.HTTP_201_CREATED)
        return CustomResponse(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Cập nhật một comment"
    )
    def update(self, request, *args, **kwargs):
        comment = self.get_object()
        
        # Kiểm tra quyền: chỉ tác giả mới được sửa comment
        if comment.user != request.user:
            return CustomResponse(
                data={"detail": "Bạn không có quyền sửa comment này."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(data=serializer.data)
        return CustomResponse(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        description="Cập nhật một phần của comment"
    )
    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
    
    @extend_schema(
        description="Xóa một comment"
    )
    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        
        # Kiểm tra quyền: chỉ tác giả mới được xóa comment
        if comment.user != request.user:
            return CustomResponse(
                data={"detail": "Bạn không có quyền xóa comment này."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        comment.delete()
        return CustomResponse(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        description="Thích hoặc bỏ thích một comment"
    )
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        comment = self.get_object()
        user = request.user
        
        if not user.is_authenticated:
            return CustomResponse(
                data={"detail": "Bạn cần đăng nhập để thực hiện hành động này."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Kiểm tra xem người dùng đã thích comment này chưa
        like_exists = CommentLike.objects.filter(comment=comment, user=user).exists()

        if like_exists:
            # Nếu đã thích, thì bỏ thích
            CommentLike.objects.filter(comment=comment, user=user).delete()
            return CustomResponse(data={"detail": "Đã bỏ thích comment."})
        else:
            # Nếu chưa thích, thì thích
            CommentLike.objects.create(comment=comment, user=user)
            return CustomResponse(data={"detail": "Đã thích comment."})

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='parent',
                description='ID của comment cần trả lời',
                required=True,
                type=OpenApiTypes.INT
            ),

        ],
        request=None,
        responses={
            200: OpenApiResponse(response=CommentSerializer),
            400: OpenApiResponse(response=None),
            401: OpenApiResponse(response=None),
            404: OpenApiResponse(response=None),
            422: OpenApiResponse(response=None),
        }
    )
    @action(detail=False, methods=['post'])
    def reply(self, request):
        parent_id = request.query_params.get('parent')
        if not parent_id:
            return CustomResponse(
                data={"detail": "Bạn cần cung cấp ID của comment cần trả lời."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Lấy comment cha
        try:
            parent_comment = Comment.objects.get(pk=parent_id)
        except Comment.DoesNotExist:
            return CustomResponse(
                data={"detail": "Comment cha không tồn tại."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Tạo reply
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                user=request.user,
                parent=parent_comment,
                post=parent_comment.post  # Reply thuộc cùng post với comment cha
            )
            return CustomResponse(data=serializer.data, status=status.HTTP_201_CREATED)
        return CustomResponse(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]
    renderer_classes = [StandardJSONRenderer] 

    @extend_schema(
        request=LoginSerializer,
        responses={200: OpenApiResponse(response=LoginResponseSerializer)}
    )    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return CustomResponse(
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                data={"message": ResponseMessage.INVALID_CREDENTIALS}
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return CustomResponse(
                data={"message": ResponseMessage.INVALID_CREDENTIALS},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user = authenticate(request, username=user.username, password=password)
        
        if user is None:
            return CustomResponse(
                data={"message": ResponseMessage.INVALID_CREDENTIALS},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return CustomResponse(
                data={"message": ResponseMessage.USER_ACCOUNT_DISABLED},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)
        user_serializer = UserSerializer(user)

        return CustomResponse(data={
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': user_serializer.data
        }, status=status.HTTP_200_OK, message=ResponseMessage.LOGIN_SUCCESS)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    @extend_schema(
        request=LogoutSerializer,
        responses={200: None},
        description="Đăng xuất và vô hiệu hóa token"
    )
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            try:
                refresh_token = serializer.validated_data['refresh_token']
                token = RefreshToken(refresh_token)
                token.blacklist()  # Thêm token vào blacklist
                return CustomResponse(
                    status=status.HTTP_200_OK,
                    message=ResponseMessage.LOGOUT_SUCCESS
                )
            except Exception:
                return CustomResponse(
                    status=status.HTTP_400_BAD_REQUEST,
                    message=ResponseMessage.INVALID_REFRESH_TOKEN
                )
        return CustomResponse(
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class RegisterView(APIView):
    renderer_classes = [StandardJSONRenderer] 
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=RegisterSerializer,
        responses={201: OpenApiResponse(response=LoginResponseSerializer)}
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(data=serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        
        return CustomResponse(data={
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED, message=ResponseMessage.REGISTER_SUCCESS)

class ImageUploadView(APIView):
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = ImageUploadSerializer
    
    @extend_schema(
        request=ImageUploadSerializer,
        responses={201: OpenApiResponse(description="Image uploaded successfully")}
    )
    def post(self, request, *args, **kwargs):
        serializer = ImageUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            image = serializer.validated_data['image']
            try:
                # Upload to cloudinary
                upload_result = cloudinary.uploader.upload(
                    image,
                    folder="sblog",  # optional folder name in cloudinary
                    public_id=None,  # let cloudinary generate a unique id
                    overwrite=True,
                    resource_type="auto"
                )
                
                # Return the upload result
                data = {
                    'url': upload_result.get('secure_url'),
                    'public_id': upload_result.get('public_id'),
                    'format': upload_result.get('format')
                }
                
                return CustomResponse(
                    data=data,
                    status=status.HTTP_201_CREATED,
                    message="Upload image successfully"
                )
                
            except Exception as e:
                return CustomResponse(
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Upload failed: {str(e)}"
                )
        
        return CustomResponse(
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
            message="Invalid input data"
        )

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    serializer_class = RefreshTokenSerializer

    @extend_schema(
        request=RefreshTokenSerializer,
        responses={
            200: OpenApiResponse(
                description="Token refreshed successfully",
                response=LoginResponseSerializer
            ),
            401: OpenApiResponse(description="Invalid refresh token")
        }
    )
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                refresh_token = serializer.validated_data['refresh_token']
                token = RefreshToken(refresh_token)
                access_token = str(token.access_token)
                
                return CustomResponse(
                    data={
                        'access_token': access_token,
                        'refresh_token': str(token)
                    },
                    status=status.HTTP_200_OK,
                    message=ResponseMessage.REFRESH_TOKEN_SUCCESS
                )
                
            except TokenError:
                return CustomResponse(
                    status=status.HTTP_401_UNAUTHORIZED,
                    message=ResponseMessage.INVALID_REFRESH_TOKEN
                )
                
        return CustomResponse(
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
            message=ResponseMessage.VALIDATION_ERROR
        )

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password changed successfully"),
            400: OpenApiResponse(description="Invalid input"),
            401: OpenApiResponse(description="Invalid old password")
        }
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']

            # Check if old password is correct
            if not user.check_password(old_password):
                return CustomResponse(
                    status=status.HTTP_401_UNAUTHORIZED,
                    message="Current password is incorrect"
                )

            # Set new password
            user.set_password(new_password)
            user.save()

            return CustomResponse(
                status=status.HTTP_200_OK,
                message="Password changed successfully"
            )

        return CustomResponse(
            data=serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
            message=ResponseMessage.VALIDATION_ERROR
        )
class SearchView(APIView):
    permission_classes = [AllowAny]
    
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='q',
                description='Search query for post titles or usernames',
                required=True,
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='type',
                description='Search type: less (max 5 results each) or hard (all results)',
                required=False,
                type=OpenApiTypes.STR,
                enum=['less', 'hard'],
                default='less'
            )
        ],
        responses={
            200: OpenApiResponse(description="Search results"),
            400: OpenApiResponse(description="Invalid parameters")
        }
    )
    def get(self, request):
        search_query = request.query_params.get('q', '')
        search_type = request.query_params.get('type', 'less')

        if not search_query:
            return CustomResponse(
                status=status.HTTP_400_BAD_REQUEST,
                message="Search query is required",
                data={
                    "posts": [],
                    "users": []
                }
            )

        # Search posts by title
        posts = Post.objects.filter(
            Q(title__icontains=search_query) | 
            Q(subtitle__icontains=search_query)
        ).order_by('-created_at')

        # Search users by name or email
        users = User.objects.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        ).order_by('-date_joined')

        # Limit results if type is 'less'
        if search_type == 'less':
            posts = posts[:5]
            users = users[:5]

        # Serialize the results
        post_serializer = PostSerializer(posts, many=True, context={'request': request})
        user_serializer = UserDetailSerializer(users, many=True, context={'request': request})

        return CustomResponse(
            status=status.HTTP_200_OK,
            message="Search results",
            data={
                "posts": post_serializer.data,
                "users": user_serializer.data
            }
        )