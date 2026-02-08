{
  "type": "object",
  "properties": {
    "mrDescription": {
      "type": "string",
      "description": "按照 MR 描述模板生成的完整 Markdown 格式影响面分析报告，可直接用作 MR 描述"
    },

    "issues": {
      "type": "array",
      "description": "代码问题列表",
      "items": {
        "type": "object",
        "properties": {
          "severity": {
            "type": "string",
            "enum": ["low", "medium", "high", "critical"]
          },
          "category": {
            "type": "string",
            "enum": ["bug", "security", "performance", "stability", "maintainability", "style"]
          },
          "file": {
            "type": "string",
            "description": "问题所在文件路径"
          },
          "line": {
            "type": "number",
            "description": "问题所在行号"
          },
          "description": {
            "type": "string",
            "description": "问题描述"
          },
          "suggestion": {
            "type": "string",
            "description": "修改建议"
          }
        },
        "required": ["severity", "category", "file", "description", "suggestion"]
      }
    },

    "reviewDecision": {
      "type": "string",
      "enum": ["approve", "approve-with-comments", "request-changes"],
      "description": "审查决定"
    }
  },

  "required": [
    "mrDescription",
    "issues",
    "reviewDecision"
  ]
}
