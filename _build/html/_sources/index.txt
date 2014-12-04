Introduction
============

Let's write HTML with Python codes:

.. code-block:: pycon

    >>> from htmlwriter import HTML5Writer

    >>> h = HTML5Writer(lang='en')

    >>> with h.body, h.main(class_='main'):
    ...     h.p('hello, world')

    >>> h.getvalue()
    '<html lang="en"><body><main class="main"><p>hello, world</p></main></body></html>'

.. note::
    * `class` attribute must be 'class_' in Python code. Also `data-*` must be 'data_*' and `aria-*` must be 'aria_*' too.
    * Function calling brackets `()` is not required at `with statement` if no arguments.


Complex HTML (Bootstrap)
------------------------

Write complex Bootstrap with :class:`~htmlwriter.Bootstrap3Writer`.

.. code-block:: pycon

    >>> from htmlwriter import Bootstrap3Writer

    >>> h = Bootstrap3Writer(lang='en')

    >>> with h.body, h.bs_modal_dialog(id="myModal", class_="fade", aria_labelledby="myModalLabel"):
    ...     with h.bs_modal_header:
    ...         h.bs_modal_close_icon('Close')
    ...         h.h4('Modal title', class_="modal-title", id="myModalLabel")
    ...
    ...     with h.bs_modal_body:
    ...         h.text('...')
    ...
    ...     with h.bs_modal_footer:
    ...         h.bs_modal_close_button('Close')
    ...         h.bs_btn_primary('Save changes')

    >>> h.getvalue()
    '''<!DOCTYPE html>
    <html lang="en">
        <body>
            <div role="dialog" aria-hidden="true" class="fade modal" aria-labelledby="myModalLabel" id="myModal"
                 tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <button data-dismiss="modal" class="close" type="button">
                                <span aria-hidden="true">&times;</span>
                                <span class="sr-only">Close</span>
                            </button>
                            <h4 class="modal-title" id="myModalLabel">Modal title</h4>
                        </div>
                        <div class="modal-body">...</div>
                        <div class="modal-footer">
                            <button data-dismiss="modal" class="btn btn-default" type="button">Close</button>
                            <button class="btn btn-primary" type="button">Save changes</button>
                        </div>
                    </div>
                </div>
            </div>
        </body>
    </html>
    '''

.. note:: The result is not prettified actually. This is prettified for example output.


Get partial result
------------------

.. code-block:: pycon

    >>> from htmlwriter import HTML5Writer

    >>> h = HTML5Writer()

    >>> with h.main:
    ...     h.p('hello, world')

    >>> h.getvalue(root_tag=False)
    '<main><p>hello, world</p></main>'

See :meth:`~htmlwriter.XMLWriter.getvalue` for more information.


Contents
========

.. toctree::
   :maxdepth: 2
   :glob:

   htmlwriter
   extend


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
