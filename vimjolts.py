#!-*- coding:utf-8 -*-
import os
import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

class MainPage(webapp.RequestHandler):
  def head(self):
    self.get(True)

  def get(self, user):
    path = os.path.join(os.path.dirname(__file__), 'main.html')
    self.response.out.write(template.render(path, {}))

def main():
  application = webapp.WSGIApplication([
    ('/(.*)', MainPage),
  ], debug=False)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
