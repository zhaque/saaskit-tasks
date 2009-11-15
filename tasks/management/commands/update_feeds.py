from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
	help = 'Fetches all new feed entries and updates twitter status as needed'
	
	def handle_noargs(self, **options):
		from django.db import transaction
		from tasks.models import Feed, Entry
		
		for feed in Feed.objects.all():
			feed.fetch_new_entries()
			
		for entry in Entry.objects.filter(published=False).order_by('date'):
			try:
				api = entry.feed.user.twitterprofile.api
				api.set_status(entry.message)
				entry.published = True
				entry.save()
			except:
				pass
		
		transaction.commit_unless_managed()
