__author__ = 'Samuel Gratzl'

import re

# extend a dictionary recursivly
def extend(target, w):
  for k,v in w.iteritems():
    if isinstance(v,dict):
      if k not in target:
        target[k] = extend({}, v)
      else:
        target[k] = extend(target[k], v)
    else:
      target[k] = v
  return target


def replace_variables_f(s, lookup):
  if re.match(r'^\$\{([^}]+)\}$', s): #full string is a pattern
    s = s[2:len(s)-1]
    v = lookup(s)
    if v is None:
      print 'cant resolve ' + s
      return '$unresolved$'
    return v
  def match(m):
    v = lookup(m.group(1))
    if v is None:
      print 'cant resolve ' + m.group(1)
      return '$unresolved$'
    return v
  return re.sub(r'\$\{([^}]+)\}', match, s)

def replace_variables(s, variables):
  return replace_variables_f(s, lambda x: variables.get(x, None))

def replace_nested_variables(obj, lookup):
  if isinstance(obj, list):
    return [replace_nested_variables(o, lookup) for o in obj]
  elif isinstance(obj, basestring):
    return replace_variables_f(obj, lookup)
  elif isinstance(obj, dict):
    return { k: replace_nested_variables(v, lookup) for k,v in obj.iteritems() }
  return obj

def unpack_eval(s):
  return re.sub(r'eval!(.*)', '\1', s)

def unpack_python_eval(s):
  m = re.search(r'eval!(.*)', s)
  if m is None:
    return s
  return eval(m.group(1))