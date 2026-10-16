"""Mock 规划器：关键词规则拆步，无外网、可复现演示。"""


class MockPlanner:
    """确定性规则，保证无 Key / 答辩可演示。"""

    name = "mock"

    async def plan(self, goal: str, context: str) -> tuple[str, list[dict]]:
        del context  # mock 不依赖画布细节
        text = (goal or "").strip().lower()
        # 同时保留中文原文匹配
        raw = goal or ""

        steps: list[dict] = []
        want_matting = any(
            key in raw for key in ("去背", "抠图", "透明背景", "去掉背景", "去除背景")
        )
        want_bright = any(
            key in raw for key in ("提亮", "亮一点", "亮度", "更亮", "提高亮度")
        )
        want_flip = any(key in raw for key in ("翻转", "镜像", "水平翻"))

        if want_matting:
            steps.append({"tool_name": "remove_background", "params": {}})
        if want_bright:
            steps.append(
                {
                    "tool_name": "adjust_image",
                    "params": {"brightness": 0.2, "contrast": 0.0, "saturation": 0.0},
                }
            )
        if want_flip:
            steps.append({"tool_name": "flip_layer", "params": {}})

        # 英文兜底
        if not steps:
            if "background" in text or "matting" in text:
                steps.append({"tool_name": "remove_background", "params": {}})
            if "bright" in text or "light" in text:
                steps.append(
                    {
                        "tool_name": "adjust_image",
                        "params": {
                            "brightness": 0.2,
                            "contrast": 0.0,
                            "saturation": 0.0,
                        },
                    }
                )
            if "flip" in text or "mirror" in text:
                steps.append({"tool_name": "flip_layer", "params": {}})

        if not steps:
            return (
                "没识别出可用的修图步骤。可以试试「去背」「提亮」「翻转」，或点工具栏。",
                [],
            )

        labels = []
        for step in steps:
            name = step["tool_name"]
            if name == "remove_background":
                labels.append("去背景")
            elif name == "adjust_image":
                labels.append("提亮")
            elif name == "flip_layer":
                labels.append("水平翻转")
            else:
                labels.append(name)

        if len(labels) == 1:
            reply = f"好，将执行：{labels[0]}。确认后开始。"
        else:
            reply = f"将按以下步骤执行：{' → '.join(labels)}。确认后开始。"
        return reply, steps
