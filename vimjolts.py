#!-*- coding:utf-8 -*-
import os
import logging
import wsgiref.handlers
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.api import memcache
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

def get_all_packages(fields):
  val = memcache.get("packages")
  if val is not None:
    return val
  pkgs = []
  offset = 0
  while True:
    exist = False
    count = 0
    for entry in db.GqlQuery('select * from Package order by timestamp desc offset %d' % offset):
      exist = True
      pkg = {}
      for field in fields:
        if field == 'id':
          pkg[field] = str(entry.key())
        else:
          pkg[field] = getattr(entry, field).encode("utf-8", "").decode("utf-8")
      pkgs.append(pkg)
      count += 1
      if maxsize != -1 and len(pkgs) > maxsize:
        exist = False
        break
    if exist == False:
      break
    offset += count
  memcache.set("packages", pkgs, 0)
  return pkgs

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
    if installer['unix'].has_key(getattr(entry, "installer")):
      pkg['installer_unix'] = installer['unix'][getattr(entry, "installer")]
    if installer['win32'].has_key(getattr(entry, "installer")):
      pkg['installer_win32'] = installer['win32'][getattr(entry, "installer")]
    self.response.out.write(simplejson.dumps(pkg))

  def post(self, id):
    if not users.get_current_user():
      self.response.set_status(401, "")
      return

class SearchPkg(webapp.RequestHandler):
  def get(self):
    word = self.request.get('word').decode("utf-8", "").lower()
    pkgs = [x for x in get_all_packages(["id", "name", "version", "description"]) if x["name"].lower().find(word) != -1 or x["description"].lower().find(word) != -1]
    self.response.out.write(simplejson.dumps(pkgs))

class CountPkg(webapp.RequestHandler):
  def get(self):
    self.response.out.write(str(len(get_all_packages(["id"]))))

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
    self.response.out.write(simplejson.dumps(get_all_packages(["id", "name", "version", "description"])[:count]))

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
    if installer['unix'].has_key(getattr(entry, "installer")):
      pkg['installer_unix'] = installer['unix'][getattr(entry, "installer")]
    if installer['win32'].has_key(getattr(entry, "installer")):
      pkg['installer_win32'] = installer['win32'][getattr(entry, "installer")]

    user = users.get_current_user()
    if user:
      greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>)" % (user.nickname(), users.create_logout_url("")))
    else:
      greeting = ("<a href=\"%s\">Sign in or sign up</a>" % users.create_login_url(""))
    self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'edit.html'), { "pkg": pkg, "greeting": greeting }))

class SearchPage(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>)" % (user.nickname(), users.create_logout_url("")))
    else:
      greeting = ("<a href=\"%s\">Sign in or sign up</a>" % users.create_login_url(""))
    self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'search.html'), { "greeting": greeting }))

class MainPage(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>)" % (user.nickname(), users.create_logout_url("")))
    else:
      greeting = ("<a href=\"%s\">Sign in or sign up</a>" % users.create_login_url(""))
    self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'main.html'), { "greeting": greeting }))

def main():
  application = webapp.WSGIApplication([
    ('/',               MainPage),
    ('/edit/(.*)',      EditPage),
    ('/search',         SearchPage),
    ('/api/list',       ListPkg),
    ('/api/search',     SearchPkg),
    ('/api/count',      CountPkg),
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
