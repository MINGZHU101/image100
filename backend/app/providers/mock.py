"""Mock 规划器：关键词规则拆步，无外网、可复现演示。"""


class MockPlanner:
    """确定性规则，保证无 Key / 答辩可演示。"""

    name = "mock"

    async def plan(self, goal: str, context: str) -> tuple[str, list[dict]]:
        text = (goal or "").strip().lower()
        raw = goal or ""
        ctx = context or ""
        has_selection = "选区：有" in ctx
        already_split = "layer_background" in ctx and "layer_subject" in ctx

        steps: list[dict] = []
        want_split = any(
            key in raw
            for key in ("拆层", "分出主体", "分离背景", "主体和背景", "分开主体")
        )
        want_matting = any(
            key in raw for key in ("去背", "抠图", "透明背景", "去掉背景", "去除背景")
        )
        want_bright = any(
            key in raw for key in ("提亮", "亮一点", "亮度", "更亮", "提高亮度")
        )
        want_local = any(
            key in raw for key in ("局部", "选区", "框内", "这块", "圈内")
        )
        want_flip = any(key in raw for key in ("翻转", "镜像", "水平翻"))

        if want_split:
            if already_split:
                return ("画面已经拆成背景和主体了，可以直接在图层面板操作。", [])
            steps.append({"tool_name": "split_layers", "params": {}})

        if want_bright and want_local:
            if not has_selection:
                return (
                    "请先在画布上框选或涂抹选区，再试「局部提亮」。",
                    [],
                )
            steps.append(
                {
                    "tool_name": "adjust_region",
                    "params": {
                        "brightness": 0.2,
                        "contrast": 0.0,
                        "saturation": 0.0,
                    },
                }
            )
            want_bright = False

        if want_matting and not want_split:
            steps.append({"tool_name": "remove_background", "params": {}})
        if want_bright:
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
        if want_flip:
            steps.append({"tool_name": "flip_layer", "params": {}})

        if not steps:
            if "split" in text or "layer" in text:
                if already_split:
                    return ("画面已经拆层，可在图层面板切换显隐。", [])
                steps.append({"tool_name": "split_layers", "params": {}})
            if "background" in text or "matting" in text:
                steps.append({"tool_name": "remove_background", "params": {}})
            if ("region" in text or "local" in text) and (
                "bright" in text or "light" in text
            ):
                if not has_selection:
                    return (
                        "请先在画布上框选或涂抹选区，再试局部提亮。",
                        [],
                    )
                steps.append(
                    {
                        "tool_name": "adjust_region",
                        "params": {
                            "brightness": 0.2,
                            "contrast": 0.0,
                            "saturation": 0.0,
                        },
                    }
                )
            elif "bright" in text or "light" in text:
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
                "没识别出可用的修图步骤。可以试试「拆层」「去背」「提亮」「局部提亮」「翻转」。",
                [],
            )

        labels = []
        for step in steps:
            name = step["tool_name"]
            if name == "remove_background":
                labels.append("去背景")
            elif name == "adjust_image":
                labels.append("提亮")
            elif name == "adjust_region":
                labels.append("局部提亮")
            elif name == "flip_layer":
                labels.append("水平翻转")
            elif name == "split_layers":
                labels.append("拆层")
            else:
                labels.append(name)

        if len(labels) == 1:
            reply = f"好，将执行：{labels[0]}。确认后开始。"
        else:
            reply = f"将按以下步骤执行：{' → '.join(labels)}。确认后开始。"
        return reply, steps
