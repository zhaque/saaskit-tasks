from django.conf import settings

BUDGET_REASON = 'Budget for "%(task)s"'
COMPLETED_REASON = 'Completed "%(task)s"'

SITE_TWEET_COST_FIXED = {
	'advertisement':0,
	'classified':0,
	'feed':0,
	'task':0,
}
SITE_TWEET_COST_VARIABLE = {
	'advertisement':0,
	'classified':0,
	'feed':0,
	'task':0,
}
SITE_TWEET_COST_FIXED.update(getattr(settings, 'TASKS_SITE_TWEET_COST_FIXED', {}))
SITE_TWEET_COST_VARIABLE.update(getattr(settings, 'TASKS_SITE_TWEET_COST_VARIABLE', {}))
