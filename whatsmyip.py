#!/usr/bin/python

from urllib2 import Request, urlopen 
from urllib import urlencode
from re import match
import json

class QuerySelector:
  @classmethod
  def getElmById(self, dom, id):
    if dom.id == id:
      return dom
    for el in dom.children():
      v = self.getElmById(el, id)
      if v: return v
  @classmethod
  def getElmByClass(self, dom, klass):
    els = []
    if dom.className() == klass: els.append(dom)
    for el in dom.children():
      els.extend(self.getElmByClass(el, klass))
    return els
  @classmethod
  def getElmByTag(self, dom, tag):
    els = []
    if dom.tag == tag: els.append(dom)
    for el in dom.children():
      els.extend(self.getElmByTag(el, tag))
    return els
  @classmethod
  def childAt(self, dom, i):
    nodes = dom.children()
    if i <= len(nodes): return nodes[i]


class Node:
  def __init__(self, tag, type="element", klass=None, id=None, value=None):
    self.tag = tag
    self.type = type
    self.klass = klass
    self.value = value
    self.id = id
    self.nodes = None
  def hasattr(self, name):
    val = getattr(self, name, None)
    return True if val else False
  def children(self, i=None):
    return self.nodes or []
  def className(self):
    return self.klass or ""
  def text(self):
    values = []
    for node in self.children():
      if node.type == "text": values.extend([node.value or ""])
    return ' '.join(values)


class Parser:
  def __init__(self, data):
    self.data = data
    self.len = len(data)
    self.pos = 0
  def is_eof(self):
    return self.pos >= self.len
  def peek(self):
    return self.data[self.pos + 1]
  def ch(self):
    return self.data[self.pos]
  def next(self):
    self.pos += 1
    return self
  def eat_chars_while(self, fun):
    result = ""
    while(not self.is_eof() and fun(self.ch())):
      result += self.ch()
      self.next()
    return result
  def eat_white(self):
    while(not self.is_eof() and self.ch() in [" ", "\n"]): self.next()
  def parse_node(self):
    #if(self.ch() == '<' and self.peek() == '/'): return
    if(self.ch() == '<'): return self.parse_elm()
    return self.parse_txt()
  def parse_txt(self):
    text = self.eat_chars_while(lambda x: x != '<')
    return Node('', type='text', value = text)
  def parse_elm(self):
    self.next()
    selfclose = ["input", "img", "br"]
    tag = self.parse_tag()
    is_self_close = tag in selfclose
    attrs = self.parse_attrs()
    node = Node(tag, klass=attrs.get('class'), id=attrs.get('id'), value=attrs.get('value'))
    self.next()
    if is_self_close: return node

    node.nodes = self.parse_nodes()

    if self.ch() != '<': exit(1)
    if self.next().ch() != '/': exit(1)
    self.next()

    closetag = self.parse_tag()
    if closetag != tag: exit(1)

    self.eat_white()

    if self.ch() != '>': exit(1)
    self.next()
    return node
  def parse_tag(self):
    alnum = range(ord('a'), ord('z')) + range(0, 9) + [ord('-'), ord('_')]
    tag = self.eat_chars_while(lambda x: match('[\w\-]+', x)) 
    return tag
  def parse_attrs(self):
    attrs = {}
    while self.ch() != '>':
      self.eat_white()
      attrkey = self.parse_tag()
      #print("attrk", attrkey)
      #print("attrk", self.ch(), self.peek())
      attrs[attrkey] = ''
      if self.ch() == '=':
        self.next()
        attrval = self.parse_attr_val()
        attrs[attrkey] = attrval
        #print("attrv", attrval)
      #if self.ch() == '/' and self.peek() == '>': self.next()
    return attrs
  def parse_attr_val(self):
    startqt = self.ch()
    val = ''
    if(startqt == "\"" or startqt == "\'"):
      self.next()
      val = self.eat_chars_while(lambda x: x != startqt)
      self.next()
      return val
    while (not self.is_eof()) and self.ch() != '>':
      if self.ch() == ' ':
        return val
      if self.ch() == '/' and self.peek() == '>': self.next()
      else:
        val += self.ch()
        self.next()
    return val
  def parse_nodes(self):
    nodes = []
    while(not self.is_eof()):
      self.eat_white()
      if self.ch() == '<' and self.peek() == '/':
        break
      node = self.parse_node()
      nodes.extend([node])
    return nodes

class NodeToJson(json.JSONEncoder):
  def default(self, o):
    hash = { 'type': o.type, 'tag': o.tag, 'className': o.className(), 'id': o.id, 'children': [] }
    if o.value: hash['value'] = o.value
    for el in o.children():
      hash['children'].append(self.default(el))
    return hash

def assert_not_found(el):
  if not el:
    print("couldn't find ip, please use https://www.google.com/search?q=whats+my+ip")
    exit(1)

def request(url, query=''):
    req = Request("%s?%s" % (url, query), headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})

    try:
      res = urlopen(req)
      return res
    except Exception as e:
      print(e)
      exit(1)

def remove_doctype(data):
  return data.replace("<!doctype html>", "")

def remove_in_tags(data, tag):
  starttag = "<%s" % tag
  endtag = "</%s>" % tag

  headstart = data.find(starttag)
  headend   = data.find(endtag)
  newdata = ""

  if headstart == -1: return data
  if headstart != -1: newdata = data[:headstart]

  if headend < 0:
    temp = data[headstart + len(starttag) :]
    close_caret_index = temp.find('>') #considering it isn't an invalid html
    return data[headstart + len(starttag) + close_caret_index]
    
  if headend > -1: newdata = newdata + data[ headend + len(endtag) : ]
  
  if newdata.find(starttag) > -1:
    return remove_in_tags(newdata, tag)
  else:
    return newdata

def clean_html(data):
  newdata = remove_doctype(data)
  newdata = remove_in_tags(newdata, "head")
  newdata = remove_in_tags(newdata, "script")

  return newdata

data = urlencode({'q': 'whats my ip'})
html_string = request("https://www.google.com/search", data).read()

stuff = clean_html(html_string)
parser = Parser(stuff)
parent = Node('')
dom = parser.parse_nodes()
parent.nodes = dom

#print(json.dumps(parent, indent=2, cls=NodeToJson))
el = QuerySelector.getElmById(parent, "search")
assert_not_found(el)
ires = QuerySelector.getElmById(el, 'ires')
assert_not_found(ires)
gs = QuerySelector.getElmByClass(ires, 'g')
assert_not_found(gs)
first = gs[0]
assert_not_found(first)
div = QuerySelector.childAt(first, 0)
assert_not_found(div)
ipel = QuerySelector.childAt(div, 0)
assert_not_found(ipel)
ipel = QuerySelector.childAt(ipel, 0)
assert_not_found(ipel)
ip = ipel.text()

print("IP: %s" % ip)
