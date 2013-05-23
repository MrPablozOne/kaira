#
#    Copyright (C) 2011, 2012 Stanislav Bohm
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

import os
import base.utils
import makefiles

import build
import writer
import program
import library
import octave
import rpc
import statespace
import simrun


class CppGenerator:

    def __init__(self, project):
        self.project = project

    def get_filename(self, directory, suffix):
        return os.path.join(directory, self.project.get_name() + suffix)

    def get_place_user_fn_header(self, place_id):
        place = self.project.get_place(place_id)
        type_name = place.type
        if type_name[-1] == ">":
            type_name += " "
        return "void place_fn(ca::Context &ctx, ca::TokenList<{1}> &place)\n" \
                  .format(place, type_name)

    def get_transition_user_fn_header(self, transition_id):
        transition = self.project.get_transition(transition_id)
        w = writer.CppWriter()
        w.line("struct Vars {{")
        for name, t in transition.get_decls().get_list():
            if name != "ctx":
                w.line("\t{0} &{1};", t, name)
        w.line("}};")
        w.emptyline()
        w.line("void transition_fn(ca::Context &ctx, Vars &var)")
        return w.get_string()


class CppProgramGenerator(CppGenerator):

    def build(self, directory):
        builder = build.Builder(self.project, self.get_filename(directory, ".cpp"))
        program.write_standalone_program(builder)
        builder.write_to_file()
        makefiles.write_program_makefile(self.project, directory)

    def build_statespace(self, directory):
        builder = build.Builder(self.project, self.get_filename(directory, ".cpp"))
        statespace.write_statespace_program(builder)
        builder.write_to_file()
        makefiles.write_statespace_makefile(self.project, directory)

    def build_simrun(self, directory):
        builder = build.Builder(self.project, self.get_filename(directory, ".cpp"))
        simrun.write_simrun_program(builder)
        builder.write_to_file()
        makefiles.write_simrun_makefile(self.project, directory)


class CppLibGenerator(CppGenerator):

    def build(self, directory):

        if self.project.get_target_mode() == "lib":
            self.build_library(directory)
            makefiles.write_library_makefile(self.project, directory)

        if self.project.get_target_mode() == "rpc-lib":
            self.build_server(directory)
            self.build_client_library(directory)
            makefiles.write_library_makefile(self.project, directory, rpc=True)

        if self.project.get_target_mode() == "octave":
            self.build_library(directory)
            self.build_oct_files(directory)
            makefiles.write_library_makefile(self.project, directory, octave=True)

        if self.project.get_target_mode() == "rpc-octave":
            self.build_server(directory)
            self.build_client_library(directory)
            self.build_oct_files(directory)
            makefiles.write_library_makefile(self.project, directory, rpc=True, octave=True)


    def build_client_library(self, directory):
        source_filename = self.get_filename(directory, ".cpp")
        header_filename = self.get_filename(directory, ".h")

        # Build .cpp
        builder = build.Builder(self.project, source_filename)
        rpc.write_client(builder, self.project.get_name() + ".h")
        builder.write_to_file()

        # Build .h
        builder = build.Builder(self.project, header_filename)
        library.write_library_header_file(builder)
        builder.write_to_file()


    def build_server(self, directory):
        server_directory = os.path.join(directory, "server")

        # Check for server directory
        if os.path.exists(server_directory):
            if not os.path.isdir(server_directory):
                raise base.utils.PtpException("'server' exists but it is not directory")
        else:
            os.makedirs(server_directory)

        source_filename = os.path.join(server_directory,
                                       self.project.get_name() + "_server.cpp")

        builder = build.Builder(self.project, source_filename)
        rpc.write_server(builder)
        builder.write_to_file()

        makefiles.write_server_makefile(self.project, server_directory)

    def build_library(self, directory):
        source_filename = self.get_filename(directory, ".cpp")
        header_filename = self.get_filename(directory, ".h")

        # Build .cpp
        builder = build.Builder(self.project, source_filename)
        library.write_library(builder, self.project.get_name() + ".h")
        builder.write_to_file()

        # Build .h
        builder = build.Builder(self.project, header_filename)
        library.write_library_header_file(builder)
        builder.write_to_file()

    def build_oct_files(self, directory):
        source_filename = os.path.join(directory, self.project.get_name() + "_oct.cpp")
        m_filename = os.path.join(directory, self.project.get_name() + ".m")

        builder = build.Builder(self.project, source_filename)
        octave.write_oct_file(builder, self.project.get_name() + ".h")
        builder.write_to_file()

        builder = octave.OctaveBuilder(self.project)
        octave.write_loader(builder, self.project.get_name() + ".oct")
        builder.write_to_file(m_filename)
