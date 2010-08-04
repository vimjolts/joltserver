#!-*- coding:utf-8 -*-
import os
import logging
import wsgiref.handlers
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
import simplejson

class Package(db.Model):
  name = db.StringProperty(required=True)
  version = db.StringProperty(required=True)
  url = db.StringProperty()
  description = db.StringProperty(multiline=True)
  packer = db.UserProperty(required=True)
  requires = db.StringProperty(multiline=True)
  installer_unix = db.StringProperty(multiline=True)
  installer_win32 = db.StringProperty(multiline=True)
  timestamp = db.DateProperty(required=True, auto_now=True)

class TestPkg(webapp.RequestHandler):
  def get(self):
    Package(
        name = 'zencoding-vim',
        version = '0.43',
        url = 'http://github.com/mattn/zencoding-vim/raw/master/zencoding.vim',
        description = 'zencoding for vim',
        packer = str(users.get_current_user()),
        requires = '',
        installer_unix = '''
mkdir -p $(VIMHOME)/plugin
cp zencoding.vim $(VIMHOME)/plugin
''',
        installer_win32 = '''
mkdir %VIMHOME%/plugin
copy zencoding.vim %VIMHOME%/plugin
''',
    ).put()
    self.response.out.write("ok")

class ShowPkg(webapp.RequestHandler):
  def get(self, id):
    entry = db.GqlQuery('select * from Package order by timestamp desc').get()
    pkg = {}
    for key in ['name', 'version', 'url', 'description', 'packer', 'requires', 'installer_unix', 'installer_win32']:
      pkg[key] = str(getattr(entry, key))
    self.response.out.write(simplejson.dumps(pkg))

class ListPkg(webapp.RequestHandler):
  def get(self):
    pkgs = []
    for entry in db.GqlQuery('select * from Package order by timestamp desc'):
      pkgs.append({
        "id" : entry.key().id(),
        "name" : entry.name,
        "version" : entry.version,
        "description" : entry.description,
    })
    self.response.out.write(simplejson.dumps(pkgs))

class EditPage(webapp.RequestHandler):
  def get(self, id):
    entry = db.GqlQuery('select * from Package order by timestamp desc').get()
    pkg = {}
    for key in ['name', 'version', 'url', 'description', 'packer', 'requires', 'installer_unix', 'installer_win32']:
      pkg[key] = str(getattr(entry, key))
    self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'edit.html'), pkg))

class MainPage(webapp.RequestHandler):
  def get(self):
    self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'main.html'), {}))

def main():
  application = webapp.WSGIApplication([
    ('/',              MainPage),
    ('/edit/(.*)',     EditPage),
    ('/api/list',      ListPkg),
    ('/api/test',      TestPkg),
    #('/api/add',       AddPkg),
    #('/api/update',    UpdatePkg),
    #('/api/delete',    DeletePkg),
    ('/api/show/(.*)', ShowPkg),
  ], debug=False)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
