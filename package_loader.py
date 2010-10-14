import sys
sys.path.append(".")

import datetime
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.tools import bulkloader
from vimjolts import Package

class PackageLoader(bulkloader.Loader):
    def __init__(self):
        bulkloader.Loader.__init__(
                self, 'Package', [
                    ('name', str),
                    ('version', str),
                    ('url', str),
                    ('description', lambda x: x.decode("utf-8", "")),
                    ('packer', lambda x: users.User(email=x)),
                    ('requires', str),
                    ('installer', str),
                    ('timestamp', lambda x: datetime.datetime.strptime(x, '%Y/%m/%d').date())])

loaders = [PackageLoader]
# vim:set et ts=4 sw=4 sts=4 :
