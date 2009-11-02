from django.db import models
from django import forms
from django.contrib.auth.models import User
from .models import Project,Task
import datetime

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
		exclude = ('slug',)
		
 
		
class AddTaskForm(forms.ModelForm):
	date_due = forms.DateField(
					required=False,
					widget=forms.DateTimeInput(attrs={'class':'due_date_picker'})
					)
					
	name = forms.CharField(
					widget=forms.widgets.TextInput(attrs={'size':35})
					)
					
	type = forms.IntegerField(widget=forms.HiddenInput)
					
	project = forms.ModelChoiceField(queryset=Project.objects.all(), widget=forms.HiddenInput)

	# The picklist showing the users to which a new task can be assigned
	# must find other members of the groups the current list belongs to.
	def __init__(self, *args, **kwargs):
		super(AddTaskForm, self).__init__(*args, **kwargs)
		# print dir(self.fields['list'])
		# print self.fields['list'].initial
		
	class Meta:
		model = Task
		exclude = ('priority', 'completed', 'description', 'raw_data', 'date_completed')
		
class NewPollTaskForm(AddTaskForm):
	question = forms.CharField()
	answers = forms.CharField(help_text='One answer per line.', widget=forms.Textarea)
	
	def save(self, *args, **kwargs):
		obj = super(NewPollTaskForm, self).save(commit=False)
		d = {}
		d['question'] = self.cleaned_data['question']
		d['answers'] = []
		for line in self.cleaned_data['answers'].splitlines():
			line = line.strip()
			if not line:
				continue
			d['answers'].append({'text':line, 'count':0})
		obj.data = d
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
	
	def save(self, *args, **kwargs):
		obj = super(NewQuizTaskForm, self).save(commit=False)
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
		obj.save()
		return obj
		
class NewPostTaskForm(AddTaskForm):
	service = forms.ChoiceField(choices=[('twitter','twitter')])
	message = forms.CharField(widget=forms.Textarea)
	
	def save(self, *args, **kwargs):
		obj = super(NewPostTaskForm, self).save(commit=False)
		d = {}
		d['service'] = self.cleaned_data['service']
		d['message'] = self.cleaned_data['message']
		obj.data = d
		obj.save()
		return obj


class EditItemForm(forms.ModelForm):

	class Meta:
		model = Task		
