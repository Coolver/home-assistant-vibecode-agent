import unittest
from importlib.util import find_spec

HAS_FASTAPI = find_spec("fastapi") is not None

if HAS_FASTAPI:
    from fastapi import HTTPException
    from app.api.entities import _parse_dict_like
    from app.api.registries import _parse_aliases
    from app.models.schemas import HelperCreate, AutomationData

@unittest.skipUnless(HAS_FASTAPI, "fastapi is not installed in current Python environment")
class StructuredArgsParsingTests(unittest.TestCase):
    def test_parse_dict_like_from_json_string(self):
        parsed = _parse_dict_like('{"entity_id":"automation.some_automation"}')
        self.assertEqual(parsed, {"entity_id": "automation.some_automation"})

    def test_parse_dict_like_invalid_string_returns_none(self):
        self.assertIsNone(_parse_dict_like("not-a-json-object"))

    def test_parse_aliases_from_json_string(self):
        parsed = _parse_aliases('["AC","downstairs AC"]')
        self.assertEqual(parsed, ["AC", "downstairs AC"])

    def test_parse_aliases_invalid_raises_422(self):
        with self.assertRaises(HTTPException) as ctx:
            _parse_aliases('{"bad":"shape"}')
        self.assertEqual(ctx.exception.status_code, 422)

    def test_helper_create_accepts_json_string_config(self):
        helper = HelperCreate(type="input_boolean", config='{"name":"Test","icon":"mdi:test"}')
        self.assertEqual(helper.config["name"], "Test")

    def test_automation_data_accepts_json_string_triggers(self):
        automation = AutomationData(
            alias="Test automation",
            triggers='[{"platform":"state","entity_id":"sensor.a"}]',
            actions='[{"service":"light.turn_on","target":{"entity_id":"light.a"}}]',
        )
        self.assertEqual(automation.trigger[0]["entity_id"], "sensor.a")
        self.assertEqual(automation.action[0]["service"], "light.turn_on")

    def test_automation_data_keeps_keys_outside_the_model(self):
        automation = AutomationData(
            alias="Test automation",
            triggers=[{"trigger": "event", "event_type": "x"}],
            actions=[{"action": "light.turn_on"}],
            mode="parallel",
            max=25,
            max_exceeded="silent",
            variables={"a": 1},
            trace={"stored_traces": 10},
            initial_state=False,
        )
        dumped = automation.model_dump(exclude_none=True)
        self.assertEqual(dumped["max"], 25)
        self.assertEqual(dumped["max_exceeded"], "silent")
        self.assertEqual(dumped["variables"], {"a": 1})
        self.assertEqual(dumped["trace"], {"stored_traces": 10})
        self.assertIs(dumped["initial_state"], False)
        self.assertNotIn("triggers", dumped)
        self.assertNotIn("actions", dumped)


if __name__ == "__main__":
    unittest.main()
