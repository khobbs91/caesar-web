from django.conf.urls.defaults import *

urlpatterns = patterns('caesar.comments.views',
    (r'new/', 'new_comment'),
)