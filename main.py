#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import jinja2
import os
from url import gravatar_base, SCORES, github_base
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import memcache
import json
 
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

class GitHub(db.Model):
    username = db.StringProperty(required=True)
    grava_id = db.StringProperty(required=True)
    score = db.IntegerProperty(required=True)

class BaseHandler(webapp2.RequestHandler):
    def render(self, template, **params):
        t = jinja_env.get_template(template)
        self.response.write(t.render(params))

    def get(self):
        self.render('index.html')

    def get_all_records(self, update=False):
        g = memcache.get('github')
        if not g or update: 
            g = list(GitHub.all())
            memcache.set('github', g)
        return g

    def get_score(self, name):
        url = github_base % name
        c = urlfetch.fetch(url)
        if c.status_code != 200:
            return
        record = GitHub.all().filter('username =', name).get()
        if not record:
            js = json.loads(c.content)
            events = [j['type'] for j in js]
            scores = sum(SCORES.get(e, 0) for e in events)
            gravatar_id = js[0]['actor_attributes']['gravatar_id']
            GitHub(username=name, grava_id = gravatar_id, score = scores).put()
            self.get_all_records(True)
            return scores
        else:
            return record.score


class MainHandler(BaseHandler):
    def get(self):
        records = self.get_all_records()
        self.render('index.html', gs=records, base_url=gravatar_base)

    def post(self):
        name = self.request.get('username')
        self.get_score(name)
        self.redirect('/')

app = webapp2.WSGIApplication([
    ('/', MainHandler)
], debug=True)
