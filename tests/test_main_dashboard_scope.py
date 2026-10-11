"""Exercise the preference endpoint with isolated account fixtures, no real DB."""
import ast
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock

from ticket_insights_service import default_layout


class MainDashboardScopeTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(Path('ticket_insights.py').read_text())
        function = next(node for node in tree.body
                        if isinstance(node, ast.FunctionDef) and node.name == 'save_main_ticket_scope')
        function.decorator_list = []
        self.records = {}
        self.user = NS(id=1)
        self.payload = {'scope': 'me'}
        self.session = NS(
            get=lambda model, user_id: self.records.get(user_id),
            add=lambda record: self.records.__setitem__(record.user_id, record),
            commit=Mock())
        namespace = dict(
            request=NS(get_json=lambda **kwargs: self.payload),
            current_user=self.user, db=NS(session=self.session),
            TicketDashboardLayout=lambda **kwargs: NS(**kwargs),
            default_layout=default_layout, datetime=datetime, timezone=timezone,
            jsonify=lambda **kwargs: kwargs)
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<scope-test>', 'exec'), namespace)
        self.save = namespace['save_main_ticket_scope']

    def test_choice_is_saved_per_account_and_can_be_changed(self):
        self.assertEqual(self.save(), {'scope': 'me'})
        self.user.id = 2
        self.payload = {'scope': 'all'}
        self.save()
        self.assertEqual(self.records[1].layout['main_ticket_scope'], 'me')
        self.assertEqual(self.records[2].layout['main_ticket_scope'], 'all')
        self.user.id = 1
        self.save()
        self.assertEqual(self.records[1].layout['main_ticket_scope'], 'all')

    def test_preserves_existing_widgets_and_filters(self):
        layout = default_layout('my')
        layout['filters'] = {'priority': '2'}
        self.records[1] = NS(layout=layout)
        self.save()
        self.assertEqual(self.records[1].layout['widgets'], layout['widgets'])
        self.assertEqual(self.records[1].layout['filters'], {'priority': '2'})
        self.assertEqual(self.records[1].layout['preset'], 'my')

    def test_invalid_choices_are_not_saved(self):
        for value in (None, [], {}, {'scope': 'other'}):
            self.payload = value
            self.assertEqual(self.save()[1], 400)
        self.session.commit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
