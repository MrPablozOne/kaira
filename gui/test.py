__author__ = 'pablo'

import xml.etree.ElementTree as xml

class Test:

    def __init__(self, project, id=None):
        if id is None:
            self.id = project.new_id()
        else:
            self.id = id
        self.project = project

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

    def get_net_name(self):
        return self.net_name

    def get_project_file(self):
        return self.project_file

    def get_project_dir(self):
        return self.project_dir

    def get_transition_id(self):
        return self.transition_id

    def as_xml(self):
        e = xml.Element("project_test")
        e.set("net_name", self.net_name)
        e.set("id", str(self.id))
        e.set("project_file", self.project_file)
        e.set("project_dir", self.project_dir)
        e.set("transition_id", str(self.transition_id))
        return e


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