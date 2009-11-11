from django.db import models
from django import forms
from django.contrib.auth.models import User
from .models import *
from .util import serialize
import datetime

class TaskListViewForm(forms.Form):
	completed = forms.BooleanField(required=False)
	label = forms.ModelChoiceField(queryset=Project.objects.all(), required=False)

class AddProjectForm(forms.ModelForm):
	# slug = models.SlugField(widget=HiddenInput)
	# slug = forms.CharField(widget=forms.HiddenInput) 
	
	# The picklist showing allowable groups to which a new list can be added
	# determines which groups the user belongs to. This queries the form object
	# to derive that list.
	
	def __init__(self, request, *args, **kwargs):
		super(AddProjectForm, self).__init__(*args, **kwargs)

	class Meta:
		model = Project
		exclude = ('slug','user')
		
 
class NewAdvertisementForm(forms.ModelForm):
	class Meta:
		model = Advertisement
		exclude = ('published','labels', 'user','date_completed','completed','views')
 
class NewClassifiedForm(forms.ModelForm):
	class Meta:
		model = Classified
		exclude = ('published','location','zip','labels', 'user','date_completed','completed','views')
		
class AddTaskForm(forms.ModelForm):
	date_due = forms.DateField(label='End Date',
					required=False,
					widget=forms.DateTimeInput(attrs={'class':'due_date_picker'})
					)
					
	name = forms.CharField(
					widget=forms.widgets.TextInput(attrs={'size':35})
					)
		
	class Meta:
		model = Task
		exclude = ('labels','views', 'user','initial_budget', 'priority', 'published', 'completed', 'description', 'raw_data', 'date_completed')
		
		
class NewPollTaskForm(AddTaskForm):
	question = forms.CharField()
	answers = forms.CharField(help_text='One answer per line.', widget=forms.Textarea)
	multiple = forms.BooleanField(label='Allow Multiple Answers?', required=False)
	
	def save(self, commit=True, *args, **kwargs):
		obj = super(NewPollTaskForm, self).save(commit=commit)
		d = {}
		d['question'] = self.cleaned_data['question']
		d['multiple'] = self.cleaned_data['multiple']
		d['answers'] = []
		for line in self.cleaned_data['answers'].splitlines():
			line = line.strip()
			if not line:
				continue
			d['answers'].append({'text':line, 'count':0})
		obj.data = d
		if commit:
			obj.save()
		return obj
		
class NewQuizTaskForm(AddTaskForm):
	question = forms.CharField()
	answers = forms.CharField(help_text='One answer per line. Begin the correct answer with an asterisk *', widget=forms.Textarea)
	
	def clean_answers(self):
		for line in self.cleaned_data['answers'].splitlines():
			if line.strip().startswith('*'):
				break
		else:
			raise forms.ValidationError('You must start the correct answer with an asterisk *')
		return self.cleaned_data['answers']
	
	def save(self, commit=True, *args, **kwargs):
		obj = super(NewQuizTaskForm, self).save(commit=commit)
		d = {}
		d['question'] = self.cleaned_data['question']
		d['answers'] = []
		lines = self.cleaned_data['answers'].splitlines()
		for i, line in zip(range(len(lines)), lines):
			line = line.strip()
			if not line:
				continue
			if line.startswith('*'):
				d['answer'] = i
				line = line[1:]
			d['answers'].append({'text':line, 'count':0})
		obj.data = d
		if commit:
			obj.save()
		return obj
		
class NewPostTaskForm(AddTaskForm):
	service = forms.ChoiceField(choices=[('twitter','twitter')])
	message = forms.CharField(widget=forms.Textarea)
	
	def save(self, commit=True, *args, **kwargs):
		obj = super(NewPostTaskForm, self).save(commit=commit)
		d = {}
		d['service'] = self.cleaned_data['service']
		d['message'] = self.cleaned_data['message']
		obj.data = d
		if commit:
			obj.save()
		return obj
		
class NewQuestionTaskForm(AddTaskForm):
	question = forms.CharField()
	length = forms.ChoiceField(label='Answer Length', choices=[(i,i) for i in ('short','medium', 'long')])
	
	def save(self, commit=True, *args, **kwargs):
		obj = super(NewQuestionTaskForm, self).save(commit=commit)
		d = {}
		d['question'] = self.cleaned_data['question']
		d['length'] = self.cleaned_data['length']
		d['answers'] = []
		obj.data = d
		if commit:
			obj.save()
		return obj


class EditItemForm(forms.ModelForm):

	class Meta:
		model = Task		



class NewTaskQuestionForm(forms.ModelForm):
	task = forms.ModelChoiceField(queryset=Task.objects.filter(published=False), widget=forms.HiddenInput)
	raw_data = forms.CharField(widget=forms.HiddenInput)
	type = forms.CharField(widget=forms.HiddenInput)
	
	def __init__(self, request, *args, **kargs):
		super(NewTaskQuestionForm, self).__init__(*args, **kargs)
		self['task'].field.queryset = self['task'].field.queryset.filter(user=request.user)
	
	class Meta:
		model = TaskQuestion
		
class NewTaskQuestionPollForm(NewTaskQuestionForm):
	question = forms.CharField()
	answers = forms.CharField(help_text='One answer per line.', widget=forms.Textarea)
	multiple = forms.BooleanField(label='Allow Multiple Answers?', required=False)
	
	def clean(self):
		d = {}
		d['question'] = self.cleaned_data['question']
		d['multiple'] = self.cleaned_data['multiple']
		d['answers'] = []
		for line in self.cleaned_data['answers'].splitlines():
			line = line.strip()
			if not line:
				continue
			d['answers'].append({'text':line, 'count':0})
		self.cleaned_data['raw_data'] = serialize(d)
		return self.cleaned_data

class NewTaskQuestionEssayForm(NewTaskQuestionForm):
	question = forms.CharField()
	length = forms.ChoiceField(label='Answer Length', choices=[(i,i) for i in ('short','medium', 'long')])
	
	def clean(self):
		d = {}
		d['question'] = self.cleaned_data['question']
		d['length'] = self.cleaned_data['length']
		d['answers'] = []
		self.cleaned_data['raw_data'] = serialize(d)
		return self.cleaned_data
