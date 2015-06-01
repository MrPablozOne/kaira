#
#    Copyright (C) 2014-2015 Pavel Siemko
#
#    This file is part of Kaira.
#
#    Kaira is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License, or
#    (at your option) any later version.
#
#    Kaira is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Kaira.  If not, see <http://www.gnu.org/licenses/>.
#

__author__ = 'Pavel Siemko'
TEST_BUILD_TARGET = "release"

import xml.etree.ElementTree as xml
import gtk
#import loader
import process
from objectlist import ObjectList
import os


class Test(object):

    def __init__(self, project, id=None):
        if id is None:
            self.id = project.new_id()
        else:
            self.id = id
        #self.project = project
        self.name = "Test - {0}".format(str(self.id))

    def set_net_name(self, net_name):
        self.net_name = net_name

    def set_project_file(self, project_file):
        self.project_file = project_file

    def set_project_dir(self, project_dir):
        self.project_dir = project_dir

    def set_transition_id(self, transition_id):
        self.transition_id = transition_id

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_net_name(self):
        return self.net_name

    def get_project_file(self):
        return self.project_file

    def get_project_filename(self):
        d, fname = os.path.split(self.project_file)
        name, ext = os.path.splitext(fname)
        return name

    def get_project_dir(self):
        return self.project_dir

    def get_transition_id(self):
        return self.transition_id

    def get_executable_filename(self):
        d, fname = os.path.split(self.project_file)
        name, ext = os.path.splitext(fname)
        return os.path.join(self.project_dir, TEST_BUILD_TARGET, name)

    def load_project(self, app):
        import loader
        p = app._catch_io_error(lambda: loader.load_project(self.get_project_file()))
        if p:
            return p
        else:
            return None

    def build_test(self, app, target=TEST_BUILD_TARGET):
        project = self.load_project(app)
        if project is None:
            #error
            return False
        app.console_write("Building test '{0}' ...\n".format(self.name), "info")
        build_config = project.get_build_config(target)
        app.start_build( project,
                         build_config,
                         lambda: self.run_test(app, target),
                         lambda: app.console_write("Error in test building", "error"))

    def run_test(self, app, target=TEST_BUILD_TARGET):
        def on_exit(code):
            app.console_write("Transition test '{0}' returned '{1}'.\n".format(self.name, code),
                              "success" if code == 0 else "error")
        def on_line(line, stream):
            if line.startswith("ASSERT"):
                app.console_write(line, "assert");
            else:
                app.console_write_output(line)
            return True
        app.console_write("Build finished ({0})\n".format(target), "success")
        app.console_write("Test '{0}' started.\n".format(self.name), "success")
        p = process.Process(self.get_executable_filename(), on_line, on_exit)
        p.cwd = self.project_dir
        p.start()


    def as_xml(self):
        e = xml.Element("project_test")
        e.set("net_name", self.net_name)
        e.set("id", str(self.id))
        e.set("project_file", self.project_file)
        e.set("project_dir", self.project_dir)
        e.set("transition_id", str(self.transition_id))
        return e

class ProjectTests(gtk.VBox):
    def __init__(self, app):
        gtk.VBox.__init__(self)
        self.app = app
        self.project = self.app.get_actual_project()

        box = gtk.HBox()
        hbox = gtk.HButtonBox()
        hbox.set_layout(gtk.BUTTONBOX_START)
        button = gtk.Button(label= "Odstranit" ,stock = gtk.STOCK_REMOVE)
        button.connect("clicked",
                       lambda w: self.remove_test(self.objlist.selected_object()))
        hbox.add(button)
        button = gtk.Button(label = "Spustit", stock = gtk.STOCK_EXECUTE)
        button.connect("clicked",
                       lambda w: self.execute(self.objlist.selected_object()))
        hbox.add(button)
        button = gtk.Button(label = "Spustit vse")
        button.connect("clicked",
                       lambda w: self.execute_all())
        hbox.add(button)
        button = gtk.Button(label = "Spustit neuspesne")
        button.connect("clicked",
                       lambda w: self.execute_wrongs())
        hbox.add(button)
        box.pack_start(hbox, False, False)

        self.pack_start(box, False, False)

        hbox = gtk.HBox()

        self.objlist = ObjectList([("_", object), ("Tests", str) ])
        self.objlist.set_size_request(100, 100)
        self.objlist.object_as_row = lambda obj: [ obj, obj.name ]
        self.objlist.row_activated = self.row_activated

        hbox.pack_start(self.objlist, False, False)
        #self.editor = CodeFileEditor(self.app.project.get_syntax_highlight_key())
        #hbox.pack_start(self.editor)

        vbox = gtk.VBox(spacing=10)
        hbox_name = gtk.HBox()
        label = gtk.Label("Test id: ")
        hbox_name.pack_start(label, False, False)
        self.label_test_id = gtk.Label("")
        hbox_name.pack_start(self.label_test_id, False, False)
        vbox.pack_start(hbox_name, False, False)
        hbox_name = gtk.HBox()
        label = gtk.Label("Test name: ")
        hbox_name.pack_start(label, False, False)
        self.label_test_name = gtk.Label("")
        hbox_name.pack_start(self.label_test_name, False, False)
        vbox.pack_start(hbox_name, False, False)
        hbox_name = gtk.HBox()
        label = gtk.Label("Test project filename: ")
        hbox_name.pack_start(label, False, False)
        self.label_project_filename = gtk.Label("")
        hbox_name.pack_start(self.label_project_filename, False, False)
        vbox.pack_start(hbox_name, False, False)
        hbox_name = gtk.HBox()
        label = gtk.Label("Test project dir: ")
        hbox_name.pack_start(label, False, False)
        self.label_project_dir = gtk.Label("")
        hbox_name.pack_start(self.label_project_dir, False, False)
        vbox.pack_start(hbox_name, False, False)
        hbox_name = gtk.HBox()
        label = gtk.Label("Test net name: ")
        hbox_name.pack_start(label, False, False)
        self.label_net_name = gtk.Label("")
        hbox_name.pack_start(self.label_net_name, False, False)
        vbox.pack_start(hbox_name, False, False)

        hbox.pack_start(vbox)


        self.pack_start(hbox)

        tests = self.project.get_all_tests()
        self.objlist.fill(tests)
        if tests:
            self.objlist.select_first()
        self.show_all()

    def execute(self, test):
        test.build_test(self.app)
        #test.run_test(self.app)


    def execute_all(self):
        tests = self.project.get_all_tests()
        for test in tests:
            test.run_test(self.app)


    def execute_wrongs(self):
        None

    def row_activated(self, obj):
        self.label_test_id.set_text(str(obj.get_id()))
        self.label_test_name.set_text(obj.get_name())
        self.label_project_filename.set_text(obj.get_project_filename())
        self.label_project_dir.set_text(obj.get_project_dir())
        self.label_net_name.set_text(obj.get_net_name())

    def save(self):
        project = self.app.get_actual_project()
        if project is not None:
            project.save()

    def remove_test(self, test):
        if test is not None:
            self.project.delete_test(test)
            tests = self.project.get_all_tests()
            self.objlist.clear()
            self.objlist.fill(tests)
            self.objlist.select_first()

    def refresh_tests(self):
        tests = self.project.get_all_tests()
        self.objlist.refresh(tests)
        self.cursor_changed(self.objlist.selected_object())


def load_test(element, project, loader):
    net_name = element.get("net_name", "X")
    id = loader.get_id(element)
    project_file = element.get("project_file")
    project_dir = element.get("project_dir")
    transition_id = element.get("transition_id")

    test = Test(project, id)
    test.set_net_name(net_name)
    test.set_project_dir(project_dir)
    test.set_project_file(project_file)
    test.set_transition_id(transition_id)

    return test