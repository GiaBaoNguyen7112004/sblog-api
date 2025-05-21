from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password

# Người dùng
class User(AbstractUser):
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True, null=True)
    avatar = models.TextField(blank=True, null=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    verification_token = models.TextField(blank=True, null=True)
    following = models.ManyToManyField(
        'self',
        through='UserFollower',
        symmetrical=False,
        related_name='followers'
    )

    def __str__(self):
        return self.username

# Liên kết mạng xã hội
class SocialMediaLink(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="social_links")
    link = models.TextField()

    def __str__(self):
        return f"{self.user.username} - {self.link}"

# Danh mục bài viết
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name

# Bài viết
class Post(models.Model):
    STATUS_CHOICES = [
        ('published', 'Published'),
        ('draft', 'Draft'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='published')

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="posts")
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    featured_image = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    watch_count = models.IntegerField(default=0)

    def __str__(self):
        return self.title

# Bình luận (chỉ tối đa 2 cấp)
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    content = models.TextField()
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.parent and self.parent.parent:
            raise ValueError("Chỉ cho phép comment tối đa 2 cấp.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.content[:30]}"

# Lượt thích bình luận
class CommentLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comment_likes")
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'comment')

    def __str__(self):
        return f"{self.user.username} liked {self.comment.id}"

# Lượt thích bài viết
class PostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_likes")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} liked {self.post.title}"

class UserFollower(models.Model):
    
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
