import unittest

from gdo.mira.module_mira import module_mira


class MiraDependenciesTest(unittest.TestCase):
    def test_runtime_module_dependencies(self):
        self.assertTrue({'chat', 'audio', 'video', 'translate'} <= set(module_mira().gdo_dependencies()))
