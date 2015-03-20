#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
import os, sys, re, datetime, tempfile
import requests, hashlib
import lxml.html

RZ_URL = 'http://ringzer0team.com'
RZ_START_TIME = datetime.datetime.now()
RZ_VERBOSE = int(os.environ.get('RZ_VERBOSE') or 1) == 1

def _tsout(*objs):
	prefix = '[{0}]'.format(datetime.datetime.now() - RZ_START_TIME)
	print(prefix, *objs, file=sys.stdout)

def _out(*objs):
	print(*objs, file=sys.stdout)

def error(*objs):
	print(*objs, file=sys.stderr)

def output(prefix, info = None):
	if RZ_VERBOSE:
		if info:
			prefix = '{0}: {1}'.format(prefix, info)
		_tsout(prefix)
	elif info:
		_out(info)

def _init(verbose = False):
	global RZ_VERBOSE
	RZ_VERBOSE = verbose

def get_auth():
	username, password = None, None
	if not sys.stdin.isatty():
		lines = sys.stdin.readlines()
		l = len(lines)
		if l == 1:
			p = lines[0].split(' ')
			if len(p) > 1: 
				username = p[0].strip()
				password = p[1].strip()
		elif l > 1:
			username = lines[0].strip()
			password = lines[1].strip()
	else:
		username = raw_input('username: ').strip()
		password = raw_input('password: ').strip()
	if not username or not password:
		_out('error: wrong auth input')
		sys.exit(1)
	return (username, password)

def get_sections(html):
	msg_section = re.compile(r'^-+\s(BEGIN|END)\s([a-z\s]+)\s-+$', re.I)
	doc = lxml.html.document_fromstring(html)
	wrapper = doc.xpath('//div[@class="challenge-wrapper"]')[0]
	text = wrapper.text_content()
	sections = {}
	section, title, msg, checksum = 'title', [], [], []
	for s in text.splitlines():
		s = s.strip()
		if not s: continue
		mx = re.match(msg_section, s)
		if mx:
			begin = mx.group(1).lower() == 'begin'
			section = mx.group(2).lower() if begin else ''
			continue
		if not section:
			continue
		if not section in sections:
			sections[section] = []
		sections[section].append(s)
	for k in sections.keys():
		sections[k] = os.linesep.join(sections[k])
	return sections

def get_response(html):
	doc = lxml.html.document_fromstring(html)
	wrapper = doc.xpath('//div[@class="challenge-wrapper"]')[0]
	xalert = wrapper.xpath('./div[contains(@class, "alert")]')[0]
	return xalert.text_content().strip()

class tmpfile(object):
	def __enter__(self):
		self.fd, self.fn = tempfile.mkstemp()
		return self.fd, self.fn
	
	def __exit__(self, ex_type, ex_value, ex_traceback):
		try: 
			os.close(self.fd)
		except: pass
		os.unlink(self.fn)

def write_bin_file(fd, data):
	f = os.fdopen(fd, 'wb')
	f.write(data)
	f.close()

def login():
	username, password = get_auth()
	if RZ_VERBOSE: 
		_tsout('logging')
	s = requests.Session()
	payload = {'username':username, 'password':password}
	r = s.post('{0}/login'.format(RZ_URL), data=payload)
	return s

def read_challenge(s, ch):
	if RZ_VERBOSE: 
		_tsout('reading challenge')
	r = s.get('{0}/challenges/{1}'.format(RZ_URL, int(ch)))
	sections = get_sections(r.text)
	if RZ_VERBOSE:
		for k, v in sections.items():
			_tsout('{0}: {1}'.format(k, v))
	return sections

def submit_challenge(s, ch, answer):
	if RZ_VERBOSE:
		_tsout('submitting challenge solution')
	r = s.get('{0}/challenges/{1}/{2}'.format(RZ_URL, int(ch), answer))
	response = get_response(r.text)
	return response
