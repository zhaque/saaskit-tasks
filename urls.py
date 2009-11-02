from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.contrib.auth import views as auth_views

urlpatterns = patterns('tasks.views',
	url(r'^$', 'project_list', name='todo-lists'),
	url(r'^mine/$', 'project_detail', {}, name="todo-mine"),
	url(r'^task/new/$', 'task_new', name='tasks-task_new'),
	url(r'^task/(?P<object_id>\d{1,6})/$', 'task_edit', name='todo-task_detail'),
	url(r'^project/(?P<object_id>\d{1,4})/$', 'project_detail', name='todo-incomplete_tasks'),
	url(r'^project/(?P<object_id>\d{1,4})/completed/$', 'project_detail', {'view_completed':1}, name='todo-completed_tasks'),    
	url(r'^project/(?P<object_id>\d{1,4})/delete/$', 'project_delete', name="todo-del_list"),

	# View reorder_tasks is only called by JQuery for drag/drop task ordering
	url(r'^api/task/set_completed/$', 'api_task_set_completed', name='tasks-task_set_completed'),
	url(r'^api/task/delete/$', 'api_task_delete', name='tasks-task_delete'),
	url(r'^api/project/reorder_tasks/$', 'reorder_tasks', name="todo-reorder_tasks"),
)

