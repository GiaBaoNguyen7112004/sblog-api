# Generated by Django 5.1.7 on 2025-03-30 10:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0004_userfollower_user_following'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='post',
            name='auto_post',
        ),
        migrations.RemoveField(
            model_name='post',
            name='post_time',
        ),
        migrations.AlterField(
            model_name='post',
            name='status',
            field=models.CharField(choices=[('published', 'Published'), ('draft', 'Draft')], default='published', max_length=10),
        ),
    ]
