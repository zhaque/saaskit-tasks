from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.contrib.auth import views as auth_views

urlpatterns = patterns('tasks.views',
	url(r'^$', 'task_index', name='tasks-index'),
	url(r'^profile/(?P<username>\w+)/$', 'profile', name='tasks-profile'),
	url(r'^admin/$', 'project_list', name='tasks-projects'),
	url(r'^home/$', 'control_task_list', {}, name='tasks-home'),
	url(r'^task/new/$', 'task_new', name='tasks-task_new'),
	
	url(r'^task/create/$', 'task_create', name='tasks-task_create'),
	url(r'^task/(?P<object_id>\d+)/setup/$', 'task_setup', name='tasks-task_setup'),
	url(r'^task/(?P<object_id>\d+)/add_question/$', 'task_question_add', name='tasks-task_question_add'),
	url(r'^task/(?P<object_id>\d+)/edit/$', 'task_edit', name='tasks-task_edit'),
	url(r'^task/(?P<object_id>\d+)/manage/$', 'task_manage', name='tasks-task_manage'),
	url(r'^task/(?P<object_id>\d+)/stats/$', 'task_stats', name='tasks-task_stats'),
	
	url(r'^task/(?P<object_id>\d+)/$', 'task_detail', name='tasks-task_detail'),
	url(r'^task/(?P<object_id>\d+)/do/$', 'task_do', name='tasks-task_do'),
	
	url(r'^project/(?P<object_id>\d+)/$', 'project_detail', name='tasks-project_incomplete_tasks'),
	url(r'^project/(?P<object_id>\d+)/completed/$', 'project_detail', {'view_completed':1}, name='tasks-project_complete_tasks'),    
	#url(r'^project/(?P<object_id>\d+)/delete/$', 'project_delete', name="tasks-project_delete"),
	
	url(r'^ad/create/$', 'ad_create', name='tasks-ad_create'),
	url(r'^ad/(?P<object_id>\d+)/$', 'ad_detail', name='tasks-ad_detail'),
	url(r'^ad/(?P<object_id>\d+)/manage/$', 'ad_manage', name='tasks-ad_manage'),
	
	url(r'^classified/create/$', 'classified_create', name='tasks-classified_create'),

	# View reorder_tasks is only called by JQuery for drag/drop task ordering
	#url(r'^api/task/set_completed/$', 'api_task_set_completed', name='tasks-task_set_completed'),
	#url(r'^api/task/delete/$', 'api_task_delete', name='tasks-task_delete'),
	#url(r'^api/project/reorder_tasks/$', 'reorder_tasks', name="tasks-project_reorder_tasks"),
)

