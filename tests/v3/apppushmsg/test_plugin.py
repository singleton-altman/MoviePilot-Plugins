"""隔离宿主和网络，验证通知筛选、配置契约与推送地址校验。"""
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
        'app.sdk.network', 'app.sdk.plugin', 'app.plugins', 'app.schemas',
        'app.schemas.types', 'app.schemas.response')}
    modules['app.sdk.config'].settings = SimpleNamespace(API_TOKEN='test-only')
    modules['app.sdk.events'].Event = SimpleNamespace
    modules['app.sdk.events'].eventmanager = SimpleNamespace(register=lambda _: lambda fn: fn)
    modules['app.sdk.logging'].logger = Mock()
    modules['app.sdk.network'].RequestUtils = Mock(side_effect=AssertionError('Real network forbidden'))
    modules['app.sdk.plugin']._PluginBase = object
    modules['app.plugins']._PluginBase = object
    types = modules['app.schemas.types']
    types.EventType = SimpleNamespace(NoticeMessage='notice.message')
    setattr(types, 'NotificationType' if legacy else 'MessageType', MessageType)

    class Response:
        """模拟宿主统一响应结构，只保留测试关心的字段。"""

        def __init__(self, success=False, message='', data=None):
            self.success = success
            self.message = message
            self.data = data

    modules['app.schemas'].Response = Response
    modules['app.schemas.response'].Response = Response

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
        # 每个用例只验证过滤语义，不受同内容去重影响。
        self.plugin._recent_deliveries = {}
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
        result = self.plugin.run_once()
        self.assertTrue(result.success)
        self.plugin._send_message.assert_called_once()

    def test_channel_and_disabled(self):
        self.send(channel='dedicated')
        self.plugin.init_plugin(None)
        self.assertFalse(self.plugin.get_state())
        self.send()
        self.plugin._send_message.assert_not_called()

    def test_duplicate_delivery_is_collapsed(self):
        # 宿主按 user,admin 路由时会在同一轮内投递两次相同通知。
        body = {'title': '同一通知', 'text': '正文', 'type': MessageType.Subscribe}
        self.plugin.send(SimpleNamespace(event_data=dict(body)))
        self.plugin.send(SimpleNamespace(event_data=dict(body)))
        self.assertEqual(self.plugin._send_message.call_count, 1)
        # 不同内容不应被误判为重复。
        self.plugin.send(SimpleNamespace(event_data={**body, 'text': '另一条'}))
        self.assertEqual(self.plugin._send_message.call_count, 2)

    def test_duplicate_window_expires(self):
        body = {'title': '窗口', 'text': '正文', 'type': MessageType.Subscribe}
        self.plugin.send(SimpleNamespace(event_data=dict(body)))
        key = ('窗口', '正文', str(MessageType.Subscribe))
        self.plugin._recent_deliveries[key] -= self.cls.DEDUP_WINDOW_SECONDS + 1
        self.plugin.send(SimpleNamespace(event_data=dict(body)))
        self.assertEqual(self.plugin._send_message.call_count, 2)

    def test_dedup_state_reset_on_init(self):
        body = {'title': '重置', 'text': '正文', 'type': MessageType.Subscribe}
        self.plugin.send(SimpleNamespace(event_data=dict(body)))
        self.plugin.init_plugin({'enabled': True, 'token': 'test'})
        self.plugin.send(SimpleNamespace(event_data=dict(body)))
        self.assertEqual(self.plugin._send_message.call_count, 2)

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

    def test_push_url_validation(self):
        for url in ('ftp://example.com/x', 'http://localhost/x', 'http://127.0.0.1/x',
                    'http://10.0.0.8/x', 'http://192.168.1.2/x', 'http://169.254.0.1/x',
                    'http://[::1]/x', 'http://0.0.0.0/x'):
            with self.assertRaises(ValueError, msg=url):
                self.cls._validate_push_url(url)
        for url in ('https://api.example.com/push', 'http://106.14.89.6/api/push'):
            self.assertEqual(self.cls._validate_push_url(url), url)

    def test_default_api_key_is_public_default(self):
        # 默认 Key 是公开值：服务端轮换 PUSH_API_KEY 即可批量失效沿用默认值的客户端。
        self.assertTrue(self.cls.DEFAULT_API_KEY.startswith('mp_push_'))
        self.assertEqual(self.plugin._api_key, self.cls.DEFAULT_API_KEY)
        self.plugin.init_plugin({'enabled': True, 'token': 't', 'apikey': 'custom-key'})
        self.assertEqual(self.plugin._api_key, 'custom-key')


if __name__ == '__main__':
    unittest.main()
