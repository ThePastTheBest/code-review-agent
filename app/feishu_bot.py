import asyncio
import json
import logging
import os
import re
import ssl
import threading

if os.environ.get("SKIP_SSL_VERIFY", "").lower() in ("1", "true"):
    _orig_create_default_context = ssl.create_default_context

    def _create_unverified_context(*args, **kwargs):
        ctx = _orig_create_default_context(*args, **kwargs)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    ssl.create_default_context = _create_unverified_context
    ssl._create_default_https_context = ssl._create_unverified_context

import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1

from app.core.config import settings
from app.models.review import ReviewDecision
from app.service.feishu_service import FeishuService
from app.service.gitlab_service import GitLabService
from app.service.review_service import ReviewService

logger = logging.getLogger(__name__)

_MENTION_PLACEHOLDER_RE = re.compile(r"@_user_\d+")

HELP_TEXT = (
    "请发送三行文本来发起代码审查：\n"
    "第一行：GitLab 项目路径（如 group/repo）\n"
    "第二行：源分支\n"
    "第三行：目标分支"
)

feishu_service = FeishuService()


def _run_review_async(
    message_id: str, chat_id: str, project: str, source_branch: str, target_branch: str
) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            _do_review(message_id, chat_id, project, source_branch, target_branch)
        )
    finally:
        loop.close()


async def _do_review(
    message_id: str, chat_id: str, project: str, source_branch: str, target_branch: str
) -> None:
    try:
        gitlab_service = GitLabService()

        try:
            gitlab_service.get_project(project)
        except Exception:
            feishu_service.reply_text(message_id, f"项目不存在或无权访问: {project}")
            return

        if not gitlab_service.check_branch_exists(project, source_branch):
            feishu_service.reply_text(message_id, f"源分支不存在: {source_branch}")
            return

        if not gitlab_service.check_branch_exists(project, target_branch):
            feishu_service.reply_text(message_id, f"目标分支不存在: {target_branch}")
            return

        review_service = ReviewService()
        result = await review_service.execute_review(
            project=project,
            source_branch=source_branch,
            target_branch=target_branch,
        )

        mr_url = result.get("mr_url", "未知")
        decision = "未知"
        review_result = result.get("review_result")
        if review_result and isinstance(review_result, dict):
            raw = review_result.get("reviewDecision", "")
            try:
                decision = ReviewDecision(raw).label
            except ValueError:
                decision = raw

        reply = f"代码审查完成\n审查决定: {decision}\nMR 链接: {mr_url}"
        feishu_service.reply_text(message_id, reply)

    except Exception as e:
        logger.exception("飞书触发的代码审查失败")
        feishu_service.reply_text(message_id, f"代码审查失败: {str(e)}")


def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
    message = data.event.message

    if message.message_type != "text":
        feishu_service.reply_text(message.message_id, "请发送文本消息\n\n" + HELP_TEXT)
        return

    try:
        raw_text = json.loads(message.content).get("text", "")
    except (json.JSONDecodeError, TypeError):
        feishu_service.reply_text(message.message_id, "消息解析失败\n\n" + HELP_TEXT)
        return

    text = _MENTION_PLACEHOLDER_RE.sub("", raw_text).strip()

    command = feishu_service.parse_review_command(text)
    if command is None:
        feishu_service.reply_text(message.message_id, HELP_TEXT)
        return

    feishu_service.reply_text(
        message.message_id,
        f"收到，正在审查中，请稍候...\n"
        f"项目: {command.project}\n"
        f"源分支: {command.source_branch}\n"
        f"目标分支: {command.target_branch}",
    )

    thread = threading.Thread(
        target=_run_review_async,
        args=(
            message.message_id,
            message.chat_id,
            command.project,
            command.source_branch,
            command.target_branch,
        ),
        daemon=True,
    )
    thread.start()


def start_feishu_bot() -> None:
    if not settings.feishu.enabled:
        logger.info("飞书机器人已禁用")
        return

    if not settings.feishu_env.app_id or not settings.feishu_env.app_secret:
        logger.warning("飞书 APP_ID 或 APP_SECRET 未配置，跳过启动")
        return

    event_handler = (
        lark.EventDispatcherHandler.builder("", "")
        .register_p2_im_message_receive_v1(do_p2_im_message_receive_v1)
        .build()
    )

    ws_client = lark.ws.Client(
        settings.feishu_env.app_id,
        settings.feishu_env.app_secret,
        event_handler=event_handler,
        log_level=lark.LogLevel.INFO,
    )

    thread = threading.Thread(target=ws_client.start, daemon=True)
    thread.start()
    logger.info("飞书机器人已启动 (WebSocket 长连接)")
