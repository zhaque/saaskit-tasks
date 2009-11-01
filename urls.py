from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from django.contrib.auth import views as auth_views

urlpatterns = patterns('tasks.views',
    url(r'^mine/$', 'view_list',{'list_slug':'mine'},name="todo-mine"),
    url(r'^(?P<list_id>\d{1,4})/(?P<list_slug>[\w-]+)/delete$', 'del_list',name="todo-del_list"),
    url(r'^task/(?P<task_id>\d{1,6})$', 'view_task', name='todo-task_detail'),
    url(r'^(?P<list_id>\d{1,4})/(?P<list_slug>[\w-]+)$', 'view_list', name='todo-incomplete_tasks'),
    url(r'^(?P<list_id>\d{1,4})/(?P<list_slug>[\w-]+)/completed$', 'view_list', {'view_completed':1},name='todo-completed_tasks'),    
    url(r'^$', 'list_lists',name="todo-lists"),
    
    # View reorder_tasks is only called by JQuery for drag/drop task ordering
    url(r'^reorder_tasks/$', 'reorder_tasks',name="todo-reorder_tasks"),
)

