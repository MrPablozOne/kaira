#
#    Copyright (C) 2013 Martin Surkovsky
#    Copyright (C) 2013 Stanislav Bohm
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

import csv

import extensions
import gtk
import gtkutils
import settingswindow
import runview
import utils
from tracelog import TraceLog

"""Supported types for extensions."""

types_repository = []


class Type(object):

    def __init__(self, name, short_name=None):
        """Initialize of type of types.

        Arguments:
        name -- name of type
        short_name -- short version of name
        files_extensions -- a list of supported file types

        """
        self.name = name
        if short_name is None:
            self.short_name = name
        else:
            self.short_name = short_name
        self.setting = None

        self.loaders = {}
        self.savers = {}
        self.default_saver = None

    def get_view(self, data, app):
        return None

    def register_load_function(self, extension, function):
        self.loaders[extension] = function

    def register_store_function(self, extension, function, default=False):
        self.savers[extension] = function
        if default or self.default_saver is None:
            self.default_saver = extension


# *****************************************************************************
# module functions
def get_type_by_suffix(suffix):
    for type in types_repository:
        if suffix in type.loaders:
            return type
    return None

def get_loader_by_suffix(suffix):
    for type in types_repository:
        loader = type.loaders.get(suffix)
        if loader is not None:
            return loader
    return None

def get_saver_by_suffix(suffix):
    for type in types_repository:
        saver = type.savers.get(suffix)
        if saver is not None:
            return saver
    return None

def get_load_file_filters():
    all_supported_types = gtk.FileFilter()
    all_supported_types.set_name("All supported files")

    result = [ all_supported_types ]
    for type in types_repository:
        patterns = [ "*." + s for s in type.loaders.keys() ]
        filter = gtk.FileFilter()
        filter.set_name("{0} ({1})".format(type.short_name, ", ".join(patterns)))
        result.append(filter)

        for pattern in patterns:
            filter.add_pattern(pattern)
            all_supported_types.add_pattern(pattern)
    return result

def get_save_file_filter(type):
    patterns = [ "*." + s for s in type.loaders.keys() ]
    filter = gtk.FileFilter()
    filter.set_name("{0} ({1})".format(type.short_name, ", ".join(patterns)))
    for pattern in patterns:
        filter.add_pattern(pattern)
    return filter

# *****************************************************************************
# supported types

# Standard data types
t_string = Type("Plain text")

# -----------------------------------------------------------------------------
# Tracelog type
t_tracelog = Type("Kaira tracelog", "Tracelog")
def load_kth(filename, app, setting=None):
    if filename is None:
        return
    return app._catch_io_error(lambda: TraceLog(filename))
t_tracelog.register_load_function("kth", load_kth)

def tracelog_view(data, app):
    return runview.RunView(app, data)
t_tracelog.get_view = tracelog_view

types_repository.append(t_tracelog)

# -----------------------------------------------------------------------------
# Table type
t_table = Type("Table")

def show_csv_setting_dialog(parent_window):
    sw = settingswindow.SettingWidget()

    sw.add_combobox("delimiter",
                    "Delimiter",
                    [("Tab", "\t"), ("Comma", ","),
                    ("Semicolon", ";"), ("Space", " ")],
                    default=1)

    sw.add_combobox("quotechar",
                    "Quote char",
                    [("Single quotes", "\'"), ("Double quotes", "\"")],
                    default=1)

    sw.add_radiobuttons("header",
                        "Header",
                        [("With header", True), ("Without header", False)],
                        default=1,
                        ncols=2)

    dialog = settingswindow.BasicSettingDialog(sw, "Setting", parent_window)
    dialog.set_size_request(400, 250)
    dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
    dialog.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK, True)

    response = dialog.run()
    if response == gtk.RESPONSE_OK:
        dialog.destroy()
        delimiter = sw.get("delimiter")
        quotechar = sw.get("quotechar")
        has_header = sw.get("header")
        return (delimiter, quotechar, has_header)

    dialog.destroy()
    return None

def load_csv(filename, app, setting):
    if setting is None:
        setting = show_csv_setting_dialog(app.window)
        t_table.setting = setting
    if setting is None:
        return # setting was canceled

    delimiter, quotechar, has_header = setting
    with open(filename, "rb") as csvfile:
        csvreader = csv.reader(
            csvfile, delimiter=delimiter, quotechar=quotechar)

        data = []
        try:
            if has_header:
                header = csvreader.next()
            else:
                row = csvreader.next()
                data.append(row)
                count = len(row)
                header = ["V{0}".format(i) for i in xrange(count)]
        except StopIteration:
            return (["V0"], [])

        for row in csvreader:
            data.append(row)
        return (header, data)

t_table.register_load_function("csv", load_csv)

def store_csv(data, filename, app, settings):
    header, rows = data
    if settings is None:
        settings = show_csv_setting_dialog(app.window)
    delimiter, quotechar, has_header = settings
    with open(filename, "w") as csvfile:
        csvwriter = csv.writer(
            csvfile, delimiter=delimiter, quotechar=quotechar)
        if has_header:
            csvwriter.writerow(header)
        for row in rows:
            csvwriter.writerow(row)

t_table.register_store_function("csv", store_csv)

def csv_view(data, app):
    header, rows = data
    colnames = [(title, str) for title in header]

    view = gtkutils.SimpleList(colnames)
    idx = 1
    for row in rows:
        try:
            view.append(row)
            idx += 1
        except ValueError:
            required_len = len(header) if header is not None else len(rows[0])
            msg = ("Row sequence has wrong length. It must have {0} items"
                    " instead of {1}.\nThe problem row is index is {2}.".
                        format(required_len, len(row), idx))
            app.show_message_dialog(msg, gtk.MESSAGE_WARNING)
    return view
t_table.get_view = csv_view

types_repository.append(t_table)