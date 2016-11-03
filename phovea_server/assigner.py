__author__ = 'Samuel Gratzl'


import logging
_log = logging.getLogger(__name__)

class MemoryIDAssigner(object):
  """
  assigns ids to object in memory only, i.e. not persisted
  """
  def __init__(self):
    self._idsmapping = {}

  def unmap(self, uids, idtype):
    if idtype not in self._idsmapping:
      return [None] * len(uids)
    cache = self._idsmapping[idtype]
    def lookup(id):
      for k,v in cache.items():
        if v == id:
          return k
      return None
    return map(lookup, uids)


  def load(self, idtype, mapping):
    """
    resets and loads the given mapping
    :param idtype:
    :param mapping: array of tuples (id, uid)
    :return:
    """
    del self._idsmapping[idtype]
    #assuming incremental ids
    self._idsmapping[idtype] = {id: uid for id,uid in mapping}

  def __call__(self, ids, idtype):
    """
     return the integer index ids for the given ids in the given idtype
    """
    if idtype not in self._idsmapping:
      self._idsmapping[idtype] = { id: i for i,id in enumerate(ids) }
      #1 to 1 mapping
      return range(len(ids))

    cache = self._idsmapping[idtype]
    def add(id) :
      i = cache.get(id, -1)
      if i < 0: #not yet part of
        i = len(cache)
        cache[id] = i
      return i
    return [ add(id) for id in ids]

def ascii(s):
  return s.encode('ascii','ignore')

class DBIDAssigner(object):
  """
  assigns ids to object using a dbm database
  """
  def __init__(self):
    import anydbm
    import phovea_server.config
    import os
    base_dir = phovea_server.config.get('phovea_server.dataDir')
    if not os.path.exists(base_dir):
      os.makedirs(base_dir)
    self._db = anydbm.open(base_dir+'/mapping.dbm','c')

  @staticmethod
  def to_forward_key(idtype, identifier):
    return ascii(idtype + '2id.' + str(identifier))

  @staticmethod
  def to_backward_key(idtype, id):
    return ascii('id2' + idtype + '.' + str(id))

  def unmap(self, uids, idtype):
    idtype = ascii(idtype)
    def lookup(id):
      key = self.to_backward_key(idtype, id)
      return self._db.get(key, None)
    return map(lookup, uids)

  def load(self, idtype, mapping):
    """
    resets and loads the given mapping
    :param idtype:
    :param mapping: array of tuples (id, uid)
    :return:
    """
    idtype = ascii(idtype)
    #assuming incremental ids
    if idtype in self._db:
      #clear old data
      for key in self._db.keys():
        if key.startswith(idtype + '2id.') or key.startswith('id2' + idtype + '.'):
          del self._db[key]

    max_uid = None
    for id,uid in mapping:
      key = self.to_forward_key(idtype, id)
      max_uid = uid if max_uid is None else max(uid, max_uid)
      self._db[key] = str(uid)
      self._db[self.to_backward_key(idtype, uid)] = str(id).encode('ascii','ignore')



  def __call__(self, ids, idtype):
    """
     return the integer index ids for the given ids in the given idtype
    """
    idtype = ascii(idtype)
    max_old = -1 if idtype not in self._db else int(self._db[idtype])
    r = []
    for id in ids:
      key = self.to_forward_key(idtype, id)
      if key in self._db:
        r.append(int(self._db[key]))
      else:
        i = max_old + 1
        _log.debug('create %s  %d',key,i)
        max_old += 1
        self._db[key] = str(i)
        self._db[self.to_backward_key(idtype, i)] = str(id).encode('ascii','ignore')
        r.append(i)

    self._db[idtype] = str(max_old)
    return r


class SqliteIDAssigner(object):
  """
  assigns ids to object using a sqlite database
  """
  def __init__(self):
    import sqlite3
    import phovea_server.config
    import os
    base_dir = phovea_server.config.get('phovea_server.dataDir')
    if not os.path.exists(base_dir):
      os.makedirs(base_dir)
    self._db = sqlite3.connect(base_dir+'/mapping.sqlite3')
    self._db.execute('create table if not exists mapping(idtype text, name text, id int, primary key(idtype,name), unique (idtype,id))')
    self._cache = {}

  def unmap(self, uids, idtype):
    existing = self.get_cache(idtype)
    def lookup(id):
      for k,v in existing.iteritems():
        if v == id:
          return k
      return None
    return map(lookup, uids)

  def get_cache(self, idtype):
    existing = self._cache.get(idtype, None)

    #lazy load
    if existing is None:
      existing = dict()
      self._cache[idtype] = existing
      for row in self._db.execute('select name, id from mapping where idtype=?', (idtype,)):
        existing[row[0]] = row[1]

    return existing

  def load(self, idtype, mapping):
    """
    resets and loads the given mapping
    :param idtype:
    :param mapping: array of tuples (id, uid)
    :return:
    """
    idtype = ascii(idtype)
    #delete cache
    del self._cache[idtype]
    self._db.execute('delete from mapping where idtype=?', (idtype,))

    self._db.executemany('insert or ignore into mapping values ("' + idtype + '",?,?)', mapping)
    self._db.commit()
    self._cache[idtype] = { id: uid for id,uid in mapping}



  def __call__(self, ids, idtype):
    """
     return the integer index ids for the given ids in the given idtype
    """
    existing = self.get_cache(idtype)

    missing = []
    r = []
    max_v = len(existing) -1

    for id in ids:
      id = str(id)
      if id in existing:
        i = existing[id]
      else:
        max_v += 1
        i = max_v
        missing.append((id, i))
        existing[id] = i
      r.append(i)

    if len(missing) > 0:
      _log.debug('add missing to %s %d', idtype, len(missing))
      self._db.executemany('insert or ignore into mapping values ("'+idtype+'",?,?)', missing)
      self._db.commit()

    return r

#TODO implement a Redis based id assigner
#TODO implement a real id mappper

_assigner = SqliteIDAssigner()

def create():
  return _assigner
