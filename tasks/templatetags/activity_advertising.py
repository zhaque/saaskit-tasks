from django import template
from tasks.conf import *
from twitter_app.utils import get_site_twitter_user

register = template.Library()
	
@register.inclusion_tag('tasks/advertising_cost.html')
def show_activity_advertising_cost(obj):
	info = get_site_twitter_info(obj)
	return {'object':obj, 'info':info}

@register.simple_tag
def show_activity_site_account():
	return get_site_twitter_user()
