# -*- coding: utf-8 -*-

from testutils import Project
from unittest import TestCase
import unittest

class BuildTest(TestCase):

    def test_helloworld(self):
        Project("helloworld", "helloworlds").quick_test("Hello world 12\n")

    def test_helloworld2(self):
        Project("helloworld2", "helloworlds").quick_test("Hello world 5\n")

    def test_strings(self):
        Project("strings").quick_test("String\nOk\nOk\nOk\nOk\n", processes=5)

    def test_externtypes(self):
        output = "10 20\n107 207\n10 20\n257 77750 A looong string!!!!!\n10 30\n3 20003 String!!!\n"
        Project("externtypes").quick_test(output, processes=2)

    def test_packing(self):
        output = "0\n1\n2\n3\n4\n0\n1\n2\n3\n4\n5\n5\n6\n7\n8\n9\n100\n100\n"
        Project("packing").quick_test(output, processes=3)

    def test_broken1(self):
        Project("broken1", "broken").fail_ptp("*104/inscription: Expression missing\n")

    def test_broken2(self):
        Project("broken2", "broken").fail_ptp("*102/type: Type missing\n")

    def test_broken_module(self):
        Project("broken_module", "broken").fail_ptp(
            "*103: Conflict of types with the assigned module in variable 'x', type in module is String\n")

    def test_parameters(self):
        Project("parameters").quick_test("9 7\n", processes = 10, params = { "first" : 10, "second" : 7 })

    def test_eguards(self):
        Project("eguards").quick_test("3\n")

    def test_bidirection(self):
        Project("bidirection").quick_test("11\n12\n13\n")

    def test_scheduler(self):
        def check(output):
            d = { "First" : 0, "Second" : 0 }
            for line in output.split("\n"):
                if line:
                    d[line] += 1
            self.assertTrue(d["First"] > 220)
            self.assertTrue(d["Second"] > 220)
        Project("scheduler").quick_test(result_fn=check, processes=10)

    def test_workers(self):
        def check_output(output):
            self.assertEquals(76127, sum([ int(x) for x in output.split("\n") if x.strip() != "" ]))
        params = { "LIMIT" : "1000", "SIZE" : "20" }
        p = Project("workers")
        p.build()
        p.run(result_fn = check_output, processes = 2, params = params)

        p.run(result_fn = check_output, processes = 6, threads = 3, params = params, repeat = 30)
        p.run(result_fn = check_output, processes = 6, threads = 1, params = params, repeat = 70)

        Project("workers_fixed", "workers").quick_test(threads=5, processes=1, result_fn = check_output, params = params, repeat=110)

    def test_functions(self):
        Project("functions").quick_test("9 9\n")

    def test_tuples(self):
        Project("tuples").quick_test("Ok\n")

    def test_doubles(self):
        Project("doubles").quick_test("Ok\n")

    """ TEMPORARILY DISABLED
    def test_log(self):
        self.build(os.path.join(TEST_PROJECTS, "log", "log.proj"), "", make_args = [ "debug" ], program_name="log_debug")
        directory = os.path.join(TEST_PROJECTS, "log")
        RunProgram(os.path.join(KAIRA_TOOLS, "logmerge.py"), [ "log1" ], cwd = directory).run()
        RunProgram(os.path.join(KAIRA_TOOLS, "logmerge.py"), [ "log2" ], cwd = directory).run()
        self.assertTrue(os.path.isfile(os.path.join(TEST_PROJECTS, "log", "log1.klog")))
        self.assertTrue(os.path.isfile(os.path.join(TEST_PROJECTS, "log", "log2.klog")))
    """

    def test_build(self):
        Project("build").quick_test("1: 10\n2: 20\n")

    def test_getmore(self):
        Project("getmore").quick_test("Ok 7 13\n")

    def test_broken_userfunction(self):
        Project("broken_userfunction", "broken").failed_make("*106/user_function:")

    def test_broken_externtype_function(self):
        Project("broken_externtype_function", "broken").failed_make("*MyType/getsize:")

    def test_multicast(self):
        Project("multicast").quick_test("1800\n", processes=4)

    def test_array(self):
        Project("array").quick_test("Ok\n")

    def test_bool(self):
        Project("bool").quick_test("Ok\n")

    def test_modules1(self):
        p = Project("modules1")
        p.build()
        p.run("148\n")
        p.run("148\n", threads=2, repeat=100)
        p.run("148\n", threads=5, processes=3, repeat=100)

    def test_modules2(self):
        Project("modules2").quick_test("0\n")

    def test_library_processes(self):
        result = "".join([ "{0}\n".format(x) for x in range(1, 101) ])
        p = Project("overtake")
        p.build_main()
        p.run_main(result)
        for x in range(2, 5):
            p.run_main(result, processes = x * x, threads = x * x)

    def test_libhelloworld(self):
        result = "40 10 Hello world\n80 10 Hello world\n"\
            "160 10 Hello world\n320 10 Hello world\n640 10 Hello world\n"
        Project("libhelloworld").quick_test_main(result)

if __name__ == '__main__':
    unittest.main()
