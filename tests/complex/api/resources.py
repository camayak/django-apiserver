from django.contrib.auth.models import User, Group
from django.contrib.comments.models import Comment
from apiserver.fields import CharField, ForeignKey, ManyToManyField, OneToOneField, OneToManyField
from apiserver.resources import ModelResource
from complex.models import Post, Profile


class ProfileResource(ModelResource):
    class Meta:
        queryset = Profile.objects.all()
        route = '/profiles'


class CommentResource(ModelResource):
    class Meta:
        queryset = Comment.objects.all()
        route = '/comments'


class GroupResource(ModelResource):
    class Meta:
        queryset = Group.objects.all()
        route = '/groups'


class UserResource(ModelResource):
    groups = ManyToManyField(GroupResource, 'groups', full=True)
    profile = OneToOneField(ProfileResource, 'profile', full=True)
    
    class Meta:
        queryset = User.objects.all()
        route = '/users'


class PostResource(ModelResource):
    user = ForeignKey(UserResource, 'user')
    comments = OneToManyField(CommentResource, 'comments', full=False)
    
    class Meta:
        queryset = Post.objects.all()
        route = '/posts'
