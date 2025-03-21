from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'social-links', views.SocialMediaLinkViewSet, basename='social-links')
router.register(r'categories', views.CategoryViewSet)
router.register(r'posts', views.PostViewSet, basename='posts')
router.register(r'comments', views.CommentViewSet, basename='comments')

urlpatterns = [
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('', include(router.urls)),
] 