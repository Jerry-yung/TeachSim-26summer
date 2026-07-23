from __future__ import annotations


DEFAULT_TEACHER_QUESTIONS = [
    {
        "id": "duration",
        "type": "radio",
        "label": "预计本次上课时长？",
        "emoji": "⏱️",
        "required": True,
        "skippable": False,
        "options": ["30 分钟", "40 分钟", "45 分钟", "50 分钟", "60 分钟"],
    },
    {
        "id": "grade",
        "type": "radio",
        "label": "您的学生是哪个年级？",
        "emoji": "🎓",
        "required": True,
        "skippable": False,
        "options": ["初一", "初二", "初三", "高一", "高二", "高三"],
    },
    {
        "id": "class_level",
        "type": "radio",
        "label": "您希望授课的班级类型是？",
        "emoji": "🏫",
        "required": True,
        "skippable": False,
        "options": ["重点班", "普通班", "平行班"],
    },
    {
        "id": "student_level",
        "type": "radio",
        "label": "您如何判断这节课的学生整体基础？",
        "emoji": "📊",
        "required": False,
        "skippable": True,
        "options": [
            "扎实：大多数同学有充分的前置基础",
            "中等：部分同学有基础，部分较薄弱",
            "较弱：从零开始，需要基础性引导",
        ],
    },
    {
        "id": "lesson_goal",
        "type": "radio",
        "label": "本节课您希望学生主要达成哪类目标？",
        "emoji": "🎯",
        "allow_multiple": True,
        "required": False,
        "skippable": True,
        "options": [
            "知识理解与记忆",
            "技能掌握与方法运用",
            "思维拓展与探究讨论",
            "情感体验与价值建构",
        ],
    },
    {
        "id": "practice_focus",
        "type": "radio",
        "label": "本次课您最想在哪个方面有所突破？",
        "hint": "课后报告将对此进行重点定向分析",
        "emoji": "💡",
        "allow_multiple": True,
        "required": False,
        "skippable": True,
        "options": [
            "课堂节奏把控",
            "知识点衔接流畅度",
            "提问质量与互动引导",
            "语言表达与亲和力",
            "时间分配合理性",
        ],
    },
    {
        "id": "discipline_simulation_level",
        "type": "radio",
        "label": "课堂纪律事件模拟强度（睡觉/交头接耳）",
        "emoji": "🚨",
        "required": False,
        "skippable": True,
        "options": ["高频（重点训练）", "中频", "低频", "关闭（不触发）"],
    },
    {
        "id": "atmosphere",
        "type": "radio",
        "label": "您期望的课堂氛围是？",
        "emoji": "🌡️",
        "required": True,
        "skippable": False,
        "options": ["活跃互动型", "均衡参与型", "沉浸讲解型"],
    },
]


STUDENT_STATES = {
    "student_xm": {
        "student_id": "student_xm",
        "student_type": "xueyou",
        "is_hand_raised": False,
    },
    "student_xw": {
        "student_id": "student_xw",
        "student_type": "gangjing",
        "is_hand_raised": True,
    },
    "student_xw2": {
        "student_id": "student_xw2",
        "student_type": "xuekun",
        "is_hand_raised": False,
    },
    "student_xl": {
        "student_id": "student_xl",
        "student_type": "xuekun",
        "is_hand_raised": True,
    },
}
