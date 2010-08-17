#!-*- coding:utf-8 -*-
import os
import logging
import wsgiref.handlers
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext.webapp import template
#import xmllib
#import elementtree.SimpleXMLTreeBuilder as xmlbuilder
import simplejson
from BeautifulSoup import BeautifulSoup

class Package(db.Model):
  name = db.StringProperty(required=True)
  version = db.StringProperty(required=True)
  author = db.StringProperty()
  url = db.StringProperty()
  description = db.StringProperty(multiline=True)
  packer = db.UserProperty(required=True)
  requires = db.StringProperty(multiline=True)
  extractor = db.StringProperty()
  installer = db.StringProperty()
  installer_unix = db.StringProperty(multiline=True)
  installer_win32 = db.StringProperty(multiline=True)
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
          val = getattr(entry, field)
          if not val:
            pkg[field] = ""
          else:
            pkg[field] = val.encode("utf-8", "").decode("utf-8")
      pkgs.append(pkg)
      count += 1
    if exist == False:
      break
    offset += count
  memcache.set("packages", pkgs, 0)
  return pkgs

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
    for key in ['name', 'version', 'url', 'description', 'author', 'requires', 'extractor', 'installer', 'installer_unix', 'installer_win32']:
      pkg[key] = getattr(entry, key).encode("utf-8", "").decode("utf-8")
    pkg["packer"] = str(entry.packer)
    pkg["id"] = str(entry.key())
    self.response.out.write(simplejson.dumps(pkg))

  def post(self, id):
    if not users.get_current_user():
      self.response.set_status(401, "")
      return
    entry = Package.get(id)
    if not entry:
      self.error(404)
      return
    info = simplejson.loads(self.request.get('info').decode("utf-8", ""))
    for key in keys(info):
      if key != 'id':
        setattr(entry, key, info[key])
    entry.put()
    memcache.delete("packages")
    self.redirect("/api/entry/%s" % (entry.key()))

class SearchPkg(webapp.RequestHandler):
  def get(self):
    word = self.request.get('word').decode("utf-8", "").lower()
    pkgs = [x for x in get_all_packages(["id", "name", "version", "description"]) if x["name"].lower().find(word) != -1 or x["description"].lower().find(word) != -1]
    self.response.out.write(simplejson.dumps(pkgs))

class CountPkg(webapp.RequestHandler):
  def get(self):
    self.response.out.write(str(len(get_all_packages(["id"]))))

class TruncatePkg(webapp.RequestHandler):
  def get(self):
    for pkg in Package.all():
      pkg.delete()
    memcache.delete("packages")
    self.response.out.write("ok")

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

class NewPage(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>)" % (user.nickname(), users.create_logout_url("")))
    else:
      greeting = ("<a href=\"%s\">Sign in or sign up</a>" % users.create_login_url(""))
    self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'edit.html'), { "pkg": {}, "greeting": greeting }))

class EditPage(webapp.RequestHandler):
  def get(self, id):
    entry = Package.get(id)
    if not entry:
      self.error(404)
      return
    pkg = {}
    for field in ['name', 'version', 'url', 'description', 'author', 'requires', 'extractor', 'installer', 'installer_unix', 'installer_win32']:
      val = getattr(entry, field)
      if not val:
        pkg[field] = ""
      else:
        pkg[field] = val.encode("utf-8", "").decode("utf-8")
    pkg["packer"] = str(entry.packer)
    pkg["id"] = str(entry.key())

    user = users.get_current_user()
    if user:
      greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>)" % (user.nickname(), users.create_logout_url("")))
    else:
      greeting = ("<a href=\"%s\">Sign in or sign up</a>" % users.create_login_url(""))
    self.response.out.write(template.render(os.path.join(os.path.dirname(__file__), 'edit.html'), { "pkg": pkg, "greeting": greeting }))

  def post(self, id):
    if not users.get_current_user():
      self.response.set_status(401, "")
      return
    if len(id) > 0:
      entry = Package.get(id)
      if not entry:
        self.error(404)
        return
      entry.name = self.request.get('name'),
      entry.version = self.request.get("version"),
      entry.description = self.request.get("description"),
      entry.url = self.request.get("url"),
      entry.extractor = self.request.get("extractor"),
      entry.author = self.request.get("author"),
      entry.packer = users.get_current_user(),
      entry.requires = self.request.get("requires"),
      entry.installer = self.request.get("installer"),
      entry.installer_unix = self.request.get("installer_unix"),
      entry.installer_win32 = self.request.get("installer_win32"),
    else:
      entry = Package(
        name=self.request.get('name'),
        version=self.request.get("version"),
        description=self.request.get("description"),
        url=self.request.get("url"),
        extractor=self.request.get("extractor"),
        author=self.request.get("author"),
        packer=users.get_current_user(),
        requires=self.request.get("requires"),
        installer=self.request.get("installer"),
        installer_unix=self.request.get("installer_unix"),
        installer_win32=self.request.get("installer_win32"),
      )
    entry.put()
    memcache.delete("packages")
    self.redirect("/edit/%s" % (entry.key()))

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

#class SyncPkg(webapp.RequestHandler):
#  def get(self):
#    config = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), 'plagger-config.yaml'), 'r'))
#    try:
#      content = urlfetch.fetch('http://www.vim.org/scripts/script_search_results.php?order_by=creation_date&direction=descending').content
#      parser = xmlbuilder.TreeBuilder()
#      xmllib.XMLParser.__init__(parser, accept_utf8=1)
#      parser.feed(content)
#      dom = parser.close()
#      entries = dom.findall('item')
#      count = 0
#      for entry in entries:
#        name = entry.find("title").contents[0].split(" - ")[0]
#        description = entry.find("title").contents[0].split(" - ")[1].encode("utf-8", "")
#        url = entry.find('link').text
#        if Package.gql('WHERE name=:name and version=:version', name=name, version=version).get(): continue
#        logging.info('posting:' + url)
#        description = entry.find('{http://purl.org/rss/1.0/}title').text or ''
#        extended = entry.find('{http://purl.org/rss/1.0/}description').text or ''
#        tags = ' '.join([x.text for x in entry.findall('{http://purl.org/dc/elements/1.1/}subject')]) or ''
#        uri = 'https://api.del.icio.us/v1/posts/add?' + urllib.urlencode({ 'url' : url, 'description' : description, 'extended' : extended, 'tags' : tags })
#        try:
#          auth = base64.b64encode('%s:%s' % (config['delicious_user'], config['delicious_pass'])).strip("\n")
#          res = urlfetch.fetch(uri, headers={ 'Authorization' : 'Basic %s' % auth }).status_code
#          Bookmark(url = url.decode('utf-8'), description = description.replace("\n", '').decode('utf-8'), extended = extended.decode('utf-8'), tags = tags.decode('utf-8')).put()
#          logging.info('posted:' + url)
#        except Exception, e:
#          logging.error(e)
#          logging.info('failed:' + url)
#          pass
#        count = count + 1
#        if count > 5: break
#      self.response.out.write('done')
#    except:
#      self.response.out.write('failed')

def main():
  application = webapp.WSGIApplication([
    ('/',               MainPage),
    ('/edit/(.*)',      EditPage),
    ('/new',            NewPage),
    ('/search',         SearchPage),
    ('/api/list',       ListPkg),
    ('/api/search',     SearchPkg),
    ('/api/count',      CountPkg),
    #('/api/truncate',   TruncatePkg),
    #('/api/add',       AddPkg),
    #('/api/update',    UpdatePkg),
    #('/api/delete',    DeletePkg),
    ('/api/entry/byname/(.*)', ByNamePkg),
    ('/api/entry/(.*)', EntryPkg),
    #('/tasks/sync',     SyncPkg),
  ], debug=False)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()

# vim:set et ts=2 sw=2:
