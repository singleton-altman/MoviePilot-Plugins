"""隔离宿主和网络，验证通知筛选与配置契约。"""
import importlib.util
import json
from enum import Enum
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
MessageType = Enum('MessageType', dict(Download='资源下载', Organize='整理入库',
    Subscribe='订阅', SiteMessage='站点', MediaServer='媒体服务器',
    Manual='手动处理', Plugin='插件', Agent='智能体', Other='其它'))


def load_plugin(legacy=False):
    modules = {name: ModuleType(name) for name in (
        'app', 'app.sdk', 'app.sdk.config', 'app.sdk.events', 'app.sdk.logging',
        'app.sdk.network', 'app.plugins', 'app.schemas', 'app.schemas.types')}
    modules['app.sdk.config'].settings = SimpleNamespace(API_TOKEN='test-only')
    modules['app.sdk.events'].Event = SimpleNamespace
    modules['app.sdk.events'].eventmanager = SimpleNamespace(register=lambda _: lambda fn: fn)
    modules['app.sdk.logging'].logger = Mock()
    modules['app.sdk.network'].RequestUtils = Mock(side_effect=AssertionError('Real network forbidden'))
    modules['app.plugins']._PluginBase = object
    types = modules['app.schemas.types']
    types.EventType = SimpleNamespace(NoticeMessage='notice.message')
    setattr(types, 'NotificationType' if legacy else 'MessageType', MessageType)
    spec = importlib.util.spec_from_file_location('apppushmsg_test', ROOT / 'plugins.v3/apppushmsg/__init__.py')
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modules):
        spec.loader.exec_module(module)
    return module.AppPushMsg


class PushTests(unittest.TestCase):
    def setUp(self):
        self.cls = load_plugin()
        self.plugin = self.cls()
        self.plugin.get_data = Mock(return_value=None)
        self.plugin.save_data = Mock()
        self.plugin._send_message = Mock(return_value=(True, 'ok'))
        self.plugin.init_plugin({'enabled': True, 'token': 'test'})

    def send(self, **body):
        self.plugin.send(SimpleNamespace(event_data={'title': 'hello', **body}))

    def test_default_all_including_unknown_and_missing(self):
        for value in [*MessageType, 'future-type', None]:
            self.send(type=value)
        self.assertEqual(self.plugin._send_message.call_count, len(MessageType) + 2)

    def test_partial_selection_representations_and_fallback(self):
        self.plugin.init_plugin({'enabled': True, 'token': 'test', 'message_types': ['资源下载']})
        for value in [MessageType.Download, 'Download', '资源下载', 'NotificationType.Download', 'MessageType.Download']:
            self.send(type=value)
        self.send(mtype=MessageType.Download)
        self.assertEqual(self.plugin._send_message.call_count, 6)
        for body in [{}, {'type': 'future'}, {'type': MessageType.Plugin},
                     {'type': MessageType.Plugin, 'mtype': MessageType.Download}]:
            self.send(**body)
        self.assertEqual(self.plugin._send_message.call_count, 6)

    def test_empty_selection_and_manual_test(self):
        self.plugin.init_plugin({'enabled': True, 'token': 'test', 'message_types': []})
        self.send(type=MessageType.Download)
        self.plugin._send_message.assert_not_called()
        self.assertEqual(self.plugin.run_once()['code'], 0)
        self.plugin._send_message.assert_called_once()

    def test_channel_and_disabled(self):
        self.send(channel='dedicated')
        self.plugin.init_plugin(None)
        self.assertFalse(self.plugin.get_state())
        self.send()
        self.plugin._send_message.assert_not_called()

    def test_config_compatibility(self):
        for value in ['站点', 'SiteMessage', MessageType.SiteMessage, {'value': 'SiteMessage'}]:
            self.assertEqual(self.cls._normalize_message_types([value]), ['站点'])
        self.assertEqual(self.cls._normalize_message_types('Download,Plugin'), ['资源下载', '插件'])
        for value in [None, '']:
            self.assertEqual(self.cls._normalize_message_types(value), [x.value for x in MessageType])

    def test_form_and_manifest(self):
        form, defaults = self.plugin.get_form()
        self.assertEqual(defaults['message_types'], [x.value for x in MessageType])
        self.assertIn('智能体', json.dumps(form, ensure_ascii=False))
        manifest = json.loads((ROOT / 'package.v3.json').read_text())['AppPushMsg']
        self.assertEqual(manifest['version'], self.plugin.plugin_version)
        self.assertEqual(manifest['system_version'], '>=3.0.0')

    def test_early_v3_import(self):
        cls = load_plugin(legacy=True)
        self.assertEqual(cls._default_message_types(), [x.value for x in MessageType])


if __name__ == '__main__':
    unittest.main()
