from django import forms 
from django.shortcuts import render_to_response
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.contrib import auth
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from .models import Task, Project, Comment, Attachment
from .forms import AddProjectForm, AddItemForm, EditItemForm
from .util import render_to, redirect_to, serialize_to
import datetime

# Need for links in email templates
current_site = Site.objects.get_current() 


@render_to('tasks/project_list.html')
@login_required
def project_list(request):	
	if request.method == 'POST':
		form = AddProjectForm(request,request.POST)
		if form.is_valid():
			try:
				obj = form.save()
				request.user.message_set.create(message=u'%s created: %s' % (obj.get_type_display(), obj.name))
				return HttpResponseRedirect(request.path)
			except IntegrityError:
				request.user.message_set.create(message="There was a problem saving the new list.")
			
	else:
		form = AddProjectForm(request)
			
	projects = Project.objects.all().order_by('name')
	task_count = Task.incomplete.count()
	
	return {'form':form, 'list_list':projects, 'list_count':projects.count(), 'item_count':task_count}
	

@render_to('tasks/project_delete.html')
@login_required
def project_delete(request, object_id):

	"""
	Delete an entire list. Danger Will Robinson! Only staff members should be allowed to access this view.
	"""
	
	if request.user.is_staff:
		can_del = 1

	# Get this list's object (to derive list.name, list.id, etc.)
	project = get_object_or_404(Project, pk=object_id)

	# If delete confirmation is in the POST, delete all items in the list, then kill the list itself
	if request.method == 'POST':
		# Kill the project
		project.tasks.all().delete()
		project.delete()
		
		# A var to send to the template so we can show the right thing
		list_killed = 1
		
		return redirect_to('tasks-index')
	else:
		item_count_done = Task.objects.filter(project=project.id,completed=1).count()
		item_count_undone = Task.objects.filter(project=project.id,completed=0).count()
		item_count_total = Task.objects.filter(project=project.id).count()	
	
	return locals()


@render_to('tasks/project_detail.html')
@login_required
def project_detail(request, object_id = 0, view_completed=0):
	# TODO: check if user has permission
		
	# First check for items in the mark_done POST array. If present, change
	# their status to complete.
	if request.POST.getlist('mark_done'):
		done_items = request.POST.getlist('mark_done')
		# Iterate through array of done items and update its representation in the model
		for thisitem in done_items:
			p = Task.objects.get(id=thisitem)
			p.completed = 1
			p.completed_date = datetime.datetime.now()
			p.save()
			request.user.message_set.create(message="Task \"%s\" marked complete." % p.title )


	# Undo: Set completed items back to incomplete
	if request.POST.getlist('undo_completed_task'):
		undone_items = request.POST.getlist('undo_completed_task')
		for thisitem in undone_items:
			p = Task.objects.get(id=thisitem)
			p.completed = 0
			p.save()
			request.user.message_set.create(message="Previously completed task \"%s\" marked incomplete." % p.title)			


	# And delete any requested items
	if request.POST.getlist('del_task'):
		deleted_items = request.POST.getlist('del_task')
		for thisitem in deleted_items:
			p = Task.objects.get(id=thisitem)
			p.delete()
			request.user.message_set.create(message="Task \"%s\" deleted." % p.title )

	# And delete any *already completed* items
	if request.POST.getlist('del_completed_task'):
		deleted_items = request.POST.getlist('del_completed_task')
		for thisitem in deleted_items:
			p = Task.objects.get(id=thisitem)
			p.delete()
			request.user.message_set.create(message="Deleted previously completed item \"%s\"."  % p.title)


	thedate = datetime.datetime.now()
	created_date = "%s-%s-%s" % (thedate.year, thedate.month, thedate.day)

	if object_id:
		project = get_object_or_404(Project, pk = object_id)
		task_list = Task.objects.filter(project=project, completed=0)
		completed_list = Task.objects.filter(project=project, completed=1)
		
	else:
		task_list = Task.objects.filter(assigned_to=request.user, completed=0)
		completed_list = Task.objects.filter(assigned_to=request.user, completed=1)

	if request.POST.getlist('add_task') :
		form = AddItemForm(request.POST,initial={
		'assigned_to':request.user.id,
		'priority':999,
		'project':project.id,
		})
		
		if form.is_valid():
			# Save task first so we have a db object to play with
			new_task = form.save()

			# Send email alert only if the Notify checkbox is checked AND the assignee is not the same as the submittor
			# Email subect and body format are handled by templates
			if "notify" in request.POST :
				if new_task.assigned_to != request.user :
										
					# Send email
					email_subject = render_to_string("todo/email/assigned_subject.txt", { 'task': new_task })					
					email_body = render_to_string("todo/email/assigned_body.txt", { 'task': new_task, 'site': current_site, })
					try:
						send_mail(email_subject, email_body, new_task.created_by.email, [new_task.assigned_to.email], fail_silently=False)
					except:
						request.user.message_set.create(message="Task saved but mail not sent. Contact your administrator." )

			request.user.message_set.create(message="New task \"%s\" has been added." % new_task.name )
			return HttpResponseRedirect(request.path)

	else:
		#if object_id: # We don't allow adding a task on the "mine" view
		form = AddItemForm(initial={
			'assigned_to':request.user.id,
			'priority':999,
			'project':project.id,
			} )

	if request.user.is_staff:
		can_del = 1
		
	list = project
	listid = list.id
	auth_ok = 1
	list_slug = 'null'
	return locals()

@serialize_to
@login_required
def task_new(request):
	if request.method == 'POST':
		form = AddItemForm(request.POST)
		
		if form.is_valid():
			# Save task first so we have a db object to play with
			new_task = form.save()

			#if request.is_ajax():
			return {'task':new_task}
			#else:
			#	msg = "Task added to %s: %s" % (new_task.project and ' to %s' % new_task.project.name or '', new_task.name)
			#	request.user.message_set.create(message=msg)
			#	return HttpResponseRedirect(request.path)
		
		else:
			form = AddItemForm()
	#if request.is_ajax():
	return HttpResponse('Invalid Request')
	#else:
	#	return HttpResponseRedirect(request.path)

@render_to('tasks/task_detail.html')
def task_detail(request, object_id):
	task = get_object_or_404(Task, pk=object_id)
	return {'task':task, 'data':task.data, 'template':'tasks/overview/%s.html' % task.get_type_display().lower()}
	
@render_to('tasks/task_do.html')
@login_required
def task_do(request, object_id):
	task = get_object_or_404(Task, pk=object_id)
	if request.method == 'POST':
		try:
			typ = task.get_type_display().lower()
			if typ == 'poll':
				choice = int(request.POST['choice'])
			return redirect_to('tasks-task_detail', task.id)
		except KeyError, e:
			request.user.message_set.create(message='Error: Please complete all required fields')
	else:
		pass #TODO: Reserve place
	return {'task':task, 'data':task.data, 'template':'tasks/form/%s.html' % task.get_type_display().lower()}
	
@render_to('tasks/task_edit.html')
@login_required
def task_edit(request, object_id):
	task = get_object_or_404(Task, pk=object_id)
	
	if request.method == 'POST' and 'attachment' in request.FILES:
		file = request.FILES['attachment']
		a = Attachment()
		a.user = request.user
		a.task = task
		a.file.save(file.name, file)
		a.save()
		request.user.message_set.create(message='Attachment saved')
		return HttpResponseRedirect(request.path)
		
	
	comment_list = Comment.objects.filter(task=object_id)
		
	# Before doing anything, make sure the accessing user has permission to view this item.
	# Admins can edit all tasks.

	if True: # TODO: check permission :request.user.is_staff:
		
		auth_ok = 1
		if request.POST:
			 form = EditItemForm(request.POST,instance=task)

			 if form.is_valid():
				 form.save()
				 
				 # Also save submitted comment, if non-empty
				 if request.POST['comment-body']:
					 c = Comment(
						 author=request.user, 
						 task=task,
						 body=request.POST['comment-body'],
					 )
					 c.save()
				 
				 request.user.message_set.create(message="The task has been edited.")
				 return HttpResponseRedirect(reverse('tasks-project_incomplete_tasks', args=[task.list.id, task.list.slug]))
				 
		else:
			form = EditItemForm(instance=task)
			thedate = task.date_due
			

	else:
		request.user.message_set.create(message="You do not have permission to view/edit this task.")

	return locals()


######################################
#             Ajax Views             #
######################################

# @login_required
def reorder_tasks(request):
	"""
	Handle task re-ordering (priorities) from JQuery drag/drop in view_list.html
	"""

	newtasklist = request.POST.getlist('tasktable[]')
	# First item in received list is always empty - remove it
	del newtasklist[0]
	
	# Items arrive in order, so all we need to do is increment up from one, saving
	# "i" as the new priority for the current object.
	i = 1
	for t in newtasklist:
		newitem = Task.objects.get(pk=t)
		newitem.priority = i
		newitem.save()
		i = i + 1
	
	# All views must return an httpresponse of some kind ... without this we get 
	# error 500s in the log even though things look peachy in the browser.	
	return HttpResponse(status=201)
		
@serialize_to
def api_task_set_completed(request):
	if request.method == 'POST':
		task = get_object_or_404(Task, pk=request.POST['task_id'])
		# TODO: check permission
		task.completed = bool(int(request.POST['completed']))
		task.save()
		return {'task':task}

@serialize_to
def api_task_delete(request):
	if request.method == 'POST':
		task = get_object_or_404(Task, pk=request.POST['task_id'])
		# TODO: check permission
		id = task.id
		task.delete()
		return {'task':{'id':id}}
