from django.contrib import admin
from .models import *

class ProjectAdmin(admin.ModelAdmin):
	list_display = ('name', 'slug', 'type')
	prepopulated_fields = {'slug': ('name',)}
	#date_heirarchy = 'date_created'
	
class AttachmentInline(admin.TabularInline):
	model = Attachment
	extra = 1

class TaskAdmin(admin.ModelAdmin):
	list_display = ('name', 'project', 'priority', 'completed', 'date_completed', 'date_due', 'date_created')
	date_heirarchy = 'date_created'
	inlines = (AttachmentInline,)
	list_filter = ('completed',)
	ordering = ('project','name')
	search_fields = ('name','description')

admin.site.register(Attachment)
admin.site.register(Task, TaskAdmin)
admin.site.register(Project, ProjectAdmin)
