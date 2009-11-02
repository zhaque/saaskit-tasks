from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import datetime

TASKS_LIST_TYPES = getattr(settings, 'TASKS_LIST_TYPES', ((0, 'None'),))

class IncompleteTaskManager(models.Manager):
	def get_query_set(self):
		return super(IncompleteTaskManager, self).get_query_set().filter(completed=0)

class Project(models.Model):
	name = models.CharField(max_length=60)
	slug = models.SlugField(max_length=60, blank=True)
	type = models.IntegerField(choices=TASKS_LIST_TYPES)
	#date_created = models.DateField(auto_now_add=True)

	def __unicode__(self):
		return self.name
		
	@property
	def incomplete_tasks(self):
		return self.tasks.filter(completed=False)
		
	def save(self):
		if not self.slug:
			self.slug = self.name
		super(Project, self).save()
		
	class Meta:
		ordering = ['name']
		verbose_name = getattr(settings, 'TASKS_PROJECT_NAME', 'Project')
		verbose_name_plural = getattr(settings, 'TASKS_PROJECT_NAME_PLURAL', verbose_name + 's')

		
class Task(models.Model):
	project = models.ForeignKey('Project', blank=True, null=True, related_name='tasks')
	
	name = models.CharField(max_length=140)
	description = models.TextField(blank=True)
	points = models.IntegerField(default=0)
	
	priority = models.PositiveIntegerField(max_length=3, default=0)
	completed = models.BooleanField()
	
	date_created = models.DateField(auto_now_add=True)
	date_due = models.DateField(blank=True,null=True)
	date_completed = models.DateField(blank=True,null=True)
	
	created_by = models.ForeignKey(User, related_name='created_by')
	assigned_to = models.ForeignKey(User, related_name='todo_assigned_to')
		
	# Custom manager lets us do things like Item.completed_tasks.all()
	objects = models.Manager()
	incomplete = IncompleteTaskManager()
	
	@property
	def is_overdue(self):
		return datetime.date.today() > self.due_date

	def __unicode__(self):
		return self.name
		
	def save(self):
		if self.completed and not self.date_completed:
			self.date_completed = datetime.datetime.now()
		super(Task, self).save()

	class Meta:
		ordering = ['priority']
		verbose_name = getattr(settings, 'TASKS_TASK_NAME', 'Task')
		verbose_name_plural = getattr(settings, 'TASKS_TASK_NAME_PLURAL', verbose_name + 's')

class Attachment(models.Model):
	user = models.ForeignKey(User)
	task = models.ForeignKey('Task', related_name='attachments')
	created_date = models.DateField(auto_now_add=True)
	file = models.FileField(upload_to='attachments/')
	
	def __unicode__(self):
		return self.file.name

#NOTE: I don't think I'm going to need this but I'll leave it for now
class Comment(models.Model):	
	"""
	Not using Django's built-in comments becase we want to be able to save 
	a comment and change task details at the same time. Rolling our own since it's easy.
	"""
	author = models.ForeignKey(User)
	task = models.ForeignKey('Task')
	date = models.DateTimeField(default=datetime.datetime.now)
	body = models.TextField(blank=True)
	
	def __unicode__(self):		
		return '%s - %s' % (
				self.author, 
				self.date, 
				)		
