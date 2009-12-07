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

def get_site_twitter_info(obj):
	from twitter_app.utils import get_site_twitter_user
	activity = obj.__class__.__name__.lower()
	r = {}
	r['user'] = get_site_twitter_user()
	r['followers'] = r['user'].twitter_profile['followers_count']
	r['cost_fixed'] = SITE_TWEET_COST_FIXED[activity]
	r['cost_variable'] = SITE_TWEET_COST_VARIABLE[activity]
	r['cost'] = r['cost_fixed'] + r['cost_variable'] * r['followers']
	return r
