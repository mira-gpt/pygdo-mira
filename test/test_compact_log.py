import json
import unittest

from gdo.mira.CompactLog import conversation_entry, format_entry


class CompactLogTest(unittest.TestCase):
    def test_plaintext_keeps_line_breaks(self):
        self.assertEqual('[now] Input:\none\ntwo\n\n',
                         format_entry({'timestamp': 'now', 'role': 'user', 'text': 'one\ntwo'}))

    def test_user_and_visible_assistant_messages(self):
        def event(role, kind, text, phase=None):
            return json.dumps({'type': 'response_item', 'timestamp': 'now', 'payload': {
                'type': 'message', 'role': role, 'phase': phase,
                'content': [{'type': kind, 'text': text}]}})
        self.assertEqual('one\ntwo', conversation_entry(event('user', 'input_text', 'one\ntwo'))['text'])
        self.assertEqual('Hello', conversation_entry(event('assistant', 'output_text', 'Hello', 'commentary'))['text'])
        self.assertEqual('Done', conversation_entry(event('assistant', 'output_text', 'Done', 'final_answer'))['text'])
        self.assertIsNone(conversation_entry(event('assistant', 'output_text', 'hidden', 'analysis')))
        self.assertIsNone(conversation_entry('{bad json'))

    def test_tool_and_image_data_are_not_logged(self):
        self.assertIsNone(conversation_entry(json.dumps({'type': 'response_item', 'payload': {
            'type': 'custom_tool_call_output', 'output': 'secret'}})))
        self.assertIsNone(conversation_entry(json.dumps({'type': 'response_item', 'payload': {
            'type': 'message', 'role': 'user', 'content': [{'type': 'input_image', 'image_url': 'data:...'}]}})))
