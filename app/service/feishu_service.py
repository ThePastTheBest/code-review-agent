import json
import logging
from dataclasses import dataclass
from typing import Optional

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ReviewCommand:
    project: str
    source_branch: str
    target_branch: str


class FeishuService:

    def __init__(self):
        self.client = (
            lark.Client.builder()
            .app_id(settings.feishu_env.app_id)
            .app_secret(settings.feishu_env.app_secret)
            .build()
        )

    def parse_review_command(self, text: str) -> Optional[ReviewCommand]:
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if len(lines) != 3:
            return None
        return ReviewCommand(
            project=lines[0],
            source_branch=lines[1],
            target_branch=lines[2],
        )

    def reply_text(self, message_id: str, text: str) -> None:
        content = json.dumps({"text": text})
        request = (
            ReplyMessageRequest.builder()
            .message_id(message_id)
            .request_body(
                ReplyMessageRequestBody.builder()
                .content(content)
                .msg_type("text")
                .build()
            )
            .build()
        )
        response = self.client.im.v1.message.reply(request)
        if not response.success():
            logger.error(
                "reply failed, code: %s, msg: %s", response.code, response.msg
            )

    def send_text(self, chat_id: str, text: str) -> None:
        content = json.dumps({"text": text})
        request = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("text")
                .content(content)
                .build()
            )
            .build()
        )
        response = self.client.im.v1.message.create(request)
        if not response.success():
            logger.error(
                "send failed, code: %s, msg: %s", response.code, response.msg
            )
