#!/usr/bin/env python

# Copyright 2015 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# A small script used to convert an .entries file into a DLL wrapper

import re
import sys

re_func = re.compile(r"""^(.*[\* ])([A-Za-z_][A-Za-z0-9_]*)\((.*)\);$""")
re_param = re.compile(r"""^(.*[\* ])([A-Za-z_][A-Za-z0-9_]*)$""")

ENTRY_PREFIX = "__dll_"

class Entry:
    def __init__(self, func_name, return_type, parameters):
        self.func_name = func_name
        self.ptr_name = "%s%s" % (ENTRY_PREFIX, func_name)
        self.return_type = return_type
        self.parameters = ""
        self.call = ""
        comma = ""
        for param in parameters:
            self.parameters += "%s%s %s" % (comma, param[0], param[1])
            self.call += "%s%s" % (comma, param[1])
            comma = ", "

def parse_file(filename, lines):
    entries = []
    failure = False
    lineno = 0
    prefix_name = "unknown"
    print "// Auto-generated from: %s" % filename
    print "// With %s" % sys.argv[0]
    print "// DO NOT EDIT THIS FILE"
    print ""
    print "#include <dlfcn.h>"
    for line in lines:
        lineno += 1
        line = line.strip()
        if len(line) == 0:  # Ignore empty lines
            continue
        if line[0] == '#':  # Ignore comments
            continue
        if line[0] == '!':  # Prefix name
            prefix_name = line[1:]
            continue
        if line[0] == '%':  # Verbatim line copy
            print line[1:]
            continue
        # Must be a function signature.
        m = re_func.match(line)
        if not m:
            print "ERROR:%s:%d '%s'" % (filename, lineno, line)
            failure = True
            break

        return_type, func_name, parameters = m.groups()
        return_type = return_type.strip()
        parameters = parameters.strip()
        params = []
        failure = False
        if parameters != "void":
            for parameter in parameters.split(','):
                parameter = parameter.strip()
                m = re_param.match(parameter)
                if not m:
                    print "ERROR:%s:%d: parameter '%s'" % (filename, lineno, parameter)
                    failure = True
                else:
                    param_type, param_name = m.groups()
                    params.append((param_type.strip(), param_name.strip()))
        if failure:
            break

        entries.append(Entry(func_name, return_type, params))

    if failure:
        return None

    print ""
    print "///"
    print "///  W R A P P E R   P O I N T E R S"
    print "///"
    print ""
    for entry in entries:
        print "static %s (*%s)(%s) = 0;" % (entry.return_type, entry.ptr_name, entry.parameters)

    print ""
    print "///"
    print "///  W R A P P E R   F U N C T I O N S"
    print "///"
    print ""

    for entry in entries:
        print "%s %s(%s) {" % (entry.return_type, entry.func_name, entry.parameters)
        if entry.return_type != "void":
            print "  return %s(%s);" % (entry.ptr_name, entry.call)
        else:
            print "  %s(%s);" % (entry.ptr_name, entry.call)
        print "}\n"

    print ""
    print "///"
    print "///  I N I T I A L I Z A T I O N   F U N C T I O N"
    print "///"
    print ""

    print "int %s_dynlink_init(void* lib) {" % prefix_name
    for entry in entries:
        print "  %s = (%s(*)(%s))dlsym(lib, \"%s\");" % \
                (entry.ptr_name,
                 entry.return_type,
                 entry.parameters,
                 entry.func_name)
        print "  if (!%s) return -1;" % entry.ptr_name
    print "  return 0;"
    print "}"

if len(sys.argv) == 1:
    parse_file("<stdin>", sys.stdin)
else:
    parse_file(sys.argv[1], open(sys.argv[1]))

