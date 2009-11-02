from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
import simplejson, datetime

def _json_encode(obj):
	if isinstance(obj, datetime.datetime):
		return obj.strftime('%b %d, %Y %H:%M:%S')

def deserialize(r):
	return simplejson.loads(r)

def serialize(r):
	for name, obj in r.items():
		if hasattr(obj, '__dict__'):
			data = {}
			for attr, val in obj.__dict__.items():
				if attr.startswith('_'):
					continue
				elif attr.endswith('_id'):
					a = attr[:-3]
					if a not in r:
						v = getattr(obj, a, None)
						if v:
							data[a] = unicode(v)
				data[attr] = val
				
			r[name] = data
		else:
			r[name] = obj
			
	return simplejson.dumps(r, default=_json_encode)
	
	
def render_to(template=''):
	def deco(view):
		def fn(request, *args, **kargs):
			if 'template' in kargs:
				t = kargs['template']
				del kargs['template']
			else:
				t = template
			r = view(request, *args, **kargs) or {}
			if isinstance(r, HttpResponse):
				return r
			else:
				c = RequestContext(request, r)
				return render_to_response(t, context_instance=c)
		return fn
	return deco
	
def serialize_to(view):
	def fn(*args, **kargs):
		r = view(*args, **kargs)
		if isinstance(r, HttpResponse):
			return r
		else:
			return HttpResponse(serialize(dict(r or {})))
	return fn
	

def redirect_to(name, *args, **kargs):
	return HttpResponseRedirect(reverse(name, args=args, kwargs=kargs))
