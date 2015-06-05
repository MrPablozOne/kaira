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
TEST_LOGS_DIR_NAME = "Test logs"

import xml.etree.ElementTree as xml
import gtk
#import loader
import process
from objectlist import ObjectList
import os
import utils
from datetime import datetime
from events import EventSource



class Test(object):

    def __init__(self, project, id=None):
        if id is None:
            self.id = project.new_id()
        else:
            self.id = id
        #self.project = project
        self.name = "Test - {0}".format(str(self.id))
        self.test_status = None

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

    def build_and_run_test(self, app, project_test, target=TEST_BUILD_TARGET):
        def fail_callback():
            write_to_log(app, self.name, "Building error in test '{0}'. Test was not runed.\n".format(self.name),
                         "error")
            project_test.emit_event("test-complete", self, "error")

        project = self.load_project(app)
        if project is None:
            #error
            return False
        write_to_log(app,
                     self.name,
                     "Test start in time {0}\n".format(str(datetime.now())),
                     write_to_console=False,
                     write_flag='w')
        app.console_write("Building test '{0}' ...\n".format(self.name), "info")
        build_config = project.get_build_config(target)
        app.start_build( project,
                         build_config,
                         lambda: self.run_test(app, project_test, target),
                         fail_callback)

    def run_test(self, app, project_test, target=TEST_BUILD_TARGET):

        def on_exit(code):
            write_to_log(app,
                         self.name,
                         "Transition test '{0}' returned '{1}' in time {2}.\n".format(self.name, code, str(datetime.now())),
                              "success" if code == 0 else "error")
            project_test.emit_event("test-complete", self)

        def on_line(line, stream):
            if line.startswith("ASSERT"):
                write_to_log(app, self.name, line, "assert")
            else:
                app.console_write_output(line)
            return True
        app.console_write("Build finished ({0})\n".format(target), "success")
        write_to_log(app,
                     self.name,
                     "Test '{0}' begin.\n".format(self.name),
                     "success")
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


def write_to_log(app, test_name, text, tag_name="normal", write_to_console=True, write_flag='a'):
    directory = app.get_actual_project().get_directory()
    tests_directory = os.path.join(directory, TEST_LOGS_DIR_NAME)
    log_file = os.path.join(tests_directory, "{0}.log".format(test_name))
    utils.make_file_if_not_exist(log_file)
    f = open(log_file, write_flag)
    f.write(text)
    f.close()
    if write_to_console:
        app.console_write(text, tag_name)


class ProjectTests(gtk.VBox, EventSource):
    """
        Events: test-complete
    """
    def __init__(self, app):
        gtk.VBox.__init__(self)
        EventSource.__init__(self)
        self.app = app
        self.project = self.app.get_actual_project()
        self.launched_tests = {}
        self.launched_tests_count = 0

        self.set_callback("test-complete",
                          lambda w: self.test_complete(w))

        directory = self.project.get_directory()
        self.tests_log_directory = os.path.join(directory, TEST_LOGS_DIR_NAME)
        utils.makedir_if_not_exists(self.tests_log_directory)

        box = gtk.HBox()
        hbox = gtk.HButtonBox()
        hbox.set_layout(gtk.BUTTONBOX_START)

        self.label_filter_mode = gtk.Label("Filter mode: ")
        box.pack_start(self.label_filter_mode, False, False)
        self.filter = gtk.combo_box_new_text()
        self.filter.append_text("All")
        self.filter.append_text("Passed")
        self.filter.append_text("Failed")
        self.filter.append_text("Build error")
        self.filter.set_active(0) # Select 'All' as default
        self.filter.connect("changed", self.filter_changed)
        hbox.pack_start(self.filter, False, False)

        self.button_remove = gtk.Button(label="Remove test")
        self.button_remove.connect("clicked",
                       lambda w: self.remove_test(self.objlist.selected_object()))
        self.button_remove.set_sensitive(False)
        hbox.add(self.button_remove)
        self.button_run = gtk.Button(label="Run test")
        self.button_run.connect("clicked",
                       lambda w: self.execute(self.objlist.selected_object(), True))
        self.button_run.set_sensitive(False)
        hbox.add(self.button_run)
        self.button_run_all = gtk.Button(label = "Run all tests")
        self.button_run_all.connect("clicked",
                       lambda w: self.execute_all())
        hbox.add(self.button_run_all)
        self.button_run_wrong = gtk.Button(label = "Run failed tests")
        self.button_run_wrong.connect("clicked",
                       lambda w: self.execute_wrongs())
        hbox.add(self.button_run_wrong)
        box.pack_start(hbox, False, False)
        self.pack_start(box, False, False)

        hbox = gtk.HBox()
        self.objlist = ObjectList([("_", object), ("Tests", str), ("Test status", str) ])
        self.objlist.set_size_request(170, 100)
        self.objlist.object_as_row = lambda obj: [ obj, obj.name, obj.test_status ]
        self.objlist.row_activated = self.row_activated
        self.objlist.cursor_changed = self.row_activated
        hbox.pack_start(self.objlist, False, False)

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
        for test in tests:
            test.test_status = None
        self.objlist.fill(tests)
        if tests:
            self.objlist.select_first()
        self.show_all()

    def execute(self, test, one_test=False):
        if one_test:
            tests = self.project.get_all_tests()
            for t in tests:
                t.test_status = None
            self.objlist.clear()
            self.objlist.fill(tests)
            self.launched_tests = {}
            self.launched_tests_count = 1
        test_return = test.build_and_run_test(self.app, self)
        if test_return is False:
            self.launched_tests[test] = "error"
            write_to_log(self.app, test.get_name(), "Test '{0}' was not launched.", "error")

    def execute_all(self):
        self.launched_tests = {}
        tests = self.project.get_all_tests()
        self.launched_tests_count = len(tests)
        for test in tests:
            self.execute(test)

    def execute_wrongs(self):
        tests = self.project.get_all_tests()
        for t in tests:
            t.test_status = None
        self.objlist.clear()
        self.objlist.fill(tests)
        items = self.launched_tests.items()
        self.launched_tests_count = 0
        self.launched_tests = {}
        for test, ret in items:
            if ret is False:
                self.launched_tests_count += 1
                self.execute(test)

    def test_complete(self, test, status=None):
        self.launched_tests[test] = status
        if len(self.launched_tests.keys()) is self.launched_tests_count:
            self.all_tests_complete()

    def all_tests_complete(self):

        def get_return_string(result):
            if result is "error":
                return "Build error"
            elif result:
                return "Passed"
            else:
                return "Failed"

        #Fill launched_tests from None to True or False from test log
        for test, ret in self.launched_tests.items():
            if ret is None:
                self.read_test_log(test)

        #write test results to console
        for test, ret in self.launched_tests.items():
            res = get_return_string(ret)
            self.app.console_write("Test '{0}' - '{1}'\n".format(test.get_name(), res),
                                   "success" if ret else "error")
            test.test_status = res
            self.objlist.update(test)

    def row_activated(self, obj):
        self.button_remove.set_sensitive(True)
        self.button_run.set_sensitive(True)
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

    def filter_changed(self, obj):
        self.objlist.clear()
        tests = self.project.get_all_tests()
        status = str(obj.get_active_text())
        if status == 'All':
            self.objlist.fill(tests)
            return
        for test in tests:
            if test.test_status == status:
                self.objlist.add_object(test)

    #set test return to launched_tests by test log
    def read_test_log(self, test):
        with open(os.path.join(self.tests_log_directory, "{0}.log".format(test.get_name()))) as f:
            lines = f.readlines()
        for line in lines:
            if "[Fail]" in line:
                self.launched_tests[test] = False
                return
        self.launched_tests[test] = True


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