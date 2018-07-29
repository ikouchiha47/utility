#!/usr/bin/env python

import argparse
import sys
import urllib
import urllib2
import json
import re
import os
from multiprocessing.pool import ThreadPool

URL="http://localhost:8001"

class Httplib:
	@staticmethod
	def humanize_response(code):
		if code < 200:
			return 'Wadduhek'
		elif code >= 200 and code < 399:
			return 'Success'
		elif code >= 400 and code < 404:
			return 'Unauthorized'
		elif code == 404:
			return 'NotFound'
		elif code > 400 and code < 500:
			return 'ErrorInRequest'
		elif code >= 500:
			return 'ServerError'
	@staticmethod
	def request(url, data='{}', method='POST'):
		req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
		req.get_method = lambda: method
		res = None

		try:
			res = urllib2.urlopen(req)
			return { 'code': Httplib.humanize_response(res.getcode()), 'data': json.loads(res.read().decode('utf-8')) }
		except urllib2.HTTPError as e:
			res = e
			return { 'code': Httplib.humanize_response(e.getcode()), 'data': json.loads(e.read().decode('utf-8')) }
		except ValueError:
			return { 'code': Httplib.humanize_response(res.getcode()), 'data': res.read().decode('utf-8') }
		except Exception as e:
			print(e)
			exit(1)
	
	@staticmethod
	def get(url, data={}):   return Httplib.request(url, urllib.urlencode(data), 'GET')
	
	@staticmethod
	def post(url, data={}):  return Httplib.request(url, json.dumps(data), 'POST')

	@staticmethod
	def put(url, data={}):   return Httplib.request(url, json.dumps(data), 'PUT')

	@staticmethod
	def patch(url, data={}):  return Httplib.request(url, json.dumps(data), 'PATCH')

	@staticmethod
	def delete(url, data={}): return Httplib.request(url, '', 'DELETE')

 
def get_apis(url="http://localhost:8001", data=[], prev_offset=""):
	apis = Httplib.get("%s/apis" % url)['data']
	data.extend(apis['data'])

	if 'offset' in apis:
		return get_apis(apis["next"], data, apis['offset'])
	return data

def get_plugins(url="http://localhost:8001", data=[], prev_offset=""):
	plugins = Httplib.get("%s/plugins" % url)['data']
	data.extend(plugins['data'])

	if 'offset' in plugins:
		return get_plugins(plugins["next"], data, plugins['offset'])
	return data

def merge(x, y):
    z = x.copy()
    z.update(y)
    return z

def make_api_data(args):
	res = {
		'name': args.name,
		'upstream_url': args.upstream,
		'uris': args.uri,
		'methods': args.method,
		'strip_uri': args.strip_uri,
		'retries': 0,
		'upstream_connect_timeout': args.conntimer * 1000,
		'upstream_read_timeout': args.readtimer * 1000,
		'upstream_send_timeout': args.sendtimer * 1000
	}

	return {k: v for k, v in res.items() if v or v == 0 or v == False}

def make_custom_plugin(args, config={}):
	if(args.config):
		config = merge(config, json.loads(args.config))

	res = {
		'name': args.name,
		'enabled': not args.disabled,
		'config': config
	}

	return {k: v for k, v in res.items() if v or v == 0 or v == False}

def make_file_log(args):
	args.name = 'file-log'
	config = {'path': '/kong-logs/file.log'}
	return make_custom_plugin(args, config)

def make_datadog(args):
	args.name = 'datadog'
	config = { 'host': 'localhost', 'port': 8125 }
	return make_custom_plugin(args, config)

def assert_prop(obj, command, parser):
	if not hasattr(obj, command):
            print('Unrecognized command')
            parser.print_help()
            exit(1)

class Api:
	def create(self):
		parser = CustomParser(description='create api')
		parser.add_argument('--name', help='api name')
		parser.add_argument('--upstream', help='upstream url')
		parser.add_argument('--uri', action='append', help='add multiple uri --uri /foo --uri bar')
		parser.add_argument('--method', nargs='?', action='append', default=[], help='add multiple method --method=get --method=post, default=[]')
		parser.add_argument('--strip_uri', action='store_true', help='strip matching uri from url')
		parser.add_argument('--conntimer', type=int, help='upstream connect timeout in second', default=10)
		parser.add_argument('--readtimer', type=int, help='upstream read timeout in second', default=10)
		parser.add_argument('--sendtimer', type=int, help='upstream send timeout in second', default=10)
		
		args = parser.parse_args(sys.argv[3:])

		resp = Httplib.post("%s/apis" % URL, make_api_data(args))
		print(json.dumps(resp['data'], indent=4))
		
		
	def update(self):
		parser = CustomParser(description='update api')
		parser.add_argument('--name', help='api name')
		parser.add_argument('--new_name', default='', help='new api name')
		parser.add_argument('--upstream', default='', help='upstream url')
		parser.add_argument('--uri', action='append', default=[], help='add multiple uri --uri /foo --uri bar')
		parser.add_argument('--method', nargs='?', action='append', default=[], help='add multiple method --method=get --method=post, default=[]')
		parser.add_argument('--strip_uri', action='store_true', help='strip uri')
		parser.add_argument('--conntimer', help='upstream connect timeout in second', default=10)
		parser.add_argument('--readtimer', help='upstream read timeout in second', default=10)
		parser.add_argument('--sendtimer', help='upstream send timeout in second', default=10)
		
		args = parser.parse_args(sys.argv[3:])
		name = args.name
		if args.new_name: args.name = args.new_name

		resp = Httplib.patch("%s/apis/%s" % (URL, name), make_api_data(args))
		print(json.dumps(resp['data'], indent=4))
	
	def find(self):
		parser = CustomParser(description='find api by name')
		parser.add_argument('--name', help='api name')
		
		args = parser.parse_args(sys.argv[3:])
		if not args.name:
			exit(0)

		data = get_apis(URL)
		if not data:
			print("couldnot find api with name %s" % args.name)
			exit(0)

		for api in data:
			if api['name'] == args.name:
				print(json.dumps(api, indent=4))
				return
		print("couldnot find api with name %s" % args.name)
	def delete(self):
		parser = CustomParser(description='delete api by name')
		parser.add_argument('--name', help='api name')

		args = parser.parse_args(sys.argv[3:])
		res = Httplib.delete("%s/apis/%s" % (URL, args.name))
		print(json.dumps(res['data'], indent=4))
	def search(self):
		parser = CustomParser(description='search api by uri or name')
		parser.add_argument('--uri', help='uri regex', nargs='?', default='')
		parser.add_argument('--name', help='name regex', nargs='?', default='')
		parser.add_argument('--upstream', help='name of upstream', nargs='?', default='')

		args = parser.parse_args(sys.argv[3:])
		data = get_apis(URL)	
		if not data: exit(0)
		
		if not args.uri and not args.name and not args.upstream:
			print(json.dumps(data, indent=4))
			return
		if args.name.strip():
			namerx = re.compile(re.escape(args.name.strip()), re.MULTILINE)
			data = list(filter(lambda x: namerx.search(x["name"]), data))
		if args.uri.strip():
			urirx = re.compile(re.escape(args.uri.strip()), re.MULTILINE)
			data = list(filter(lambda x: filter(urirx.search, x.get('uris', [])), data))
		if args.upstream.strip():
			uprx = re.compile(re.escape(args.upstream.strip()), re.MULTILINE)
			data = list(filter(lambda x: uprx.search(x["upstream_url"]), data))

		print(json.dumps(data, indent=4))
		

class Plugin:
	def create(self):
		parser = CustomParser(description='create plugin for api')
		parser.add_argument('--api', help='api name')
		parser.add_argument('--name', help='plugin name')
		parser.add_argument('--config', help='plugin config in json', nargs='?')
		parser.add_argument('--disabled', action='store_true', help='enable plugin')
		parser.add_argument('--file', help='json file path for plugin', nargs='?')

		data = {}
		args = parser.parse_args(sys.argv[3:])
		if args.name == "file-log":
			data = make_file_log(args)
		elif args.name == "datadog":
			data = make_datadog(args)
		else:
			if not args.config and not args.file:
				print('please provide file path or use config in json format')
				return
			if not args.config and args.file:
				with open(args.file) as f: args.config = json.loads(f)

			data = make_custom_plugin(args)

		resp = Httplib.post("%s/apis/%s/plugins" % (URL, args.api), data)
		print(json.dumps(resp['data'], indent=4))
	def update(self):
		parser = CustomParser(description='update plugin with id or name and api')
		parser.add_argument('--api', help='api name')
		group = parser.add_mutually_exclusive_group(required=True)
		group.add_argument('--name', help='plugin name')
		group.add_argument('--id', help='plugin id')
		parser.add_argument('--config', help='plugin config in json', nargs='?')
		parser.add_argument('--disabled', action='store_true', help='disable plugin')
		parser.add_argument('--file', help='json file path for plugin', nargs='?')

		args = parser.parse_args(sys.argv[3:])
		plugin = None

		if args.name:
			res = Httplib.get("%s/apis/%s/plugins" % (URL, args.api))
			if res['code'] != 'Success':
				print("Could not find plugins for api %s" % args.api)
				return
			plugins = filter(lambda x: x["name"] == args.name, res['data']['data'])
			if not plugins:
				print("Couldnot find plugin %s for api %s" % (args.name, args.api))
				return
			plugin = plugins[0]
		elif args.id:
			res = Httplib.get("%s/plugins/%s" % (URL, args.id))
			if res['code'] != 'Success':
				print("couldnot find plugin with id")
				return
			plugin = res['data']

		data = {}
		args = parser.parse_args(sys.argv[3:])
		if args.name == "file-log":
			data = make_file_log(args)
		elif args.name == "datadog":
			data = make_datadog(args)
		elif args.name == "gojek-auth":
			data = make_gojek_auth(args)
		elif args.name == "fraud-blacklist-auth":
			data = make_fraud_blacklist_auth(args)
		else:
			if not args.config and not args.file:
				print('please provide file path or use config in json format')
				return
			if not args.config and args.file:
				with open(args.file) as f: args.config = json.loads(f)

			data = make_custom_plugin(args)
		
		args.id = plugin["id"]
		resp = Httplib.patch("%s/plugins/%s" % (URL, args.id), data)
		print(json.dumps(resp['data'], indent=4))
	def find(self):
		parser = CustomParser(description='find all plugins or particular plugin for api')
		parser.add_argument('--api', help='api name', nargs='?')
		group = parser.add_mutually_exclusive_group(required=False)
		group.add_argument('--name', help='plugin name')
		group.add_argument('--id', help='plugin id')
		
		args = parser.parse_args(sys.argv[3:])
		
		if args.id:
			res = Httplib.get("%s/plugins/%s" % (URL, args.id))
			print(json.dumps(res['data'], indent=4))
			return

		if not args.api:
			print("please provide api name if plugin id is unknown")
			exit(1)

		res = Httplib.get("%s/apis/%s/plugins" % (URL, args.api))
		if not res['code'] == 'Success':
			print(json.dumps(res['data'], indent=4))
			return
		if not args.name:
			print(json.dumps(res['data']['data'], indent=4))
			return

		namerx = re.compile(re.escape(args.name), re.MULTILINE)
		print(res['data'])
		for plug in res['data']['data']:
			if namerx.search(plug['name']): 
				print(json.dumps(plug, indent=4))
				return
		print("Could not find plugin %s for api %s" % (args.name, args.api))
	def delete(self):
		parser = CustomParser(description='delete plugin by id or name')
		parser.add_argument('--api', help='api name', default='')
		group = parser.add_mutually_exclusive_group(required=True)
		group.add_argument('--name', help='plugin name')
		group.add_argument('--id', help='plugin id')
		
		args = parser.parse_args(sys.argv[3:])
		if args.id:
			res = Httplib.delete("%s/plugins/%s" % (URL, args.id))
			print(json.dumps(res['data'], indent=4))
			return
		if args.name and args.api:
			res = Httplib.get("%s/apis/%s/plugins" % (URL, args.api))
			if res['code'] != 'Success':
				print(json.dumps(res['data'], indent=4))
				return
			for plug in res['data']['data']:
				if plugin['name'] == args.name:
					res = Httplib.delete("%s/plugins/%s" % (URL, plugin["id"]))
					print(json.dumps(res['data'], indent=4))
					return
			
			print("Could not find plugin %s for api %s" % (args.name, args.api))
	def search(self):
		parser = CustomParser(description='search')
		parser.add_argument('--api', help='api name to filter', nargs='?')
		parser.add_argument('--api_id', help='api id to filter', nargs='?')
		parser.add_argument('--name', help='plugin name', nargs='?')
		parser.add_argument('--verbose', '-vv', help='show plugin details', action='store_true')
		
		args = parser.parse_args(sys.argv[3:])
		plugins = get_plugins(URL)
		res = []
	        namerx = None
	
		if args.name:
			namerx = re.compile(re.escape(args.name), re.MULTILINE)

		for plugin in plugins:
			if not namerx:
				if args.verbose:
					res.extend([ {"apiId": plugin.get("api_id", None), 'id': plugin['id'], 'name': plugin['name'], 'config': plugin['config'] } ])
				else:
					res.extend([{ 'name': plugin["name"], 'id': plugin["id"], 'apiId': plugin.get("api_id", None) }])
	
			elif namerx.search(plugin["name"]):
				if args.verbose:
					res.extend([ {"apiId": plugin.get("api_id", None), 'id': plugin['id'], 'name': plugin['name'], 'config': plugin['config'] } ])
				else:
					res.extend([{ 'name': plugin["name"], 'id': plugin["id"], 'apiId': plugin.get("api_id", None) }])
		
		def fetch_api_name(plugin):
			if not plugin["apiId"]: return {}
			res = Httplib.get("%s/apis/%s" % (URL, plugin['apiId']))
			if res['code'] != 'Success': return plugin
			return merge(plugin, { 'api': res['data']['name'] })

		results = ThreadPool(20).imap_unordered(fetch_api_name, res)

		for plugin in results:
			if not plugin: pass
			if not plugin.get("api"): print(json.dumps(plugin, indent=4))
			elif args.api_id:
				if(plugin["apiId"].encode('utf8') == args.api_id): print(json.dumps(plugin, indent=4))
			elif args.api:
				apirx = re.compile(re.escape(args.api), re.MULTILINE)
				if apirx.search(plugin["api"]): print(json.dumps(plugin, indent=4))
			else:
				print(json.dumps(plugin, indent=4))
		
class Upstream:
	def create(self):
		parser = CustomParser(description='create upstream with targets')
		parser.add_argument('--name', help='name for upstream url')
		parser.add_argument('--target', action='append', help='target urls multiple targets')
		parser.add_argument('--weight', action='append', type=int, default=[], help='weights for corresponding targets')
		
		args = parser.parse_args(sys.argv[3:])
		res = Httplib.post("%s/upstreams" % URL, { 'name': args.name })
		if res['code'] != 'Success': return

		result  = res['data']
		del(result['orderlist'])
		args.weight = dict((key, value) for key, value in enumerate(args.weight)) 
		targets = []
		for i, target in enumerate(args.target):
			weight = args.weight.get(i, 100)
			res = Httplib.post("%s/upstreams/%s/targets" % (URL, args.name), {'target': target, 'weight': weight})
			targets.append(res['data'])
		result['targets'] = targets
		print(json.dumps(result, indent=4))
	def update(self):
		parser = CustomParser(description='update upstreams with targets')
		parser.add_argument('--name', help='name for upstream url')
		parser.add_argument('--new_name', help='new name for upstream url', nargs='?')
		parser.add_argument('--target', action='append', help='target urls multiple targets')
		parser.add_argument('--weight', action='append', type=int, default=[], help='weights for corresponding targets')
		
		args = parser.parse_args(sys.argv[3:])
	
		name = args.name
		result = {"name": args.name}
		if args.new_name:
			args.name = args.new_name
			res = Httplib.patch("%s/upstreams/%s" % (URL, name), { 'name': args.name })
			if res['code'] != 'Success': return
			result = res['data']
			del(result["orderlist"])

		args.weight = dict((key, value) for key, value in enumerate(args.weight)) 
		targets = []
		for i, target in enumerate(args.target):
			weight = args.weight.get(i, 100)
			res = Httplib.post("%s/upstreams/%s/targets" % (URL, args.name), {'target': target, 'weight': weight})
			targets.append(res['data'])
		result['targets'] = targets
		print(json.dumps(result, indent=4))
	def delete(self):
		parser = CustomParser(description='find upstream with targets')
		parser.add_argument('--name', help='name for upstream url')
		args = parser.parse_args(sys.argv[3:])

		res = Httplib.delete("%s/upstreams/%s" % (URL, args.name))
		print(json.dumps(res, indent=4))
	def find(self):
		parser = CustomParser(description='find upstream with targets')
		parser.add_argument('--name', help='name for upstream url')
		
		args = parser.parse_args(sys.argv[3:])
		res = Httplib.get("%s/upstreams/%s" % (URL, args.name))
		res = res["data"]
		targets = Httplib.get("%s/upstreams/%s/targets" % (URL, args.name))
		targets = targets["data"]
		res = { "slots": res["slots"], "name": res["name"], "id": res["id"], "created_at": res["created_at"], "targets": targets["data"] }
		print(json.dumps(res, indent=4))

class CustomParser(argparse.ArgumentParser):
	def error(self, message):
		sys.stderr.write('error: %s\n' % message)
        	self.print_help()
		sys.exit(2)

class Url:
    @classmethod
    def set(self, url):
        data = "URL=%s" % url
        with open(".config", "w+") as f:
            f.write(data)
        return data
    
    @classmethod
    def get(self):
        with open(".config", "r") as f: line = f.read()
        if not line: return "http://localhost:8001"
        v = line.split('=').pop()
        return v

class Kaylo:
	def __init__(self):
		global URL
		if os.environ.get("URL"): URL = os.environ["URL"]
        elif Url.get(): URL = Url.get()

		parser = CustomParser(description='command line for kong', usage='''./kaylo <command> [<args>]
The most commonly used kaylo commands are:
	apis         find create update delete search for apis by name uri
	plugins      find create update delete search for plugins by api name or plugn id
	upstreams   find create update upstreams with target
''')
		parser.add_argument('command', help="subcommands to curd apis, plugins and upstreams")

		args = parser.parse_args(sys.argv[1:2])
		assert_prop(self, args.command, parser)
		getattr(self, args.command)()
    def set(self):
        parser = CustomParser(description='set kong url', usage='./kaylo.py set --url')
        parser.add_argument('--url', default="http://localhost:8001" help='set url with <hostname/ip>:<port>')
        args = parser.parse_args(sys.argv[2:3])
        Url.set(args.url)
	def apis(self):
		parser = CustomParser(description='create find update and delete api', usage=''' ./kaylo api [<nargs>] <command>
The most commonly use kaylo api commands are:
	create    create api with name upstream and uris
	update    update apis with name or id
	find	  find apis using api name
	delete	  delete api by name or id
	search    search apis by parts of uri or name
''')
		parser.add_argument('command', help='Subcommand for api')
		args = parser.parse_args(sys.argv[2:3])
		api = Api()
		assert_prop(api, args.command, parser)
		getattr(api, args.command)()
	def plugins(self):
		parser = CustomParser(description='create find update and delete plugin', usage=''' ./kaylo plugin [<nargs>] <command>
The most commonly use kaylo plugin commands are:
	create    create plugin for an api with name and config
	update    update plugins for api or with id
	find	  find plugins by id or api name
	delete	  delete plugins by id or name from api
	serach    search apis with plugins using part of plugin and api name
''')

		parser.add_argument('command', help='Subcommand for plugin')
		args = parser.parse_args(sys.argv[2:3])
		plugin = Plugin()
		assert_prop(plugin, args.command, parser)
		getattr(plugin, args.command)()
	def upstreams(self):
		parser = CustomParser(description='create find update and delete upstream')
		parser.add_argument('command', help='Subcommand for upstream')
		args = parser.parse_args(sys.argv[2:3])
		upstream = Upstream()
		assert_prop(upstream, args.command, parser)
		getattr(upstream, args.command)()

if __name__ == "__main__":
	Kaylo()

