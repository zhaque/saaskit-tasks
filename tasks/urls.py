from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.contrib.auth import views as auth_views

urlpatterns = patterns('tasks.views',
	url(r'^$', 'startpage', name='tasks-startpage'),
	url(r'^browse/$', 'task_index', name='tasks-index'),
	url(r'^profile/(?P<username>\w+)/$', 'profile', name='tasks-profile'),
	url(r'^home/$', 'control_task_list', {}, name='tasks-home'),
	
	url(r'^task/create/$', 'task_create', name='tasks-task_create'),
	url(r'^task/(?P<object_id>\d+)/setup/$', 'task_setup', name='tasks-task_setup'),
	url(r'^task/(?P<object_id>\d+)/add_question/$', 'task_question_add', name='tasks-task_question_add'),
	url(r'^task/(?P<object_id>\d+)/manage/$', 'task_manage', name='tasks-task_manage'),
	url(r'^task/(?P<object_id>\d+)/stats/$', 'task_stats', name='tasks-task_stats'),
	
	url(r'^task/(?P<object_id>\d+)/$', 'task_detail', name='tasks-task_detail'),
	url(r'^task/(?P<object_id>\d+)/do/$', 'task_do', name='tasks-task_do'),
	
	url(r'^ad/create/$', 'ad_create', name='tasks-ad_create'),
	url(r'^ad/(?P<object_id>\d+)/$', 'ad_detail', name='tasks-ad_detail'),
	url(r'^ad/(?P<object_id>\d+)/manage/$', 'ad_manage', name='tasks-ad_manage'),
	
	url(r'^classified/(?P<object_id>\d+)/$', 'classified_detail', name='tasks-classified_detail'),
	url(r'^classified/(?P<object_id>\d+)/manage/$', 'classified_manage', name='tasks-classified_manage'),
	url(r'^classified/create/$', 'classified_create', name='tasks-classified_create'),
	
	url(r'^feed/create/$', 'feed_create', name='tasks-feed_create'),
	url(r'^feed/(?P<object_id>\d+)/$', 'feed_detail', name='tasks-feed_detail'),
	url(r'^feed/(?P<object_id>\d+)/manage/$', 'feed_manage', name='tasks-feed_manage'),
	url(r'^entry/(?P<object_id>\d+)/$', 'entry_detail', name='tasks-entry_detail'),
	
	url(r'^activity/(?P<object_id>\d+)/self-advertise/$', 'activity_self_advertise', name='tasks-activity_self_advertise'),
	url(r'^activity/(?P<object_id>\d+)/site-advertise/$', 'activity_site_advertise', name='tasks-activity_site_advertise'),
)

