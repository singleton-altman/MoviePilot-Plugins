from typing import Any, List, Dict, Tuple
from datetime import datetime

from app.core.event import eventmanager, Event
from app.log import logger
from app.plugins import _PluginBase
from app.schemas.types import EventType
from app.utils.http import RequestUtils


class AppPushMsg(_PluginBase):
    DEFAULT_API_KEY = "mp_push_3f8d1c7a9b4e2f6c0a5d8e1b7c9f2a4d6e3b1c8f5a7d9e2"

    # 插件名称
    plugin_name = "APPLitePush"
    # 插件描述
    plugin_desc = "支持使用 APPLitePush 接口发送消息通知。"
    # 插件图标
    plugin_icon = "Pushplus_A.png"
    # 插件版本
    plugin_version = "1.1.3"
    # 插件作者
    plugin_author = "altman"
    # 作者主页
    author_url = "https://github.com/singleton-altman"
    # 插件配置项ID前缀
    plugin_config_prefix = "apppushmsg_"
    # 加载顺序
    plugin_order = 30
    # 可使用的用户级别
    auth_level = 1

    _enabled = False
    _token = None

    _api_url = "http://106.14.89.6/api/push"
    _api_key = DEFAULT_API_KEY

    def init_plugin(self, config: dict = None):
        if config:
            self._enabled = config.get("enabled", False)
            self._token = config.get("token")
            self._api_key = config.get("apikey") or self.DEFAULT_API_KEY
        else:
            self._api_key = self.DEFAULT_API_KEY

    def get_state(self) -> bool:
        return bool(self._enabled and self._token)

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        return [{
            "path": "/run",
            "endpoint": self.run_once,
            "methods": ["GET"],
            "summary": "发送测试消息",
            "description": "发送一条本地测试通知"
        }]

    def run_once(self) -> Dict[str, Any]:
        success, message = self._send_message(
            title="测试消息",
            content="这是一条本地测试通知"
        )
        self._save_test_result(success=success, message=message)
        return {
            "code": 0 if success else 500,
            "msg": message
        }

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        last_test_text = self._format_test_result()
        return [
            {
                "component": "VForm",
                "content": [
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {
                                    "cols": 12,
                                    "md": 6
                                },
                                "content": [
                                    {
                                        "component": "VSwitch",
                                        "props": {
                                            "model": "enabled",
                                            "label": "启用插件"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {
                                    "cols": 12,
                                    "md": 8
                                },
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "token",
                                            "label": "App Push Token",
                                            "placeholder": "请输入推送 token"
                                        }
                                    }
                                ]
                            },
                            {
                                "component": "VCol",
                                "props": {
                                    "cols": 12,
                                    "md": 4,
                                    "class": "d-flex align-end"
                                },
                                "content": [
                                    {
                                        "component": "VBtn",
                                        "props": {
                                            "block": True,
                                            "color": "primary",
                                            "variant": "tonal",
                                            "loading": "{{ !!model.test_loading }}",
                                            "disabled": "{{ !!model.test_loading }}",
                                            "onClick": """async function () {
                                                const formatResult = (success, message) => {
                                                    const now = new Date();
                                                    const pad = (value) => String(value).padStart(2, '0');
                                                    const time = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
                                                    model.last_test_text = `最近一次测试结果：${success ? '成功' : '失败'} | 时间：${time} | 返回：${message || '无返回信息'}`;
                                                };

                                                model.test_loading = true;
                                                try {
                                                    const response = await fetch('/api/v1/plugin/AppPushMsg/run', {
                                                        method: 'GET',
                                                        credentials: 'include'
                                                    });
                                                    const data = await response.json().catch(() => ({}));
                                                    const success = response.ok && Number(data?.code ?? 500) === 0;
                                                    const message = data?.msg || (success ? '消息发送成功' : `HTTP ${response.status}`);
                                                    formatResult(success, message);
                                                } catch (error) {
                                                    formatResult(false, error?.message || '请求失败，请稍后重试');
                                                } finally {
                                                    model.test_loading = false;
                                                }
                                            }"""
                                        },
                                        "text": "发送测试消息"
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {
                                    "cols": 12,
                                    "md": 8
                                },
                                "content": [
                                    {
                                        "component": "VTextField",
                                        "props": {
                                            "model": "apikey",
                                            "label": "API Key",
                                            "placeholder": "不填写则使用默认值"
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "component": "VRow",
                        "content": [
                            {
                                "component": "VCol",
                                "props": {
                                    "cols": 12
                                },
                                "content": [
                                    {
                                        "component": "VAlert",
                                        "props": {
                                            "type": "info",
                                            "variant": "tonal",
                                            "text": "请先保存 token 和 apikey，再点击测试按钮。测试按钮会使用已保存的配置发送消息。"
                                        }
                                    },
                                    {
                                        "component": "VAlert",
                                        "props": {
                                            "type": "secondary",
                                            "variant": "tonal",
                                            "text": "{{ model.last_test_text || '最近一次测试结果：暂无记录' }}"
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ], {
            "enabled": False,
            "token": "",
            "apikey": self.DEFAULT_API_KEY,
            "last_test_text": last_test_text,
            "test_loading": False
        }

    def get_page(self) -> List[dict]:
        return []

    @eventmanager.register(EventType.NoticeMessage)
    def send(self, event: Event):
        if not self.get_state() or not event.event_data:
            return

        msg_body = event.event_data
        channel = msg_body.get("channel")
        if channel:
            return

        title, content = self._build_message(msg_body)
        if not title and not content:
            logger.warn("标题和内容不能同时为空")
            return

        success, message = self._send_message(title=title, content=content)
        if success:
            logger.info("App Push消息发送成功")
        else:
            logger.warn(f"App Push消息发送失败：{message}")
        self._save_test_result(success=success, message=message)

    @staticmethod
    def _build_message(msg_body: Dict[str, Any]) -> Tuple[str, str]:
        title = str(msg_body.get("title") or msg_body.get("subject") or "").strip()
        content = str(
            msg_body.get("text")
            or msg_body.get("content")
            or msg_body.get("summary")
            or msg_body.get("message")
            or ""
        ).strip()
        image = str(msg_body.get("image") or "").strip()

        if image:
            content = f"{content}\n\n图片：{image}" if content else f"图片：{image}"

        if not title:
            title = content[:50] if content else "MoviePilot 消息通知"
        if not content:
            content = title

        return title, content

    def _send_message(self, title: str, content: str) -> Tuple[bool, str]:
        if not self._token:
            return False, "请先配置 token 并保存"

        normalized_title = title or "MoviePilot 消息通知"
        normalized_content = content or normalized_title or "MoviePilot 消息通知"
        payload = {
            "token": self._token,
            "title": normalized_title,
            "content": normalized_content,
            "jpush": {
                "title": normalized_title,
                "content": normalized_content,
                "msg_content": normalized_content
            }
        }

        try:
            res = RequestUtils(
                content_type="application/json",
                headers={"X-API-Key": self._api_key}
            ).post_res(self._api_url, json=payload)

            if res is None:
                return False, "未获取到接口返回信息"

            if 200 <= res.status_code < 300:
                try:
                    ret_json = res.json()
                except Exception:
                    return True, "消息发送成功"

                if isinstance(ret_json, dict):
                    code = ret_json.get("code")
                    success = ret_json.get("success")
                    message = ret_json.get("message") or ret_json.get("msg") or "消息发送成功"

                    if success is False:
                        return False, str(message)

                    if code not in (None, 0, 200, "0", "200"):
                        return False, str(message)

                    return True, str(message)

                return True, "消息发送成功"

            return False, f"HTTP {res.status_code}: {res.reason}"
        except Exception as err:
            logger.error(f"App Push消息发送失败：{err}")
            return False, str(err)

    def _save_test_result(self, success: bool, message: str):
        self.save_data("last_test_result", {
            "success": success,
            "message": message,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    def _format_test_result(self) -> str:
        test_result = self.get_data("last_test_result") or {}
        if not test_result:
            return "最近一次测试结果：暂无记录"

        status = "成功" if test_result.get("success") else "失败"
        message = test_result.get("message") or "无返回信息"
        time = test_result.get("time") or "未知时间"
        return f"最近一次测试结果：{status} | 时间：{time} | 返回：{message}"

    def stop_service(self):
        pass
