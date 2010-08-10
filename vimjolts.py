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
  installer = db.StringProperty()
  timestamp = db.DateProperty(required=True, auto_now=True)

installer = {

"unix": {
'00': '',
'10': '''wget $(TARGETURL) -O $(TARGETFILE)
mkdir -p $(VIMHOME)/plugin
cp $(TARGETFILE) $(VIMHOME)/plugin/$(TARGETFILE)
''',
"20": '''wget $(TARGETURL) -O $(TARGETFILE)
unzip $(TARGETFILE) -d $(VIMHOME)
''',
"30": '''svn export $(TARGETURL) $(VIMHOME)
''',
},

"win32": {
'00': '',
"10": '''wget %TARGETURL% -O %TARGETFILE%
mkdir "%VIMHOME%/plugin"
copy %TARGETFILE% "%VIMHOME%/plugin/%TARGETFILE%"
''',
"20": '''wget %TARGETURL% -O "%TARGETFILE%"
unzip "%TARGETFILE%" -d "%VIMHOME%"
''',
"30": '''svn export $(TARGETURL) $(VIMHOME)
''',
},
}

class TestPkg(webapp.RequestHandler):
  def get(self):

    for entry in Package.all():
      entry.delete()

    Package(
        name = 'zencoding-vim',
        version = '0.43',
        url = 'http://github.com/mattn/zencoding-vim/raw/master/zencoding.vim',
        description = 'zencoding for vim',
        packer = users.get_current_user(),
        requires = '',
        installer = "10",
    ).put()

    Package(
        name = 'vim-quickrun',
        version = 'v0.4.1',
        url = 'http://github.com/thinca/vim-quickrun/zipball/v0.4.1',
        description = 'Run commands quickly.',
        packer = users.get_current_user(),
        requires = '',
        installer = "20",
    ).put()

    self.response.out.write("ok")

class ByNamePkg(webapp.RequestHandler):
  def get(self, name):
    entry = Package.gql('where name = :1', name).get()
    if entry:
      self.redirect("/api/entry/%s" % (entry.key()))
    else:
      self.error(404)

class EntryPkg(webapp.RequestHandler):
  def get(self, id):
    entry = Package.get(id)
    if not entry:
      self.error(404)
      return
    pkg = {}
    for key in ['name', 'version', 'url', 'description', 'packer', 'requires', 'installer']:
      pkg[key] = str(getattr(entry, key))
    pkg["id"] = str(entry.key())
    pkg['installer_unix'] = installer['unix'][getattr(entry, "installer")]
    pkg['installer_win32'] = installer['win32'][getattr(entry, "installer")]
    self.response.out.write(simplejson.dumps(pkg))

  def post(self, id):
    if not users.get_current_user():
      self.response.set_status(401, "")
      return

class SearchPkg(webapp.RequestHandler):
  def get(self):
    pkgs = []
    word = self.request.get('word').decode("utf-8", "")
    for entry in db.GqlQuery('select * from Package order by timestamp desc'):
      if entry.name.find(word) != -1 or entry.description.find(word) != -1:
        pkgs.append({
          "id" : str(entry.key()),
          "name" : entry.name,
          "version" : entry.version,
          "description" : entry.description,
    })
    self.response.out.write(simplejson.dumps(pkgs))

class ListPkg(webapp.RequestHandler):
  def get(self):
    count = self.request.get('count')
    try:
      count = int(count)
    except:
      count = 9999
    if count <= 0:
      self.error(500)
      return
    pkgs = []
    for entry in db.GqlQuery('select * from Package order by timestamp desc limit %d' % count):
      pkgs.append({
        "id" : str(entry.key()),
        "name" : entry.name,
        "version" : entry.version,
        "description" : entry.description,
    })
    self.response.out.write(simplejson.dumps(pkgs))

class EditPage(webapp.RequestHandler):
  def get(self, id):
    entry = Package.get(id)
    if not entry:
      self.error(404)
      return
    pkg = {}
    for key in ['name', 'version', 'url', 'description', 'packer', 'requires', 'installer']:
      pkg[key] = str(getattr(entry, key))
    pkg["id"] = str(entry.key())
    pkg['installer_unix'] = installer['unix'][getattr(entry, "installer")]
    pkg['installer_win32'] = installer['win32'][getattr(entry, "installer")]

    user = users.get_current_user()
    if user:
      greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>)" % (user.nickname(), users.create_logout_url("")))
    else:
      greeting = ("<a href=\"%s\">Sign in or register</a>" % users.create_login_url(""))
    self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'edit.html'), { "pkg": pkg, "greeting": greeting }))

class SearchPage(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>)" % (user.nickname(), users.create_logout_url("")))
    else:
      greeting = ("<a href=\"%s\">Sign in or register</a>" % users.create_login_url(""))
    self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'search.html'), { "greeting": greeting }))

class MainPage(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>)" % (user.nickname(), users.create_logout_url("")))
    else:
      greeting = ("<a href=\"%s\">Sign in or register</a>" % users.create_login_url(""))
    self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'main.html'), { "greeting": greeting }))

def main():
  application = webapp.WSGIApplication([
    ('/',               MainPage),
    ('/edit/(.*)',      EditPage),
    ('/search',         SearchPage),
    ('/api/list',       ListPkg),
    ('/api/search',     SearchPkg),
    ('/api/test',       TestPkg),
    #('/api/add',       AddPkg),
    #('/api/update',    UpdatePkg),
    #('/api/delete',    DeletePkg),
    ('/api/entry/byname/(.*)', ByNamePkg),
    ('/api/entry/(.*)', EntryPkg),
  ], debug=False)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()

# vim:set et ts=2 sw=2:
