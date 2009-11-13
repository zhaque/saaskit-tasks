from django import forms 
from django.shortcuts import render_to_response
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.contrib import auth
from django.template import RequestContext
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from twitter_app.decorators import oauth_required
from twitter_app.utils import get_site_twitter_user, get_or_create_twitter_user
from twitter_app.tweet import global_tweet
from twitter_app import twython
from prepaid.models import UnitPack
from .models import *
from .forms import *
from .util import render_to, serialize_to
from .conf import *
import datetime

# Need for links in email templates
current_site = Site.objects.get_current()

def _get_site_twitter_info(activity):
	r = {}
	r['user'] = get_site_twitter_user()
	r['followers'] = r['user'].twitter_profile['followers_count']
	r['cost_fixed'] = SITE_TWEET_COST_FIXED[activity]
	r['cost_variable'] = SITE_TWEET_COST_VARIABLE[activity]
	r['cost'] = r['cost_fixed'] + r['cost_variable'] * r['followers']
	return r

@render_to('tasks/profile.html')
def profile(request, username):
	user = get_or_create_twitter_user(username)
	info = user.twitter_profile
	return {'profile':user, 'info':info}

@render_to('tasks/project_list.html')
@login_required
def project_list(request):	
	if request.method == 'POST':
		form = AddProjectForm(request,request.POST)
		if form.is_valid():
			try:
				obj = form.save(commit=False)
				obj.user = request.user
				obj.save()
				request.user.message_set.create(message=u'%s created: %s' % (obj.get_type_display(), obj.name))
				return HttpResponseRedirect(request.path)
			except IntegrityError:
				request.user.message_set.create(message="There was a problem saving the new list.")
			
	else:
		form = AddProjectForm(request)
			
	projects = Project.objects.filter(user=request.user).order_by('name')
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
		
		return redirect('tasks-index')
	else:
		item_count_done = Task.objects.filter(project=project.id,completed=1).count()
		item_count_undone = Task.objects.filter(project=project.id,completed=0).count()
		item_count_total = Task.objects.filter(project=project.id).count()
	
	return locals()

@render_to('tasks/control_task_list.html')
@login_required
def control_task_list(request):
	form = TaskListViewForm(request.GET, initial={'completed':False})
	form.is_valid()
	view = form.cleaned_data
	
	tasks = Activity.objects.filter(user=request.user)
	
	if view['completed']:
		tasks = tasks.filter(completed=True)
	else:
		tasks = tasks.filter(completed=False)
		
	if view['label']:
		tasks &= view['label'].activities.all()
		
	return {'tasks':tasks, 'view':view}

@render_to('tasks/project_detail.html')
@login_required
def project_detail(request, object_id = None, view_completed=0):
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
		project = None
		task_list = Task.objects.filter(user=request.user, completed=0)
		completed_list = Task.objects.filter(user=request.user, completed=1)

	if request.POST.getlist('add_task') :
		form = AddTaskForm(request.POST,initial={
		'assigned_to':request.user.id,
		'priority':999,
		'project':object_id,
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
		form = AddTaskForm(initial={
			'assigned_to':request.user.id,
			'priority':999,
			'project':object_id,
			} )

	if request.user.is_staff:
		can_del = 1
		
	list = project
	listid = object_id
	auth_ok = 1
	list_slug = 'null'
	
	return locals()
	
@render_to('tasks/task_list.html')
def task_index(request):
	return {'tasks':Task.objects.filter(published=True)}

@render_to('tasks/task_create.html')
@login_required
def task_create(request):
	form_class = AddTaskForm
	try:
		typ = int(request.REQUEST['type'])
		
		if typ == TaskType.POLL:
			form_class = NewPollTaskForm
			
		elif typ == TaskType.QUIZ:
			form_class = NewQuizTaskForm
			
		elif typ == TaskType.POST:
			form_class = NewPostTaskForm
			
		elif typ == TaskType.QUESTION:
			form_class = NewQuestionTaskForm
	except:
		pass
	
	if request.method == 'POST':
		form = form_class(request.POST)
		
		if form.is_valid():
			budget = form.cleaned_data['budget']
			if budget > UnitPack.get_user_credits(request.user):
				form.errors['budget'] = ['Your budget cannot be higher than your current points']
			else:
				task = form.save(commit=False)
				task.user = request.user
				task.budget = budget
				task.save()
				if task.budget > 0:
					UnitPack.consume(request.user, budget, reason=BUDGET_REASON % {'task':task.name})
				return redirect('tasks-task_setup', task.id)
	else:
		form = form_class()
	return {'form':form}
	
@render_to('tasks/task_setup.html')
@login_required
def task_setup(request, object_id):
	task = get_object_or_404(Task, pk=object_id, user=request.user, published=False)
	if request.method == 'POST':
		if task.questions.count() >= 1:
			task.published = True
			task.save()
			return redirect('tasks-task_manage', task.id)
		else:
			request.user.message_set.create(message='You must add at least one question')
	return locals()
	
@render_to('tasks/task/question_add.html')
@login_required
def task_question_add(request, object_id):
	task = get_object_or_404(Task, pk=object_id, user=request.user, published=False)
	forms = {
		'poll':NewTaskQuestionPollForm,
		#'quiz':NewQuizTaskForm,
		'text':NewTaskQuestionEssayForm,
	}
	typ = request.REQUEST['type']
	form_class = forms[typ]
	if request.method == 'POST':
		form = form_class(request, request.POST, initial={'task':task.id, 'type':typ, 'raw_data':'{}'})
		if form.is_valid():
			form.save()
			return redirect('tasks-task_setup', task.id)
	else:
		form = form_class(request, initial={'task':task.id, 'type':typ, 'raw_data':'{}'})
	return locals()

@serialize_to
@login_required
def task_new(request):
	if request.method == 'POST':
		form = AddTaskForm(request.POST)
		
		if form.is_valid():
			# Save task first so we have a db object to play with
			task = form.save()
			
			d = {}
			
			# TODO: extra fields for configuring tasks
			tt = task.type
			if tt in [TaskType.POLL, TaskType.QUIZ]:
				d['question'] = 'What is the answer to life, the universe, and everything?'
				d['answers'] = [{'text':'Pizza','count':0}, {'text':'42', 'count':0}, {'text':'I simply haven\'t a clue', 'count':0}]
			elif tt == TaskType.POST:
				d['service'] = 'twitter'
				d['message'] = 'Tweet! Tweet! Tweet!'
				
			task.data = d
			task.save()
				

			#if request.is_ajax():
			return {'task':task}
			#else:
			#	msg = "Task added to %s: %s" % (new_task.project and ' to %s' % new_task.project.name or '', new_task.name)
			#	request.user.message_set.create(message=msg)
			#	return HttpResponseRedirect(request.path)
		
		else:
			form = AddTaskForm()
	#if request.is_ajax():
	return HttpResponse('Invalid Request')
	#else:
	#	return HttpResponseRedirect(request.path)

@render_to('tasks/task_detail.html')
def task_detail(request, object_id):
	task = get_object_or_404(Task, pk=object_id, published=True)
	started = completed = None
	remaining = 0
	if request.user.is_authenticated():
		completed = request.user.achievements.filter(task=task, complete=True)
		remaining = task.get_chances_remaining(request.user)
		try:
			started = request.user.achievements.get(task=task, complete=False)
		except Achievement.DoesNotExist:
			pass
	return {'task':task, 'data':task.data, 'started':started, 'completed':completed, 'remaining':remaining}
	
@render_to()
@login_required
def task_stats(request, object_id):
	task = get_object_or_404(Task, pk=object_id, user=request.user)
	# TODO: permission
	return {'task':task, 'data':task.data, 'template':'tasks/stats/%s.html' % task.get_type_display().lower()}
	
@render_to('tasks/task/do.html')
@login_required
@oauth_required
def task_do(request, object_id):
	task = get_object_or_404(Task, pk=object_id, published=True)
	
	# Create or retrieve achievement
	achievement = None
	remaining = task.get_chances_remaining(request.user)
	try:
		achievement = Achievement.objects.get(user=request.user, task=task, complete=False)
		if achievement.is_expired:
			# Reset achievement time as long as there is room on the waiting list
			if remaining > 0:
				achievement.date_started = datetime.datetime.now()
			else:
				request.user.message_set.create(message='Sorry, your time to complete this task has run out.')
				return redirect('tasks-task_detail', task.id)
	except Achievement.DoesNotExist:
		if remaining > 0:
			a = Achievement()
			a.task = task
			a.user = request.user
			a.save()
			achievement = a
			
	if not achievement:
		request.user.message_set.create(message='Sorry, you can\'t do that.')
	
	if request.method == 'POST':
		try:
			questions = task.questions.all()
			modified = []
			errors = []
			for form_id, question in zip(range(1, questions.count()+1), questions):
				typ = question.type
				data = question.data
				error = None
				if typ == 'poll':
					choices = map(int, request.POST.getlist('choice%s' % form_id))
					for choice in choices:
						data['answers'][choice]['count'] += 1
					
				elif typ == 'text':
					answer = request.POST['answer%s' % form_id].strip()
					if len(answer):
						data['answers'].append(answer)
					else:
						error = 'You must answer the question!'
				else:
					error = 'Invalid Task'
				"""
				elif typ == TaskType.QUIZ:
					choice = int(request.POST['choice'])
					if choice != data['answer']:
						error = 'Sorry, you answered incorrectly.'
					
				elif typ == TaskType.POST:
					request.twitter.set_status(data['message'])
				"""
				
					
				if error:
					errors.append(error)
					question.error = error
				else:
					question.data = data
				modified.append(question)
					
			if errors:
				# FIXME: Delete achievement and form if theres an error??
				# Maybe it should reload the form with info filled in somehow
				#achievement.delete()
				#return redirect('tasks-task_detail', task.id)
				return {'task':task, 'questions':modified}
			else:
				# No errors, yay!
				for m in modified:
					m.save()
				task.budget -= task.points
				task.save()
				
				achievement.complete = True
				achievement.save()
				if task.points > 0:
					UnitPack.credit(request.user, task.points, reason=COMPLETED_REASON % {'task':task.name})
					request.user.message_set.create(message='You earned %s points. How exciting!' % task.points)
				else:
					request.user.message_set.create(message='You didn\'t earn any points. But at least you had fun!')
				
				return redirect('tasks-task_detail', task.id)
			
		except KeyError, e:
			request.user.message_set.create(message='Error: Please complete all required fields')
		#except Exception, e:
		#	request.user.message_set.create(message='Error: Something went wrong, try again later')
	else:
		pass
	return {'task':task, 'questions':task.questions.all()}
	
@render_to('tasks/task/manage.html')
@login_required
def task_manage(request, object_id):
	task = get_object_or_404(Task, pk=object_id, user=request.user, published=True)
	return locals()
	
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
#                Ads                 #
######################################

@render_to('tasks/ad/create.html')
@login_required
def ad_create(request):
	if request.method == 'POST':
		form = NewAdvertisementForm(request.POST)
		if form.is_valid():
			ad = form.save(commit=False)
			ad.user = request.user
			ad.published = True
			ad.save()
			return redirect('tasks-home')
	else:
		form = NewAdvertisementForm()
	return locals()
	
def ad_detail(request, object_id):
	ad = get_object_or_404(Advertisement, pk=object_id)
	ad.views += 1
	ad.save()
	return HttpResponseRedirect(ad.url)
	
@render_to('tasks/ad/manage.html')
@login_required
@oauth_required
def ad_manage(request, object_id):
	ad = get_object_or_404(Advertisement, pk=object_id, user=request.user)
	site_twitter = _get_site_twitter_info('ad')
	
	if request.method == 'POST':
		if request.POST.get('global'):
			cost = site_twitter['cost']
			need = cost - UnitPack.get_user_credits(request.user)
			if need <= 0:
				msg = 'Posted to %s\'s twitter profile' % site_twitter['user']
				global_tweet(ad.message)
				if cost > 0:
					UnitPack.consume(request.user, cost, reason=msg)
				request.user.message_set.create(message=msg)
			else:
				request.user.message_set.create(message='Sorry, you need %s more points' % need)
		else:
			request.twitter.set_status(ad.message)
			request.user.message_set.create(message='Posted to your twitter profile')
		return redirect('tasks-ad_manage', ad.id)
		
	return locals()
	
######################################
#             Classifieds            #
######################################

@render_to('tasks/classified/detail.html')
def classified_detail(request, object_id):
	object = get_object_or_404(Classified, pk=object_id)
	return locals()
	
@render_to('tasks/classified/manage.html')
def classified_manage(request, object_id):
	object = get_object_or_404(Classified, pk=object_id)
	return locals()
	
@render_to('tasks/classified/create.html')
@login_required
def classified_create(request):
	if request.method == 'POST':
		form = NewClassifiedForm(request.POST)
		if form.is_valid():
			obj = form.save(commit=False)
			obj.user = request.user
			obj.published = True
			obj.save()
			return redirect('tasks-home')
	else:
		form = NewClassifiedForm()
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
@login_required
def api_task_delete(request):
	if request.method == 'POST':
		task = get_object_or_404(Task, pk=request.POST['task_id'])
		if request.user == task.user:
			id = task.id
			task.delete()
			if request.is_ajax():
				return {'task':{'id':id}}
	return redirect('tasks-projects')
