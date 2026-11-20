import unittest
from unittest.mock import patch

from gdo.core.GDT_Text import GDT_Text
from gdo.mira.module_mira import module_mira


class AgentSkillTagsTest(unittest.TestCase):
    def test_optional_free_text_configuration(self):
        with patch('gdo.core.GDT_String.t', side_effect=lambda key, *args: key), \
             patch('gdo.ui.WithIcon.t', side_effect=lambda key, *args: key), \
             patch('gdo.date.Time.Time.human_duration', return_value='22m'):
            field = next(field for field in module_mira().gdo_module_config()
                         if field.get_name() == 'agent_skill_tags')
        self.assertIsInstance(field, GDT_Text)
        self.assertFalse(field.is_not_null())
        field.val('Python, wind turbines\nتحليل')
        self.assertEqual('Python, wind turbines\nتحليل', field.get_val())
