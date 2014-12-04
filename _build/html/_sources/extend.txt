Custom writer
=============

Template
--------

Easiest way, you can create shorthand method from template.

.. code-block:: python

    from htmlwriter import XMLWriter

    class CustomWriter(XMLWriter):
        _template = '''<template prefix="my_">

            most simple example:
                <tag1/>

            with default attributes:
                <tag2 attr1="default value"/>

            nested:
                <wrap>
                    <tag3 template-attributes="*">
                        <template-content/>
                        <template-yield/>
                    </tag3>
                </wrap>

        </template>'''


Naming convention
~~~~~~~~~~~~~~~~~

Method name is determined from `prefix` attribute of root element and attribute of each element.

    1. If element has a `id` attribute, the method name is `prefix` + `id`. And `id` attribute will be removed from
       element.
    2. If element has a `class` attribute and it is only single class, the name is `prefix` + `class`.

See source of :meth:`~htmlwriter.PreProcessor.get_name`.


Not nested element
~~~~~~~~~~~~~~~~~~

The method created from not nested element is a shortcut of :meth:`~htmlwriter.XmlWriter._tag`. Tag name is first
positional argument, content and attributes are default arguments.

See source of :meth:`~htmlwriter.PreProcessor.make_from_shallow` and :meth:`~htmlwriter.PreProcessor.make_from_deep`.


Element `template-content`
~~~~~~~~~~~~~~~~~~~~~~~~~~

This element will be replaced with first positional argument.

See source of :meth:`~htmlwriter.PreProcessor.make_from_deep`.


Element `template-yield`
~~~~~~~~~~~~~~~~~~~~~~~~

The method will pause this element in `with statement`.

See source of :meth:`~htmlwriter.PreProcessor.make_from_deep`.


Attribute `template-attributes`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Filter and copy attributes argument in this element. Default attributes will be overwritten or merged.

Rule:
    * Patterns are separated with " " or ",".
    * Pattern is glob style pattern. See :meth:`~fnmatch.translate`.
    * Pattern that starts with "-" is a exclude pattern.

See source of :meth:`~htmlwriter.PreProcessor.handle_attributes`.


Attribute `template-attribute-map-class`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate `class` attribute from attributes.

Rule:
    * Patterns are separated with ",".
    * Source attribute name and target class name are separated with "as".
    * If no "as", target class name is same as source attribute name.
    * Source attribute value will be evaluated as `bool`.

See source of :meth:`~htmlwriter.PreProcessor.handle_attribute_map_class`.


Examples
~~~~~~~~

:attr:`~_template` attribute in :class:`~htmlwriter.HTMLWriter`

:attr:`~_template` attribute in :class:`~htmlwriter.HTML5Writer`

:attr:`~_template` attribute in :class:`~htmlwriter.Bootstrap3Writer`


TagMethodHelper
---------------

Another way, wrap method by :class:`~htmlwriter.TagMethodHelper`.

.. code-block:: python

    import contextlib
    from htmlwriter import XMLWriter, TagMethodHelper

    class CustomWriter(XMLWriter):

        # default attributes
        @TagMethodHelper
        def shallow(self, *args, attr1='val1', attr2='val2', **attributes):
            return self.tag('tag_name', *args, attr1=attr1, attr2=attr2, **attributes)

        @TagMethodHelper
        @contextlib.contextmanager
        def nested(self, *args, **attributes):
            with self.tag('parent'), self.tag('self', *args, **attributes):
                yield


.. note:: You must use `*args` for accept any attribute name. If you use positional argument for example `text`, you
          can't use attribute named `text`.

Examples
~~~~~~~~

:meth:`~htmlwriter.Bootstrap3Writer.bs_glyphicon`


Renaming and merging attribute
------------------------------

For customize renaming attribute, use :attr:`~htmlwriter.XMLWriter._attribute_rename_patterns` in subclass.

For customize merging attribute, use :attr:`~htmlwriter.XMLWriter._merge_attribute_handlers` in subclass.

See source of :meth:`~htmlwriter.XMLWriter._merge_attributes` for implementation.


Internal
--------

.. autoclass:: htmlwriter.XMLWriter
   :members:
   :undoc-members:
   :private-members:
   :exclude-members: tag, text, comment, cdata, write, getvalue, declaration, doctype, root_tag, root_attributes

   See :class:`~htmlwriter.XMLWriter` for public interface.

.. autoclass:: htmlwriter.TagMethodHelper

.. autoclass:: htmlwriter.PreProcessor
   :members:
   :undoc-members:
   :private-members:
