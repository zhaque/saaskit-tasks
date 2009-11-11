from django import template

register = template.Library()

@register.inclusion_tag('tasks/task/question_form.html')
def show_task_question_form(q, form_id=''):
	return {'question':q, 'data':q.data, 'form_id':form_id}

@register.inclusion_tag('tasks/task/question_stats.html')
def show_task_question_stats(q):
	return {'question':q, 'data':q.data}
