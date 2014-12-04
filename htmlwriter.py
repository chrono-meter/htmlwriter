#!/usr/local/bin/python3.4
# -*- coding: utf-8 -*-
"""\
htmlwriter - HTML with Python codes
===================================

This module is similar to `html <https://pypi.python.org/pypi/html>`_, but this provides:
    * support `with statement <https://docs.python.org/3/reference/compound_stmts.html#with>`_
    * support shorthand (Bootstrap is supported)
    * simple and consistent API
"""
import warnings
import keyword
from io import StringIO
import re
import fnmatch
from os.path import commonprefix
import textwrap
import contextlib
import functools
import collections
# from lxml import etree  # lxml doesn't support customizing entity handler
from xml.etree import ElementTree as etree
import xml.sax.saxutils  # or html.escape
import json
import unittest


__version__ = '1.0.0'
__author__ = __author_email__ = 'chrono-meter@gmx.net'
__license__ = 'PSF'
__url__ = 'http://pypi.python.org/pypi/?'
# http://pypi.python.org/pypi?%3Aaction=list_classifiers
__classifiers__ = [i.strip() for i in '''\
    Development Status :: 4 - Beta
    Environment :: Web Environment
    Intended Audience :: Developers
    License :: OSI Approved :: Python Software Foundation License
    Operating System :: OS Independent
    Programming Language :: Python :: 3.4
    Topic :: Internet :: WWW/HTTP
    Topic :: Software Development :: Libraries :: Python Modules
    Topic :: Text Processing :: Markup
    Topic :: Text Processing :: Markup :: HTML
    Topic :: Text Processing :: Markup :: XML
    '''.strip().splitlines()]
__all__ = ()
#: HTML 4.01 strict doctype
html_4_01_strict = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
#: HTML 4.01 transitional doctype
html_4_01_transitional = \
    '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">'
#: HTML 4.01 frameset doctype
html_4_01_frameset = \
    '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN" "http://www.w3.org/TR/html4/frameset.dtd">'
#: XHTML 1.0 doctype
xhtml_1_0_strict = \
    '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">'
#: XHTML 1.0 transitional doctype
xhtml_1_0_transitional = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"' \
                         ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
#: XHTML 1.0 frameset doctype
xhtml_1_0_frameset = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN"' \
                     ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd">'
#: XHTML 1.1 doctype
xhtml_1_1 = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">'


def parse_xml(data):
    data = re.sub('&([A-Za-z0-9]+);', '&amp;\\1;', data)

    # In Python 3, it's unable to override `xml.etree.ElementTree.XMLParser` expat handler.
    parser = etree.XMLParser()
    parser.entity['amp'] = '&'
    # parser.entity.update(html.entities.html5)

    parser.feed(data)
    return parser.close()


class TagMethodHelper:
    """Method wrapper for some features:

        * Register and cleanup :attr:`~htmlwriter.XMLWriter._pending`.
        * `Conetxt manager` without function calling.
    """

    def __init__(self, method, *args, **kwargs):
        """
        :param function method: original function
        :param args: bound positional arguments
        :param kwargs: bound keyword arguments
        """
        self.method = method
        self.args = args
        self.kwargs = kwargs
        self.context_manager = None
        functools.update_wrapper(self, method)

    @classmethod
    def decorator(cls, *args, **kwargs):
        def helper(method):
            return cls(method, *args, **kwargs)
        return helper

    def __get__(self, obj, type=None):
        result = self.__class__(self.method.__get__(obj, type), *self.args, **self.kwargs)
        result.__name__ = self.__name__
        result.__doc__ = self.__doc__
        return result

    def __str__(self):
        return str(self.method)

    def __repr__(self):
        return repr(self.method)

    def __call__(self, *args, **kwargs):
        method = self.method  # get bound method
        args = self.args + args
        kwargs = dict(self.kwargs, **kwargs)
        self = method.__self__

        @contextlib.contextmanager
        def helper():
            assert self._pending is pending, '%s' % (self._pending, )
            self._pending = None
            with method(*args, **kwargs) as result:
                yield result

        self.write('')  # consume self._pending
        assert self._pending is None, '%s' % (self._pending, )

        self._pending = pending = helper()
        return pending

    def __enter__(self):
        assert self.context_manager is None
        self.context_manager = contextlib.ExitStack()
        return self.context_manager.enter_context(self.method(*self.args, **self.kwargs))

    def __exit__(self, *args):
        del args
        assert self.context_manager
        self.context_manager.close()
        self.context_manager = None


class PreProcessor(type):
    """Metaclass for process :attr:`~htmlwriter.XMLWriter._template`.

    This is a metaclass of :class:`~htmlwriter.XMLWriter`.
    """
    def __new__(cls, name, bases, classdict):
        klass = type.__new__(cls, name, bases, dict(classdict))
        cls.compile_template(klass)
        return klass

    @classmethod
    def compile_template(cls, writer_class):
        """Generate methods from string.

        :param XMLWriter writer_class: target class
        """
        doc = parse_xml(writer_class._template)

        for e in doc:
            e.tail = ''

            if e.tag == etree.Comment:
                continue

            name = cls.get_name(doc.attrib.get('prefix', ''), e)
            # if hasattr(writer_class, name):
            #     warnings.warn('%s conflict: %s' % (name, etree.tostring(e, encoding='unicode')))
            #     continue

            if len(e):
                method = cls.make_from_deep(e)

            else:
                method = cls.make_from_shallow(e)

            method = TagMethodHelper(method)
            method.__name__ = name
            method._signature = '[text: str, ]**attributes'
            setattr(writer_class, name, method)

    @classmethod
    def get_name(cls, prefix: str, e: etree.Element) -> str:
        """Generate method name from element.

        :param str prefix: method name prefix
        :param Element e: source element
        :return: method name
        :rtype: str
        """
        common_class_name = commonprefix(e.attrib.get('class', '').split())

        if 'id' in e.attrib:
            name = e.attrib.pop('id')
        elif common_class_name:
            name = common_class_name
        else:
            name = e.tag

        name = prefix + re.sub('\\W+', '_', name.strip().lower())

        if keyword.iskeyword(name):
            warnings.warn('renamed %s -> %s' % (name, name + '_'))
            name += '_'

        return name

    @classmethod
    def make_from_shallow(cls, e: etree.Element):
        """Generate method from element.

        :param Element e: source element
        :return: not bound method
        :rtype: function
        """
        tag = e.tag
        default_attributes = e.attrib.copy()
        default_content = e.text

        def result(self, *args, **attributes):
            if not args:
                args = (default_content, )
            return self._tag(tag, *args, **self._merge_attributes(tag, default_attributes, attributes))

        result.__doc__ = 'Write or enter "%s".\nSee :func:`~XMLWriter.tag`.' % (
            etree.tostring(e, encoding='unicode').replace('&amp;', '&'), )
        return result

    @classmethod
    def make_from_deep(cls, root: etree.Element):
        """Generate method from element.

        :param Element e: source element
        :return: not bound method
        :rtype: function
        """
        prefix = 'template-'

        def result(self, *args, **attributes):
            pause = object()

            @contextlib.contextmanager
            def walk(node):
                if node.tag == prefix + 'content':
                    if args:
                        self.text(*args)
                    else:
                        self.write(node.text or '')
                    yield
                    self.write(node.tail)
                    return

                elif node.tag == prefix + 'yield':
                    yield pause
                    return

                elif node.tag.startswith(prefix):
                    raise NotImplementedError(
                        'not supported element: %s' % (etree.tostring(node, encoding='unicode'), ))

                imported_attributes = {}
                handlable_attributes = {}
                for name, value in node.attrib.items():
                    if not name.startswith(prefix):
                        imported_attributes[name] = value
                    else:
                        name = name[len(prefix):]
                        handlable_attributes[name] = value

                for name, value in handlable_attributes.items():
                    handler = getattr(cls, 'handle_' + re.sub('\\W+', '_', name))
                    imported_attributes = \
                            self._merge_attributes(node.tag, imported_attributes, handler(value, attributes))

                with self.tag(node.tag, **imported_attributes):
                    self.write(node.text or '')

                    yielded = False
                    for i in node:
                        with walk(i) as _:
                            if _ is pause:
                                assert not yielded
                                yielded = True
                                yield pause
                    if not yielded:
                        yield

                self.write(node.tail or '')

            return walk(root)

        tmpl = textwrap.indent(textwrap.dedent(etree.tostring(root, encoding='unicode').replace('&amp;', '&')), '    ')
        result.__doc__ = 'Write or enter template:\n\n.. code-block:: xml\n\n' + tmpl
        # result.__doc__ = etree.tostring(root, encoding='unicode').replace('&amp;', '&')
        return result

    @classmethod
    def handle_attributes(cls, patterns: str, input_attributes: dict) -> dict:
        """Handle `template-attributes`.

        Pattern is glob style and `-` prefix means exclude pattern.

        :param str patterns: handling attribute value
        :param dict input_attributes: source attributes
        :return: filtered attributes
        :rtype: dict
        """
        includes = []
        excludes = []

        patterns = patterns.split(',') if ',' in patterns else patterns.split()
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern.startswith('-'):
                includes.append(fnmatch.translate(pattern))
            else:
                excludes.append(fnmatch.translate(pattern[1:]))

        includes = re.compile('^(' + '|'.join(includes) + ')$', flags=re.IGNORECASE)
        excludes = re.compile('^(' + '|'.join(excludes) + ')$', flags=re.IGNORECASE)

        result = {}

        for name, value in input_attributes.items():
            if excludes.match(name):
                continue
            elif includes.match(name):
                result[name] = value

        return result

    @classmethod
    def handle_attribute_map_class(cls, patterns: str, input_attributes: dict) -> dict:
        """Handle `template-attribute-map-class`.

        :param str patterns: handling attribute value (ex. 'active, disabled as btn-disabled')
        :param dict input_attributes: source attributes
        :return: filtered attributes
        :rtype: dict
        """
        classes = set()

        for line in patterns.split(','):
            match = re.search('(\\S+)\\s+as\\s+(\\S+)', line)
            if match:
                name, alias = match.groups()
            else:
                name = alias = line.strip()

            if input_attributes.get(name):
                classes.add(alias)

        return {'class': ' '.join(classes)} if classes else {}


class XMLWriter(StringIO, metaclass=PreProcessor):
    """\
    Base writer class. This provides useful functions for writing XML content.

    Simplest usage:
        >>> writer = XMLWriter('html')
        >>> with writer.tag('body'):
        ...     writer.tag('p', 'hello, world')
        >>> writer.getvalue()
        '<html><body><p>hello, world</p></body></html>'

    Note that :meth:`~tag` returns
    `context manager <https://docs.python.org/3/library/stdtypes.html#context-manager-types>`_.
    So you can use `with statement <https://docs.python.org/3/reference/compound_stmts.html#with>`_ with it.
    """
    _signature = '[doctype: str, ]root_tag: str, **root_attributes'
    #: XML declaration string or `None`. This will be written before content on :meth:`~getvalue`.
    declaration = None
    #: XML doctype string or `None`. This will be written before content on :meth:`~getvalue`.
    doctype = None
    #: root tag name
    root_tag = 'xml'
    #: root tag attributes
    root_attributes = {}

    #: Generate method from string quickly.
    #: See source of :class:`~htmlwriter.PreProcessor` for implementation.
    _template = '<template></template>'
    #: Set of tag name that does not require end tag.
    #: See source of :meth:`~htmlwriter.XMLWriter._tag` for implementation.
    _no_end_tags = set()
    #: Set of tag name that must have end tag.
    #: See source of :meth:`~htmlwriter.XMLWriter._tag` for implementation.
    _require_end_tags = set()
    #: Tuple of boolean attribute (attribute without value. ex <input disabled/>).
    #: Item may be `(None, 'attribute_name')` or `('tag_name', 'attribute_name')`.
    _boolean_attributes = set()
    #: Tuple of attribute renaming pattern.
    #: Item may be `(pattern, repl)` (1st and 2nd argument for `re.sub`).
    #: See source of :meth:`~htmlwriter.XMLWriter._merge_attributes` for implementation.
    _attribute_rename_patterns = (
        ('^(xml|xmlns)_(.+)', '\\1:\\2'),
    )
    #: See source of :meth:`~htmlwriter.XMLWriter._merge_attributes` for implementation.
    _merge_attribute_handlers = {
        # (None, 'attribute_name'): handler(old_value, new_value),
        # ('tag_name', 'attribute_name'): handler(old_value, new_value),
    }
    #: Pending writing state as `context manager`. This must be not executed, execute in next
    #: :meth:`~htmlwriter.XMLWriter.write`.
    _pending = None

    def __init__(self, *args, **root_attributes):
        """
        :param doctype: XML doctype
        :type doctype: str or None
        :param str root_tag: root tag name
        :param root_attributes: root tag attributes
        """
        super().__init__()

        assert len(args) > 0, 'no root tag'
        assert len(args) <= 2, 'too many arguments'

        if len(args) == 1:
            self.root_tag = args[0]

        else:
            assert args[0].startswith('<!DOCTYPE ') and args[0].endswith('>')
            self.doctype = args[0]
            self.root_tag = args[1]

        self.root_attributes = root_attributes

    def getvalue(self, *, declaration: bool=True, doctype: bool=True, root_tag: bool=True) -> str:
        """Get the written string.

        :param declaration: XML declaration output flag or XML declaration
        :type declaration: bool or str
        :param doctype: XML doctype output flag or XML doctype
        :type doctype: bool or str
        :param bool root_tag: root tag output flag
        :return: XML string
        :rtype: str

        See :meth:`io.StringIO.getvalue`.
        """
        self.write('')  # consume self._pending

        header = ''

        if declaration:
            if isinstance(declaration, str):
                header += declaration + '\n'
            elif self.declaration:
                header += self.declaration + '\n'

        if doctype:
            if isinstance(doctype, str):
                header += doctype + '\n'
            elif self.doctype:
                header += self.doctype + '\n'

        content = super().getvalue()

        if root_tag:
            return '%s%s%s</%s>' % (
                header,
                self._get_begin_tag(self.root_tag, **self.root_attributes),
                content,
                self.root_tag,
            )
        else:
            return content

    def write(self, s: str):
        """Write text with no escaping.

        See :meth:`io.StringIO.getvalue`.
        """
        # execute pending `context manager`
        if self._pending:
            with self._pending:
                pass
            # NOTE: required explicit clearing at top of `context manager` (`self._pending = None`)
        return super().write(s)

    def _merge_attributes(self, tag: str, *args) -> dict:
        """Merge and rename attributes.

        :param str tag: tag name string
        :param args: tuple of attributes, later is prior
        :type args: tuple(dict)
        :return: new merged attributes `dict`
        :rtype: dict
        """
        result = {}

        for attributes in args:
            assert isinstance(attributes, collections.Mapping)

            for name, value in attributes.items():
                # do renaming
                for pattern, repl in self._attribute_rename_patterns:
                    name = re.sub(pattern, repl, name)

                if name in result:
                    # call merge handler
                    if (tag, name) in self._merge_attribute_handlers:
                        result[name] = self._merge_attribute_handlers[tag, name](result[name], value)
                    elif (None, name) in self._merge_attribute_handlers:
                        result[name] = self._merge_attribute_handlers[None, name](result[name], value)
                    else:
                        result[name] = value
                else:
                    result[name] = value

        return result

    def _get_begin_tag(self, tag: str, **attributes) -> str:
        """Get a string of begin tag.

        :param str tag: tag name
        :param attributes: tag attributes
        :return: '<tag ...>' or '<tag>' if attributes are empty
        :rtype: str
        """
        result = ''

        attributes = self._merge_attributes(tag, attributes)  # do renaming and merging

        for name, value in attributes.items():
            s = self._stringify_attribute(tag, name, value)
            if s:
                result += ' ' + s

        return '<' + tag + result + '>'

    def _stringify_attribute(self, tag: str, name: str, value) -> str:
        """Get a string of attribute.

        :param str tag: tag name
        :param str name: attribute name
        :param value: attribute value
        :return: representation string for embedding begin tag
        :rtype: str
        """
        if (tag, name) in self._boolean_attributes or (None, name) in self._boolean_attributes:
            if value:
                return name

        else:
            if isinstance(value, str):
                pass

            elif isinstance(value, bytes):
                raise TypeError('not supported %r' % (value, ))

            elif isinstance(value, bool):
                value = 'true' if value else 'false'

            elif isinstance(value, (int, float)):
                value = str(value)

            elif isinstance(value, collections.Mapping):
                raise NotImplementedError('')  # TODO: dict attribute

            elif isinstance(value, collections.Iterable):
                value = ' '.join(value)

            else:
                value = str(value)

            return '%s=%s' % (name, xml.sax.saxutils.quoteattr(value))

        return ''

    def _tag(self, *args, **attributes):
        """Non wrapped version of :meth:`~htmlwriter.XMLWriter.tag`. Don't call this function directly. This function
        doesn't register and cleanup :attr:`~htmlwriter.XMLWriter._pending`.

        :param str tag: tag name
        :param str text: text content, this will be written by :meth:`~htmlwriter.XMLWriter.text`
        :param attributes: attributes
        :return: `context manager <https://docs.python.org/3/library/stdtypes.html#context-manager-types>`_
        """
        assert len(args) > 0, 'no tag'
        assert len(args) <= 2, 'too many arguments'
        if len(args) == 1:
            tag = args[0]
            content = None
        else:
            tag, content = args
        assert isinstance(tag, str) and tag, 'not expected: %s' % (tag, )

        @contextlib.contextmanager
        def helper():
            self.write(self._get_begin_tag(tag, **attributes))
            if content:
                self.text(content)  # NOTE: Use .write() for content without escaping

            wrote = self.tell()

            yield

            if not content and wrote == self.tell() and self._pending is None:
                if tag in self._require_end_tags:
                    self.write('</%s>' % (tag, ))
                elif tag in self._no_end_tags:
                    pass
                else:
                    self.seek(self.tell() - 1)
                    self.write('/>')
            else:
                assert tag not in self._no_end_tags, '"%s" tag cannot contain content' % (tag, )
                self.write('</%s>' % (tag, ))

        return helper()

    tag = TagMethodHelper(_tag)
    tag.__doc__ = """Write or enter a tag.

        :param str tag: tag name
        :param str text: text content, this will be written by :func:`~htmlwriter.XMLWriter.text`
        :param attributes: attributes
        :return: `context manager <https://docs.python.org/3/library/stdtypes.html#context-manager-types>`_
        """

    def text(self, s: str):
        """Write text with escaping '<' and '>'.
        """
        # self.write(xml.sax.saxutils.escape(s))
        self.write(s.replace(">", "&gt;").replace("<", "&lt;"))

    def comment(self, s: str):
        """Write comment.
        """
        assert '-->' not in s
        self.write('<!--%s-->' % (s, ))

    def cdata(self, s: str):
        """Write cdata.
        """
        assert ']]>' not in s
        # TODO: see xml.etree.ElementTree._escape_cdata
        #       .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.write('<![CDATA[%s]]>' % (s, ))


# TODO: html pretty printing (like: etree._serialize['html'] = etree._serialize_html, etree.tostring(*, method='html'))


class XmlTestCase(unittest.TestCase):

    def assertXmlEqual(self, first, second, msg=None, type=None):
        # https://github.com/formencode/formencode/blob/master/formencode/doctest_xml_compare.py
        # def parse(data):
        #     class Element(etree.Element):
        #         doctype = None
        #
        #     class TreeBuilder(etree.TreeBuilder):
        #         doctype = None
        #
        #         def doctype(self, name, pubid, system):
        #             self.doctype = name, pubid, system
        #
        #         def close(self):
        #             result = super().close()
        #             # result.doctype = self.doctype
        #             return result
        #
        #     parser = etree.XMLParser(target=TreeBuilder(Element))
        #     parser.entity['amp'] = '&'
        #     parser.feed(re.sub('&([A-Za-z0-9]+);', '&amp;\\1;', data))
        #     return parser.close()

        def element(x):
            if isinstance(x, str):
                x = parse_xml(x)
            self.assertIsInstance(x, etree.Element)
            return x

        first = element(first)
        second = element(second)

        self.assertEqual(first.tag, second.tag)
        # self.assertEqual(getattr(first, 'doctype', None), getattr(second, 'doctype', None))

        if type is None:
            type = re.sub('^\{.+\}', '', first.tag.lower())

        for a, b in ((first.attrib, second.attrib), (second.attrib, first.attrib)):
            for name, value in a.items():
                if type == 'html' and name == 'class':
                    self.assertSetEqual(set(value.split()), set(b.get(name, '').split()))
                else:
                    self.assertIn(name, b)
                    self.assertEqual(value.strip(), b[name].strip())
        # self.assertSetEqual(set(first.attrib), set(second.attrib))
        # for name, value in first.attrib.items():
        #     if type == 'html' and name == 'class':
        #         self.assertSetEqual(set(value.split()), set(second.attrib[name].split()))
        #     else:
        #         self.assertEqual(value.strip(), second.attrib[name].strip())

        self.assertMultiLineEqual((first.text or '').strip(), (second.text or '').strip())
        self.assertMultiLineEqual((first.tail or '').strip(), (second.tail or '').strip())

        first = [i for i in first if i.tag is not etree.Comment]
        second = [i for i in second if i.tag is not etree.Comment]
        self.assertEqual(len(first), len(second))
        for i, j in zip(first, second):
            self.assertXmlEqual(i, j, msg=msg, type=type)


def merge_class(*classes):
    result = set()

    for class_ in classes:
        result.update(class_.split() if isinstance(class_, str) else class_)

    return result


class HTMLWriter(XMLWriter):
    """Helper class for writing HTML.
    """
    _signature = '[doctype: str, ]**root_attributes'
    _template = '''<template>
        <a href="#"/>
        <abbr/>
        <acronym/>
        <address/>
        <applet/>
        <area/>
        <b/>
        <base/>
        <basefont/>
        <bdo/>
        <big/>
        <blockquote/>
        <body/>
        <br/>
        <button/>
        <caption/>
        <center/>
        <cite/>
        <code/>
        <col/>
        <colgroup/>
        <dd/>
        <del/>
        <dfn/>
        <dir/>
        <div/>
        <dl/>
        <dt/>
        <em/>
        <fieldset/>
        <font/>
        <footer/>
        <form/>
        <frame/>
        <frameset/>
        <h1/>
        <h2/>
        <h3/>
        <h4/>
        <h5/>
        <h6/>
        <head/>
        <hr/>
        <html/>
        <i/>
        <iframe/>
        <img/>
        <input/>
        <ins/>
        <kbd/>
        <label/>
        <legend/>
        <li/>
        <link/>
        <map/>
        <menu/>
        <meta/>
        <noframes/>
        <noscript/>
        <object/>
        <ol/>
        <optgroup/>
        <option/>
        <p/>
        <param/>
        <pre/>
        <q/>
        <s/>
        <samp/>
        <script/>
        <select/>
        <small/>
        <span/>
        <strike/>
        <strong/>
        <style/>
        <sub/>
        <sup/>
        <table/>
        <tbody/>
        <td/>
        <textarea/>
        <tfoot/>
        <th/>
        <thead/>
        <title/>
        <tr/>
        <tt/>
        <u/>
        <ul/>
        <var/>
    </template>'''
    _no_end_tags = {  # from xml.etree.ElementTree.HTML_EMPTY
        'area',
        'base',
        'basefont',
        'br',
        'col',
        'frame',
        'hr',
        'img',
        'input',
        'isindex',
        'link',
        'meta',
        'param',
    }
    _require_end_tags = {
        'script',
        'textarea',
        'span',
        'div',
    }
    _attribute_rename_patterns = XMLWriter._attribute_rename_patterns + (
        ('^class_$', 'class'),
    )
    _merge_attribute_handlers = {
        (None, 'class'): merge_class,
    }
    _boolean_attributes = {
        ('fieldset', 'disabled'),
        ('button', 'disabled'),
        ('input', 'checked'),
        ('input', 'required'),
        ('input', 'multiple'),
        ('input', 'disabled'),
        ('input', 'readonly'),
        ('option', 'selected'),
        ('select', 'required'),
        ('select', 'multiple'),
    }

    def __init__(self, *args, **root_attributes):
        """
        :param doctype: XML doctype
        :type doctype: str or None
        :param root_attributes: root tag attributes
        """
        args += ('html', )
        super().__init__(*args, **root_attributes)

    def scriptdata(self, **variables):
        """Write "<script>name1 = value1, name2 = value2, ...</script>" with escaping '<' and '>'.
        """
        content = ','.join(
            '%s = %s' % (k, json.dumps(v, separators=(',', ':')).replace('<', '\\x3c').replace('>', '\\x3e'))
            for k, v in variables.items())
        self.script(content)


class XHTMLWriter(HTMLWriter):
    """Helper class for writing XHTML.
    """
    _no_end_tags = set()


class HTML5Writer(HTMLWriter):
    """Helper class for writing HTML5.
    """
    _signature = '**root_attributes'
    _template = '''<template>
        <a href="#"/>
        <abbr/>
        <address/>
        <area/>
        <article/>
        <aside/>
        <audio/>
        <b/>
        <base/>
        <bdi/>
        <bdo/>
        <blockquote/>
        <body/>
        <br/>
        <button/>
        <canvas/>
        <caption/>
        <cite/>
        <code/>
        <col/>
        <colgroup/>
        <datalist/>
        <dd/>
        <del/>
        <details/>
        <dfn/>
        <dialog/>
        <div/>
        <dl/>
        <dt/>
        <em/>
        <embed/>
        <fieldset/>
        <figcaption/>
        <figure/>
        <footer/>
        <form/>
        <h1/>
        <h2/>
        <h3/>
        <h4/>
        <h5/>
        <h6/>
        <head/>
        <header/>
        <hgroup/>
        <hr/>
        <html/>
        <i/>
        <iframe/>
        <img/>
        <input/>
        <ins/>
        <kbd/>
        <keygen/>
        <label/>
        <legend/>
        <li/>
        <link/>
        <main/>
        <map/>
        <mark/>
        <menu/>
        <menuitem/>
        <meta/>
        <meter/>
        <nav/>
        <noscript/>
        <object/>
        <ol/>
        <optgroup/>
        <option/>
        <output/>
        <p/>
        <param/>
        <pre/>
        <progress/>
        <q/>
        <rp/>
        <rt/>
        <ruby/>
        <s/>
        <samp/>
        <script/>
        <section/>
        <select/>
        <small/>
        <source/>
        <span/>
        <strong/>
        <style/>
        <sub/>
        <summary/>
        <sup/>
        <table/>
        <tbody/>
        <td/>
        <textarea/>
        <tfoot/>
        <th/>
        <thead/>
        <time/>
        <title/>
        <tr/>
        <track/>
        <u/>
        <ul/>
        <var/>
        <video/>
        <wbr/>
    </template>'''
    _attribute_rename_patterns = HTMLWriter._attribute_rename_patterns + (
        ('^(data|aria)_(.+)', '\\1-\\2'),
    )

    def __init__(self, **root_attributes):
        """
        :param root_attributes: root tag attributes
        """
        super().__init__('<!DOCTYPE html>', **root_attributes)


class Bootstrap3Writer(HTML5Writer):
    """Helper class for writing HTML5 with `Bootstrap3 <http://getbootstrap.com/>`_.
    """

    @TagMethodHelper
    def bs_glyphicon(self, name: str, **attributes):
        """Write or enter "<span class="glyphicon glyphicon-`name`" aria-hidden="true"/>".
        See :func:`~XMLWriter.tag`.
        """
        return self.span(**self._merge_attributes(
            'span',
            dict(class_={'glyphicon', 'glyphicon-%s' % (name, )}, aria_hidden=True),
            attributes))

    _template = '''<template prefix="bs_">
        <div class="container"/>
        <div class="container-fluid"/>
        <div class="row"/>
        Typography:
            Lead body copy:
                <p class="lead"/>
            Alignment classes:
                <p class="text-left"/>
                <p class="text-center"/>
                <p class="text-right"/>
                <p class="text-justify"/>
                <p class="text-nowrap"/>
            Transformation classes:
                <p class="text-lowercase"/>
                <p class="text-uppercase"/>
                <p class="text-capitalize"/>
            Blockquote options:
                <blockquote class="blockquote-reverse"/>
            Lists:
                <ul id="ul-unstyled" class="list-unstyled"/>
                <ul id="ul-inline" class="list-inline"/>
                <ol id="ol-unstyled" class="list-unstyled"/>
                <ol id="ol-inline" class="list-inline"/>
                <dl class="dl-horizontal"/>
            Tables:
                <table class="table"/>
                <table id="table-striped" class="table table-striped"/>
                <table id="table-bordered" class="table table-bordered"/>
                <table id="table-hover" class="table table-hover"/>
                <table id="table-condensed" class="table table-condensed"/>
                <div class="table-responsive">
                    <table class="table" template-attributes="*">
                        <template-content/>
                        <template-yield/>
                    </table>
                </div>
        Forms:
            <form id="form" role="form"/>
            <form class="form-inline" role="form"/>
            <form class="form-horizontal" role="form"/>
            <div class="form-group"/>
            <p class="help-block"/>
            <input id="input" class="form-control"/>
            <textarea id="textarea" class="form-control"/>
            <select id="select" class="form-control"/>
            <p class="form-control-static"/>
            <label class="control-label"/>
            <div class="checkbox">
                <label>
                    <input type="checkbox" template-attributes="*"/>
                    <template-content/>
                    <template-yield/>
                 </label>
            </div>
            <div class="radio">
                <label>
                    <input type="radio" template-attributes="*"/>
                    <template-content/>
                    <template-yield/>
                </label>
            </div>
            <label class="checkbox-inline">
                <input type="checkbox" template-attributes="*"/>
                <template-content/>
                <template-yield/>
            </label>
            <label class="radio-inline">
                <input type="radio" template-attributes="*"/>
                <template-content/>
                <template-yield/>
            </label>
        Buttons:
            <button id="btn-default" type="button" class="btn btn-default"/>
            <button id="btn-primary" type="button" class="btn btn-primary"/>
            <button id="btn-success" type="button" class="btn btn-success"/>
            <button id="btn-info" type="button" class="btn btn-info"/>
            <button id="btn-warning" type="button" class="btn btn-warning"/>
            <button id="btn-danger" type="button" class="btn btn-danger"/>
            <button id="btn-link" type="button" class="btn btn-link"/>
        Images:
            <img class="img-responsive"/>
            <img class="img-rounded"/>
            <img class="img-circle"/>
            <img class="img-thumbnail"/>
        Helper classes:
            Contextual colors:
                <p class="text-muted"/>
                <p class="text-primary"/>
                <p class="text-success"/>
                <p class="text-info"/>
                <p class="text-warning"/>
                <p class="text-danger"/>
            Contextual backgrounds:
                <p class="bg-primary"/>
                <p class="bg-success"/>
                <p class="bg-info"/>
                <p class="bg-warning"/>
                <p class="bg-danger"/>
            Close icon:
                <button type="button" class="close" template-attributes="*">
                    <span aria-hidden="true">&times;</span>
                    <span class="sr-only">
                        <template-content>Close</template-content>
                    </span>
                    <template-yield/>
                </button>
            Carets:
                <span class="caret"></span>
            Quick floats:
                <div class="pull-left"/>
                <div class="pull-right"/>
            Center content blocks:
                <div class="center-block"/>
            Clearfix:
                <div class="clearfix"/>
        <li id="menuitem" role="presentation" template-attribute-map-class="active, disabled">
            <a href="#" role="menuitem" tabindex="-1" template-attributes="*, -active, -disabled">
                <template-content/>
                <template-yield/>
            </a>
        </li>
        Dropdowns:
            <div class="dropdown"/>
            TODO: aria-expanded="true|false"
            <button id="dropdown-toggle" type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown"/>
            <ul class="dropdown-menu" role='menu'/>
            <ul id="dropdown-menu-right" class="dropdown-menu dropdown-menu-right" role="menu"/>
            <li class="dropdown-header" role="presentation"/>
            <li class="divider" role="presentation"/>
        Button groups:
            <div class="btn-group" role="group"/>
            <div class="btn-toolbar" role="toolbar"/>
            <div class="btn-group-vertical" role="group"/>
            <div id="btn-group-justified" class="btn-group btn-group-justified" role="group"/>
        Input groups:
            <div class="input-group"/>
            <div id="input-group-lg" class="input-group input-group-lg"/>
            <div id="input-group-sm" class="input-group input-group-sm"/>
            <span class="input-group-addon"/>
            <span class="input-group-btn">
                <button class="btn btn-default" type="button" template-attributes="*">
                    <template-content/>
                    <template-yield/>
                </button>
            </span>
            ...
        Navs:
            <ul id="nav-tabs" class="nav nav-tabs"/>
            <ul id="nav-pills" class="nav nav-pills"/>
            <ul id="nav-pills-stacked" class="nav nav-pills nav-stacked"/>
            <ul id="nav-tabs-justified" class="nav nav-tabs nav-justified"/>
            <ul id="nav-pills-justified" class="nav nav-pills nav-justified"/>
            <li id="nav-dropdown" role="presentation" class="dropdown"/>
        Navbar:
            <nav id="navbar-default" class="navbar navbar-default" role="navigation"/>
            <div class="navbar-header"/>
            ...
        Pager:
            <ul class="pager"/>
            <li class="previous" template-attribute-map-class="disabled">
                <a href="#" template-attributes="*, -disabled">
                    <span aria-hidden="true">&larr;</span>
                    <template-content/>
                    <template-yield/>
                </a>
            </li>
            <li class="next" template-attribute-map-class="disabled">
                <a href="#" template-attributes="*, -disabled">
                    <template-content/>
                    <template-yield/>
                    <span aria-hidden="true">&rarr;</span>
                </a>
            </li>
        Labels:
            <span id="label-default" class="label label-default"/>
            <span id="label-primary" class="label label-primary"/>
            <span id="label-success" class="label label-success"/>
            <span id="label-info" class="label label-info"/>
            <span id="label-warning" class="label label-warning"/>
            <span id="label-danger" class="label label-danger"/>
        Badges:
            <span class="badge"/>
        Jumbotron:
            <div class="jumbotron"/>
        Page header:
            <div class="page-header"/>
        Alerts:
            <div id="alert-success" class="alert alert-success" role="alert"/>
            <div id="alert-info" class="alert alert-info" role="alert"/>
            <div id="alert-warning" class="alert alert-warning" role="alert"/>
            <div id="alert-danger" class="alert alert-danger" role="alert"/>
        Panel:
            <div id="panel-primary" class="panel panel-primary"/>
            <div id="panel-success" class="panel panel-success"/>
            <div id="panel-info" class="panel panel-info"/>
            <div id="panel-warning" class="panel panel-warning"/>
            <div id="panel-danger" class="panel panel-danger"/>
            <div class="panel-heading"/>
            <div class="panel-body"/>
            <div class="panel-footer"/>
        Modal:
            .fade is removed
            <div id="modal-dialog" class="modal" tabindex="-1" role="dialog" aria-hidden="true" template-attributes="*">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <template-content/>
                        <template-yield/>
                    </div>
                </div>
            </div>
            <div id="modal-dialog-lg" class="modal" tabindex="-1" role="dialog" aria-hidden="true" template-attributes="*">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <template-content/>
                        <template-yield/>
                    </div>
                </div>
            </div>
            <div id="modal-dialog-sm" class="modal" tabindex="-1" role="dialog" aria-hidden="true" template-attributes="*">
                <div class="modal-dialog modal-sm">
                    <div class="modal-content">
                        <template-content/>
                        <template-yield/>
                    </div>
                </div>
            </div>
            <div class="modal-header"/>
            <div class="modal-body"/>
            <div class="modal-footer"/>
            <button id="modal-close-icon" type="button" class="close" data-dismiss="modal">
                <span aria-hidden="true">&times;</span>
                <span class="sr-only">
                    <template-content>Close</template-content>
                </span>
                <template-yield/>
            </button>
            <button id="modal-close-button" type="button" class="btn btn-default" data-dismiss="modal">
                <template-content>Close</template-content>
                <template-yield/>
            </button>
    </template>'''
