#!/usr/local/bin/python3.4
# -*- coding: utf-8 -*-
from htmlwriter import XmlTestCase, HTML5Writer, Bootstrap3Writer


class Test(XmlTestCase):

    def test_simple(self):
        h = HTML5Writer()
        with h.body:
            h.text('hello, world')

        self.assertXmlEqual(h.getvalue(), '''
            <!DOCTYPE html>
            <html>
                <body>
                    hello, world
                </body>
            </html>
        ''')

    def test_escape(self):
        h = HTML5Writer()
        with h.body:
            h.text('hello, world><')

        self.assertXmlEqual(h.getvalue(), '''
            <!DOCTYPE html>
            <html>
                <body>
                    hello, world&gt;&lt;
                </body>
            </html>
        ''')

    def test_nested_with(self):
        h = HTML5Writer()
        with h.body, h.main:
            h.p('hello, world')

        self.assertXmlEqual(h.getvalue(), '''
            <!DOCTYPE html>
            <html>
                <body>
                    <main>
                        <p>hello, world</p>
                    </main>
                </body>
            </html>
        ''')

    def test_rewrite_attributes(self):
        h = HTML5Writer()
        with h.body:
            h.div('hello, world', class_='main')

        self.assertXmlEqual(h.getvalue(), '''
            <!DOCTYPE html>
            <html>
                <body>
                    <div class="main">
                        hello, world
                    </div>
                </body>
            </html>
        ''')

    def test_cdata(self):
        h = HTML5Writer()
        with h.head:
            h.title('hello, world')
            with h.script:
                h.cdata('// hello')

        self.assertXmlEqual(h.getvalue(), '''
            <!DOCTYPE html>
            <html>
                <head>
                    <title>hello, world</title>
                    <script><![CDATA[// hello]]></script>
                </head>
            </html>
        ''')

    def test_root_attributes(self):
        h = HTML5Writer(lang='en')

        self.assertXmlEqual(h.getvalue(), '''
            <!DOCTYPE html>
            <html lang="en"></html>
        ''')

    def test_bs_dropdown_simple(self):
        h = Bootstrap3Writer(lang='en')

        with h.body, h.bs_dropdown:
            with h.bs_dropdown_toggle(id="dropdownMenu1", aria_expanded="true"):
                h.text('Dropdown')
                h.bs_caret()

            with h.bs_dropdown_menu(aria_labelledby="dropdownMenu1"):
                h.bs_menuitem('Action')
                h.bs_menuitem('Another action')
                h.bs_menuitem('Something else here')
                h.bs_menuitem('Separated link')

        # print(h.getvalue())
        self.assertXmlEqual(h.getvalue(), '''
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <div class="dropdown">
                        <button type="button" data-toggle="dropdown" id="dropdownMenu1"
                                class="btn btn-default dropdown-toggle" aria-expanded="true">
                            Dropdown
                            <span class="caret"></span>
                        </button>
                        <ul role="menu" aria-labelledby="dropdownMenu1" class="dropdown-menu">
                            <li role="presentation"><a tabindex="-1" href="#" role="menuitem">Action</a></li>
                            <li role="presentation"><a tabindex="-1" href="#" role="menuitem">Another action</a></li>
                            <li role="presentation"><a tabindex="-1" href="#" role="menuitem">Something else here</a></li>
                            <li role="presentation"><a tabindex="-1" href="#" role="menuitem">Separated link</a></li>
                        </ul>
                    </div>
                </body>
            </html>
        ''')

    def test_bs_modal_simple(self):
        h = Bootstrap3Writer(lang='en')

        with h.body, h.bs_modal_dialog(id="myModal", class_="fade", aria_labelledby="myModalLabel"):
            with h.bs_modal_header:
                h.bs_modal_close_icon('Close')
                h.h4('Modal title', class_="modal-title", id="myModalLabel")

            with h.bs_modal_body:
                h.text('...')

            with h.bs_modal_footer:
                h.bs_modal_close_button('Close')
                h.bs_btn_primary('Save changes')

        # print(h.getvalue())
        self.assertXmlEqual(h.getvalue(), '''
            <!DOCTYPE html>
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
        ''')

    def test_bs_previous(self):
        h = Bootstrap3Writer(lang='en')

        with h.body:
            h.bs_previous('Previous', href='/previous_page', disabled=False)

        # print(h.getvalue())
        self.assertXmlEqual(h.getvalue(), '''
            <!DOCTYPE html>
            <html lang="en">
                <body>
                    <li class="previous">
                        <a href="/previous_page">
                            <span aria-hidden="true">&larr;</span>
                            Previous
                        </a>
                    </li>
                </body>
            </html>
        ''')
