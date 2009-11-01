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
		
 
		
class AddItemForm(forms.ModelForm):
	date_due = forms.DateField(
					required=False,
					widget=forms.DateTimeInput(attrs={'class':'due_date_picker'})
					)
					
	name = forms.CharField(
					widget=forms.widgets.TextInput(attrs={'size':35})
					) 

	# The picklist showing the users to which a new task can be assigned
	# must find other members of the groups the current list belongs to.
	def __init__(self, *args, **kwargs):
		super(AddItemForm, self).__init__(*args, **kwargs)
		# print dir(self.fields['list'])
		# print self.fields['list'].initial
		
	class Meta:
		model = Task
		exclude = ('points',)
		


class EditItemForm(forms.ModelForm):

	class Meta:
		model = Task		
