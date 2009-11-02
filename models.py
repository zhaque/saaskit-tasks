from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import datetime
from .util import serialize, deserialize

TASKS_LIST_TYPES = getattr(settings, 'TASKS_LIST_TYPES', ((0, 'None'),))

class TaskType:
	POLL = 1
	QUIZ = 2
	POST = 3

TASK_TYPES = (
	(TaskType.POLL, 'poll'),
	(TaskType.QUIZ, 'quiz'),
	(TaskType.POST, 'post'),
)

class IncompleteTaskManager(models.Manager):
	def get_query_set(self):
		return super(IncompleteTaskManager, self).get_query_set().filter(completed=0)

class Project(models.Model):
	name = models.CharField(max_length=60)
	slug = models.SlugField(max_length=60, blank=True)
	type = models.IntegerField(choices=TASKS_LIST_TYPES)
	#date_created = models.DateTimeField(auto_now_add=True)

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
	type = models.IntegerField(choices=TASK_TYPES)
	
	points = models.IntegerField(default=0)
	max_points = models.IntegerField(default=0)
	
	limit = models.IntegerField(default=100)
	limit_per_user = models.IntegerField(default=1)
	
	reserve_time = models.IntegerField(help_text='in minutes', default=5)
	
	priority = models.PositiveIntegerField(max_length=3, default=0)
	#active = models.BooleanField(default=True)
	completed = models.BooleanField(default=False)
	
	date_created = models.DateTimeField(auto_now_add=True)
	date_due = models.DateTimeField(blank=True,null=True)
	date_completed = models.DateTimeField(blank=True,null=True)
		
	# Custom manager lets us do things like Item.completed_tasks.all()
	objects = models.Manager()
	incomplete = IncompleteTaskManager()
	
	raw_data = models.TextField(default='{}')
	
	def get_data(self):
		return deserialize(self.raw_data)
		
	def set_data(self, v):
		self.raw_data = serialize(v)
	
	data = property(get_data, set_data)
	
	def get_chances_remaining(self, user=None):
		r = self.limit - self.achievements.count()
		if user:
			ur = self.limit_per_user - self.achievements.filter(user=user).count()
			return min(r, ur)
		return r
	
	@property
	def summary(self):
		r = self.get_type_display()
		rl = r.lower()
		if rl in ['poll','quiz']:
			r += u': %s' % self.data['question']
		elif rl == 'post':
			r += u': %s' % self.data['service']
		return r
	
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
	created_date = models.DateTimeField(auto_now_add=True)
	file = models.FileField(upload_to='attachments/')
	
	def __unicode__(self):
		return self.file.name
		
class Achievement(models.Model):
	user = models.ForeignKey(User, related_name='achievements')
	task = models.ForeignKey('Task', related_name='achievements')
	date_started = models.DateTimeField(auto_now_add=True)
	complete = models.BooleanField(default=False)
	
	def __unicode__(self):
		return self.task.name
		
	@property
	def is_expired(self):
		return self.date_started > datetime.datetime.now() + datetime.timedelta(minutes=self.task.reserve_time)

#NOTE: I don't think I'm going to need this but I'll leave it for now
class Comment(models.Model):	
	"""
	Not using Django's built-in comments becase we want to be able to save 
	a comment and change task details at the same time. Rolling our own since it's easy.
	"""
	author = models.ForeignKey(User)
	task = models.ForeignKey('Task')
	date = models.DateTimeField(auto_now_add=True)
	body = models.TextField(blank=True)
	
	def __unicode__(self):		
		return '%s - %s' % (
				self.author, 
				self.date, 
				)		
