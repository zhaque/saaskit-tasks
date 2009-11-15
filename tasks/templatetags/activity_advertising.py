from django import template
from twitter_app.utils import get_site_twitter_user
from tasks.conf import *

register = template.Library()

def get_site_twitter_info(obj):
	activity = obj.__class__.__name__.lower()
	r = {}
	r['user'] = get_site_twitter_user()
	r['followers'] = r['user'].twitter_profile['followers_count']
	r['cost_fixed'] = SITE_TWEET_COST_FIXED[activity]
	r['cost_variable'] = SITE_TWEET_COST_VARIABLE[activity]
	r['cost'] = r['cost_fixed'] + r['cost_variable'] * r['followers']
	return r
	
@register.inclusion_tag('tasks/advertising_cost.html')
def show_activity_advertising_cost(obj):
	info = get_site_twitter_info(obj)
	return {'object':obj, 'info':info}

@register.simple_tag
def show_activity_site_account():
	return get_site_twitter_user()
