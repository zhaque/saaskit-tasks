from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
import datetime
from .util import serialize, deserialize, get_shorturl, random_string
from prepaid.models import UnitPack
from django.template.loader import get_template, Context
import tagging

TASKS_LIST_TYPES = getattr(settings, 'TASKS_LIST_TYPES', ((0, 'None'),))

class TaskType:
	POLL = 1
	QUIZ = 2
	POST = 3
	QUESTION = 4

TASK_TYPES = (
	(TaskType.POLL, 'poll'),
	(TaskType.QUIZ, 'quiz'),
	(TaskType.POST, 'post'),
	(TaskType.QUESTION, 'question'),
)

class CompleteObjectManager(models.Manager):
	def get_query_set(self):
		return super(CompleteObjectManager, self).get_query_set().filter(complete=True)


class IncompleteTaskManager(models.Manager):
	def get_query_set(self):
		return super(IncompleteTaskManager, self).get_query_set().filter(completed=0)

class Project(models.Model):
	user = models.ForeignKey(User, related_name='task_labels')
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
		
class Activity(models.Model):
	user = models.ForeignKey(User, related_name='activities', editable=False)
	
	name = models.CharField(max_length=140)
	views = models.IntegerField(default=0, editable=False)
	labels = models.ManyToManyField('Project', blank=True, related_name='activities', editable=False)
	
	published = models.BooleanField(default=False, editable=False)
	completed = models.BooleanField(default=False, editable=False)
	
	date_created = models.DateTimeField(auto_now_add=True)
	date_due = models.DateTimeField('End Date', blank=True,null=True)
	date_completed = models.DateTimeField(blank=True,null=True, editable=False)
	date_self_advertised = models.DateTimeField(blank=True, null=True, editable=False)
	date_site_advertised = models.DateTimeField(blank=True, null=True, editable=False)
	
	content_type = models.ForeignKey(ContentType, editable=False)
	derived = generic.GenericForeignKey(fk_field='id')
	
	def __unicode__(self):
		return unicode(self.derived)
	
	def attach(self, file):
		a = Attachment()
		a.activity = self
		a.file.save(random_string(15), file)
		if hasattr(file, 'name'):
			a.original_filename = file.name
		a.save()
		return a
	attach.alters_data = True
		
	def get_manage_url(self):
		return '%smanage/' % self.derived.get_absolute_url()
			
	def save(self, *args, **kargs):
		if self.__class__ != Activity:
			self.content_type = ContentType.objects.get_for_model(self)
		super(Activity, self).save(*args, **kargs)
	save.alters_data = True
	
	class Meta:
		ordering = ['-date_created']
#tagging.register(Activity)
	
class Advertisement(Activity):
	text = models.CharField(max_length=140)
	url = models.URLField()
	
	def __unicode__(self):
		return self.text
		
	@models.permalink
	def get_absolute_url(self):
		return ('tasks-ad_detail', [str(self.id)])
	
	@property
	def message(self):
		url = get_shorturl(self)
		if self.text.find('URL') >= 0:
			return self.text.replace('URL', url)
		else:
			return '%s %s' % (self.text, url)
			
class Classified(Activity):
	title = models.CharField(max_length=140)
	location = models.CharField(max_length=200, blank=True)
	zip = models.CharField(max_length=15, blank=True)
	details = models.TextField(blank=True)
	
	def __unicode__(self):
		return self.title
		
	@models.permalink
	def get_absolute_url(self):
		return ('tasks-classified_detail', [str(self.id)])
tagging.register(Classified)

class Feed(Activity):
	url = models.URLField()
	date_last_updated = models.DateTimeField(default=datetime.datetime(1900,1,1))
	
	def __unicode__(self):
		return self.url
		
	def fetch(self):
		import feedparser
		return feedparser.parse(self.url)
		
	def fetch_new(self):
		feed = self.fetch()
		r = []
		for entry in feed.entries:
			if datetime.datetime(*entry.updated_parsed[:6]) > self.date_last_updated:
				r.append(entry)
		
		self.date_last_updated = datetime.datetime.now()
		self.save()
		return r
	fetch_new.alters_data = True
	
	def fetch_new_entries(self):
		r = []
		for entry in self.fetch_new():
			e = Entry()
			e.feed = self
			e.date = datetime.datetime(*entry.updated_parsed[:6])
			e.title = entry.title
			e.url = entry.link
			e.save()
			r.append(e)
		return r
		
	fetch_new_entries.alters_data = True
	
	@models.permalink
	def get_absolute_url(self):
		return ('tasks-feed_detail', [str(self.id)])
		
class Entry(models.Model):
	feed = models.ForeignKey(Feed, related_name='entries')
	date = models.DateTimeField()
	title = models.CharField(max_length=140)
	url = models.CharField(max_length=200)
	views = models.IntegerField(default=0)
	published = models.BooleanField(default=False)
	
	def __unicode__(self):
		return self.title
	
	@property
	def message(self):
		c = Context()
		c['url'] = get_shorturl(self)
		c['title'] = self.title
		t = get_template('tasks/entry_tweet.txt')
		return t.render(c).strip()
		
	@models.permalink
	def get_absolute_url(self):
		return ('tasks-entry_detail', [str(self.id)])
	
		
class Task(Activity):
	#type = models.IntegerField(choices=TASK_TYPES, default=0)
	
	points = models.IntegerField(default=0)
	budget = models.IntegerField(default=0)
	initial_budget = models.IntegerField(default=0)
	
	limit = models.IntegerField(default=100)
	limit_per_user = models.IntegerField(default=1)
	
	reserve_time = models.IntegerField(help_text='in minutes', default=5)
	
	#priority = models.PositiveIntegerField(max_length=3, default=0)
	#active = models.BooleanField(default=True)
		
	# Custom manager lets us do things like Item.completed_tasks.all()
	objects = models.Manager()
	incomplete = IncompleteTaskManager()
	
	raw_data = models.TextField(default='{}')
	
	def get_data(self):
		return deserialize(self.raw_data)
		
	def set_data(self, v):
		self.raw_data = serialize(v)
	
	data = property(get_data, set_data)
	
	def __unicode__(self):
		return self.name
		
	def get_chances_remaining(self, user=None):
		limit = self.limit - self.achievements.count()
		if self.points:
			point_limit = self.budget // self.points
			limit = min(limit, point_limit)
		if user:
			per_user_rem = self.limit_per_user - self.achievements.filter(user=user).count()
			return min(limit, per_user_rem)
		return limit
		
	@property
	def message(self):
		c = Context()
		c['url'] = get_shorturl(self)
		c['points'] = self.points
		c['text'] = self.name
		t = get_template('tasks/task_tweet.txt')
		return t.render(c).strip()
		
	@models.permalink
	def get_absolute_url(self):
		return ('tasks-task_detail', [str(self.id)])
		
	def get_manage_url(self):
		if self.published:
			return '%smanage/' % self.derived.get_absolute_url()
		else:
			return '%ssetup/' % self.derived.get_absolute_url()
	
	@property
	def completions(self):
		return self.achievements.filter(complete=True)
	
	@property
	def is_overdue(self):
		return datetime.date.today() > self.due_date
		
	def delete(self):
		if self.budget > 0:
			UnitPack.credit(self.user, self.budget)
		super(Task, self).delete()
		
	def save(self, *args, **kargs):
		if not self.id:
			self.initial_budget = self.budget
		if self.completed and not self.date_completed:
			self.date_completed = datetime.datetime.now()
		super(Task, self).save(*args, **kargs)

	class Meta:
		verbose_name = getattr(settings, 'TASKS_TASK_NAME', 'Task')
		verbose_name_plural = getattr(settings, 'TASKS_TASK_NAME_PLURAL', verbose_name + 's')
tagging.register(Task)

class TaskQuestion(models.Model):
	task = models.ForeignKey(Task, related_name='questions')
	type = models.CharField(max_length=15)
	#priority = models.IntegerField(default=0)
	raw_data = models.TextField(default='{}')
	
	def get_data(self):
		return deserialize(self.raw_data)
		
	def set_data(self, v):
		self.raw_data = serialize(v)
	
	data = property(get_data, set_data)
	
	class Meta:
		ordering = ['id']

class Attachment(models.Model):
	activity = models.ForeignKey('Activity', related_name='attachments')
	original_filename = models.CharField(max_length=200, blank=True)
	file = models.FileField(upload_to='attachments/')
	
	@property
	def name(self):
		return self.original_filename or os.path.basename(self.file.name)
	
	def __unicode__(self):
		return self.file.name
		
class Achievement(models.Model):
	user = models.ForeignKey(User, related_name='achievements')
	task = models.ForeignKey('Task', related_name='achievements')
	date_started = models.DateTimeField(auto_now_add=True)
	complete = models.BooleanField(default=False)
	
	objects = models.Manager()
	completed = CompleteObjectManager()
	
	def __unicode__(self):
		return self.task.name
		
	@property
	def is_expired(self):
		return self.date_started > datetime.datetime.now() + datetime.timedelta(minutes=self.task.reserve_time)
