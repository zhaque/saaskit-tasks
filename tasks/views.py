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
from prepaid.models import UnitPack
from .models import *
from .forms import *
from .util import render_to, serialize_to
from .conf import *
from .templatetags.activity_advertising import get_site_twitter_info
import datetime

# Need for links in email templates
current_site = Site.objects.get_current()

def _get_and_delete_form_data(request):
	if 'form-data' in request.session:
		data = request.session['form-data']
		del request.session['form-data']
		request.form_autosubmit = True
		return data

@render_to('tasks/expired.html')
def _activity_expired(request, object):
	return {'object':object}

@render_to('tasks/startpage.html')
def startpage(request):
	if request.method == 'POST' and 'activity' in request.POST:
		activity = request.POST['activity']
		request.session['form-data'] = dict(request.POST.items())
		return redirect('tasks-%s_create' % activity)
	else:
		f = {}
		f['task'] = AddTaskForm()
		f['ad'] = NewAdvertisementForm()
		f['classified'] = NewClassifiedForm()
		f['feed'] = NewFeedForm()
		return {'forms':f}

@render_to('tasks/profile.html')
def profile(request, username):
	user = get_or_create_twitter_user(username)
	info = user.twitter_profile
	return {'profile':user, 'info':info}

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

######################################
#             Activities             #
######################################

@login_required
def activity_self_advertise(request, object_id):
	obj = get_object_or_404(Activity, pk=object_id, user=request.user, published=True).derived
	
	if request.method == 'POST':
		# Publish to user's twitter profile
		# obj.self_advertise()
		request.user.twitterprofile.api.set_status(obj.message)
		request.user.message_set.create(message='Posted to your twitter profile')
		
		obj.date_self_advertised = datetime.datetime.now()
		obj.save()
	
	return HttpResponseRedirect(obj.get_manage_url())
	
@login_required
def activity_site_advertise(request, object_id):
	obj = get_object_or_404(Activity, pk=object_id, user=request.user, published=True).derived
	
	if request.method == 'POST' and not obj.date_site_advertised:
		# Publish to site's twitter profile
		# obj.site_advertise()
		site_twitter = get_site_twitter_info(obj)
		cost = site_twitter['cost']
		need = cost - UnitPack.get_user_credits(request.user)
		if need <= 0:
			msg = 'Posted to %s\'s twitter profile' % site_twitter['user']
			global_tweet(obj.message)
			if cost > 0:
				UnitPack.consume(request.user, cost, reason=msg)
			request.user.message_set.create(message=msg)
			obj.date_site_advertised = datetime.datetime.now()
			obj.save()
		else:
			request.user.message_set.create(message='Sorry, you need %s more points' % need)
				
	return HttpResponseRedirect(obj.get_manage_url())

######################################
#                Tasks               #
######################################

@render_to('tasks/task_list.html')
def task_index(request):
	tags = request.GET.get('tags')
	if tags:
		objects = Task.tagged.with_all(tags)
	else:
		objects = Task.objects.filter(published=True)
	return {'tasks':objects, 'cloud':Task.tags.cloud()}

@render_to('tasks/task/create.html')
@login_required
def task_create(request):
	form_class = AddTaskForm
	
	if request.method == 'POST':
		form = form_class(request.POST, request.FILES)
		
		if form.is_valid():
			budget = form.cleaned_data['budget']
			if budget > UnitPack.get_user_credits(request.user):
				form.errors['budget'] = ['Your budget cannot be higher than your current points']
			else:
				task = form.save(commit=False)
				task.user = request.user
				task.budget = budget
				task.save()
				task.tags = form.cleaned_data['tags']
				if form.cleaned_data['attachment']:
					task.attach(form.cleaned_data['attachment'])
				if task.budget > 0:
					UnitPack.consume(request.user, budget, reason=BUDGET_REASON % {'task':task.name})
				return redirect('tasks-task_setup', task.id)
	else:
		form = form_class(initial=_get_and_delete_form_data(request))
	return {'form':form}
	
@render_to('tasks/task/setup.html')
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
		form = form_class(request, request.POST, request.FILES, initial={'task':task.id, 'type':typ, 'raw_data':'{}'})
		if form.is_valid():
			form.save()
			return redirect('tasks-task_setup', task.id)
	else:
		form = form_class(request, initial={'task':task.id, 'type':typ, 'raw_data':'{}'})
	return locals()

@render_to('tasks/task/detail.html')
def task_detail(request, object_id):
	task = get_object_or_404(Task, pk=object_id, published=True)
	if task.is_expired():
		return _activity_expired(request, task)
	started = completed = None
	remaining = 0
	if request.user.is_authenticated():
		completed = request.user.achievements.filter(task=task, complete=True)
		remaining = task.get_chances_remaining(request.user)
		try:
			started = request.user.achievements.get(task=task, complete=False)
		except Achievement.DoesNotExist:
			pass
	return {'object':task, 'data':task.data, 'started':started, 'completed':completed, 'remaining':remaining}
	
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
	if task.is_expired():
		return _activity_expired(request, task)
	
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
	object = get_object_or_404(Task, pk=object_id, user=request.user, published=True)
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
			return redirect('tasks-ad_manage', ad.id)
	else:
		form = NewAdvertisementForm(initial=_get_and_delete_form_data(request))
	return locals()
	
def ad_detail(request, object_id):
	ad = get_object_or_404(Advertisement, pk=object_id)
	if ad.is_expired():
		return _activity_expired(request, ad)
	else:
		ad.views += 1
		ad.save()
		return HttpResponseRedirect(ad.url)
	
@render_to('tasks/ad/manage.html')
@login_required
@oauth_required
def ad_manage(request, object_id):
	ad = get_object_or_404(Advertisement, pk=object_id, user=request.user)
	return {'object':ad}
	"""
	if request.method == 'POST':
		if request.POST.get('global'):
			site_twitter = get_site_twitter_info(ad)
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
	"""
	
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
		form = NewClassifiedForm(request.POST, request.FILES)
		if form.is_valid():
			obj = form.save(commit=False)
			obj.user = request.user
			obj.published = True
			obj.save()
			obj.tags = form.cleaned_data['tags']
			if form.cleaned_data['attachment']:
				obj.attach(form.cleaned_data['attachment'])
			return redirect('tasks-home')
	else:
		form = NewClassifiedForm(initial=_get_and_delete_form_data(request))
	return locals()
	
######################################
#           Feeds/Entries            #
######################################

def feed_detail(request, object_id):
	object = get_object_or_404(Feed, pk=object_id)
	return HttpResponseRedirect(object.url)
	
@render_to('tasks/feed/manage.html')
def feed_manage(request, object_id):
	object = get_object_or_404(Feed, pk=object_id)
	return locals()
	
@render_to('tasks/feed/create.html')
@login_required
def feed_create(request):
	if request.method == 'POST':
		form = NewFeedForm(request.POST)
		if form.is_valid():
			obj = form.save(commit=False)
			obj.user = request.user
			obj.published = True
			obj.save()
			return redirect('tasks-feed_manage', obj.id)
	else:
		form = NewFeedForm(initial=_get_and_delete_form_data(request))
	return locals()
	
def entry_detail(request, object_id):
	obj = get_object_or_404(Entry, pk=object_id)
	obj.views += 1
	obj.save()
	return HttpResponseRedirect(obj.url)
	
