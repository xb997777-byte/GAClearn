COUNT_PER_POINT = 72
DEFAULT_SCENES = ["课堂", "校园", "备考", "职场", "阅读", "日常"]
CORE_ROLES = {"subject", "predicate", "object", "complement", "gerund"}


def _pick(items, index, step):
    return items[(index * step) % len(items)]


def _segment(
    text,
    translation,
    role_type,
    label="",
    explanation="",
    color_token="",
    is_core=None,
    annotate=True,
    joiner=None,
):
    return {
        "text": text,
        "translation": translation,
        "role_type": role_type,
        "label": label,
        "explanation": explanation,
        "color_token": color_token or role_type,
        "is_core": is_core,
        "annotate": annotate,
        "joiner": joiner,
    }


def _compose_sentence(segments):
    sentence = ""
    annotations = []
    chunks = []
    core_texts = []

    for index, item in enumerate(segments):
        joiner = item.get("joiner")
        if joiner is None:
            joiner = "" if index == 0 else " "
        sentence += joiner
        start_index = len(sentence)
        sentence += item["text"]
        end_index = len(sentence)

        if not item.get("annotate", True):
            continue

        is_core = item["is_core"]
        if is_core is None:
            is_core = item["role_type"] in CORE_ROLES

        annotations.append(
            {
                "text_span": item["text"],
                "start_index": start_index,
                "end_index": end_index,
                "role_type": item["role_type"],
                "grammar_label": item["label"],
                "explanation": item["explanation"],
                "color_token": item["color_token"],
                "is_core": is_core,
                "sort_order": len(annotations) + 1,
            }
        )
        chunks.append(
            {
                "en": item["text"],
                "cn": item["translation"],
                "role_label": item["label"],
                "note": item["explanation"],
                "is_core": is_core,
            }
        )
        if is_core:
            core_texts.append(item["text"])

    sentence = sentence.strip()
    if sentence and sentence[-1] not in ".?!":
        sentence = f"{sentence}."

    main_structure = " ".join(core_texts).strip()
    if main_structure and main_structure[-1] not in ".?!":
        main_structure = f"{main_structure}."

    return sentence, annotations, main_structure, chunks


def _build_entry(point_meta, order_in_point, segments, translation_cn, summary, analysis, tags, scene_tag, is_long_sentence=False):
    sentence, annotations, main_structure, chunks = _compose_sentence(segments)
    return {
        "order_in_point": order_in_point,
        "sentence": sentence,
        "translation_cn": translation_cn,
        "summary": summary,
        "analysis": analysis,
        "main_structure": main_structure,
        "difficulty": point_meta["difficulty"],
        "scene_tag": scene_tag,
        "grammar_tags": tags,
        "chunk_breakdown": chunks,
        "practice_type": "choice",
        "practice_prompt": point_meta["practice_prompt"],
        "practice_options": point_meta["practice_options"],
        "practice_answer": point_meta["practice_answer"],
        "practice_explanation": point_meta["practice_explanation"],
        "is_long_sentence": is_long_sentence,
        "annotations": annotations,
    }


def _generate_basic_svo(point_meta, subjects, predicates, objects, adverbials, summary, tags):
    result = []
    for index in range(COUNT_PER_POINT):
        subject = _pick(subjects, index, 1)
        predicate = _pick(predicates, index, 2)
        object_item = _pick(objects, index, 3)
        adverbial = _pick(adverbials, index, 5)
        segments = [
            _segment(
                subject[0],
                subject[1],
                "subject",
                label="主语",
                explanation=f"{subject[0]} 是句子的主语，表示动作的发出者。",
            ),
            _segment(
                predicate[0],
                predicate[1],
                "predicate",
                label=point_meta["title"],
                explanation=f"{predicate[0]} 是句子的谓语部分，体现 {point_meta['title']} 的核心结构。",
            ),
            _segment(
                object_item[0],
                object_item[1],
                "object",
                label="宾语",
                explanation=f"{object_item[0]} 是谓语动作直接作用的对象。",
            ),
            _segment(
                adverbial[0],
                adverbial[1],
                "adverbial",
                label="状语",
                explanation=f"{adverbial[0]} 补充动作发生的时间、地点或方式。",
                is_core=False,
            ),
        ]
        translation_cn = f"{subject[1]}{adverbial[1]}{predicate[1]}{object_item[1]}。"
        analysis = (
            f"句子主干是 {subject[0]} {predicate[0]} {object_item[0]}。"
            f"{adverbial[0]} 作为状语补充背景信息，帮助学习者在完整句子中识别主干。"
        )
        result.append(
            _build_entry(
                point_meta,
                index + 1,
                segments,
                translation_cn,
                summary,
                analysis,
                tags,
                _pick(DEFAULT_SCENES, index, 1),
            )
        )
    return result


def _generate_passive(point_meta):
    subjects = [
        ("The review sheet", "这份复习表"),
        ("The speaking task", "这项口语任务"),
        ("The final outline", "这份最终提纲"),
        ("The homework list", "这份作业清单"),
        ("The grammar note", "这条语法笔记"),
        ("The video lesson", "这节视频课程"),
        ("The reading plan", "这份阅读计划"),
        ("The classroom poster", "这张课堂海报"),
        ("The practice file", "这个练习文件"),
        ("The sample answer", "这份范文答案"),
        ("The listening script", "这份听力稿"),
        ("The course page", "这个课程页面"),
    ]
    predicates = [
        ("was prepared", "被整理好"),
        ("is used", "被使用"),
        ("was shared", "被分享"),
        ("is explained", "被讲解"),
        ("was completed", "被完成"),
        ("is displayed", "被展示"),
        ("was updated", "被更新"),
        ("is reviewed", "被复查"),
    ]
    adverbials = [
        ("for new learners", "供新学习者使用"),
        ("during the workshop", "在工作坊期间"),
        ("before the exam", "在考试前"),
        ("in the morning class", "在上午的课堂上"),
        ("on the online platform", "在在线平台上"),
        ("with extra notes", "并附有额外说明"),
    ]
    agents = [
        ("by the teaching assistant", "由教学助教"),
        ("by the course designer", "由课程设计者"),
        ("by the senior coach", "由资深教练"),
        ("by the study group leader", "由学习小组长"),
        ("by the language teacher", "由语言老师"),
        ("by the training team", "由培训团队"),
    ]
    summary = "被动语态把动作的承受者放在句首，常用于突出结果、流程或客观描述。"
    tags = ["被动语态", "受事主语", "考试常见结构"]
    result = []
    for index in range(COUNT_PER_POINT):
        subject = _pick(subjects, index, 1)
        predicate = _pick(predicates, index, 2)
        adverbial = _pick(adverbials, index, 3)
        agent = _pick(agents, index, 5)
        segments = [
            _segment(subject[0], subject[1], "subject", label="受事主语", explanation=f"{subject[0]} 是动作的承受者，因此放在句首。"),
            _segment(
                predicate[0],
                predicate[1],
                "predicate",
                label="被动结构",
                explanation=f"{predicate[0]} 由 be 动词和过去分词构成，体现被动语态。",
            ),
            _segment(
                adverbial[0],
                adverbial[1],
                "adverbial",
                label="补充状语",
                explanation=f"{adverbial[0]} 补充说明用途、场景或时间。",
            ),
            _segment(
                agent[0],
                agent[1],
                "agent",
                label="动作发出者",
                explanation=f"{agent[0]} 用 by 引出真正执行动作的人或团队。",
                is_core=False,
            ),
        ]
        translation_cn = f"{subject[1]}{predicate[1]}，{adverbial[1]}，{agent[1]}处理。"
        analysis = f"该句重点观察 {predicate[0]} 这一被动结构。句首的 {subject[0]} 不是动作执行者，而是动作承受者。"
        result.append(
            _build_entry(
                point_meta,
                index + 1,
                segments,
                translation_cn,
                summary,
                analysis,
                tags,
                _pick(DEFAULT_SCENES, index, 1),
            )
        )
    return result


def _generate_infinitive(point_meta):
    subjects = [
        ("The new student", "这位新同学"),
        ("The course tutor", "这位课程导师"),
        ("The team leader", "这位小组长"),
        ("The speaking coach", "这位口语教练"),
        ("The careful reader", "这位认真阅读的人"),
        ("The exam candidate", "这位备考生"),
        ("The office trainer", "这位职场培训师"),
        ("The class monitor", "这位班长"),
        ("The note-taking learner", "这位爱记笔记的学习者"),
        ("The online teacher", "这位线上老师"),
        ("The project assistant", "这位项目助理"),
        ("The grammar beginner", "这位语法初学者"),
    ]
    predicates = [
        ("uses", "使用"),
        ("keeps", "保留"),
        ("checks", "检查"),
        ("revises", "修改"),
        ("reads", "阅读"),
        ("organizes", "整理"),
        ("collects", "收集"),
        ("marks", "标记"),
    ]
    objects = [
        ("flash cards", "单词卡片"),
        ("a sentence map", "句子结构图"),
        ("the practice notes", "练习笔记"),
        ("the model paragraph", "范文段落"),
        ("the review list", "复习清单"),
        ("the grammar chart", "语法图表"),
        ("the key examples", "关键例句"),
        ("the class summary", "课堂总结"),
    ]
    infinitives = [
        ("to remember new phrases", "记住新短语"),
        ("to understand the main clause", "理解主句"),
        ("to check the verb form", "检查动词形式"),
        ("to improve speaking accuracy", "提高口语准确度"),
        ("to review the difficult pattern", "复习较难结构"),
        ("to compare two sentence types", "对比两种句型"),
        ("to notice the tense marker", "注意时态标记"),
        ("to build a clearer outline", "建立更清晰的提纲"),
    ]
    summary = "不定式常表示目的、计划或结果，在学习场景中常用来说明“做某事是为了什么”。"
    tags = ["不定式", "目的表达", "句子补足成分"]
    result = []
    for index in range(COUNT_PER_POINT):
        subject = _pick(subjects, index, 1)
        predicate = _pick(predicates, index, 2)
        object_item = _pick(objects, index, 3)
        infinitive = _pick(infinitives, index, 5)
        segments = [
            _segment(subject[0], subject[1], "subject", label="主语", explanation=f"{subject[0]} 是执行动作的人。"),
            _segment(predicate[0], predicate[1], "predicate", label="谓语", explanation=f"{predicate[0]} 描述主语当前采取的动作。"),
            _segment(object_item[0], object_item[1], "object", label="宾语", explanation=f"{object_item[0]} 是主语处理或使用的对象。"),
            _segment(
                infinitive[0],
                infinitive[1],
                "infinitive",
                label="不定式结构",
                explanation=f"{infinitive[0]} 解释前面动作的目的或结果。",
                is_core=False,
            ),
        ]
        translation_cn = f"{subject[1]}{predicate[1]}{object_item[1]}，来{infinitive[1]}。"
        analysis = f"句子核心动作是 {subject[0]} {predicate[0]} {object_item[0]}，不定式 {infinitive[0]} 用来补充目的。"
        result.append(
            _build_entry(
                point_meta,
                index + 1,
                segments,
                translation_cn,
                summary,
                analysis,
                tags,
                _pick(DEFAULT_SCENES, index, 1),
            )
        )
    return result


def _generate_gerund(point_meta):
    gerunds = [
        ("Reading aloud", "大声朗读"),
        ("Reviewing the outline", "复习提纲"),
        ("Comparing sentence patterns", "比较句型"),
        ("Writing short summaries", "写简短总结"),
        ("Repeating key phrases", "重复关键短语"),
        ("Checking the subject and verb", "检查主谓结构"),
        ("Highlighting the main clause", "标出主句"),
        ("Listening to model sentences", "听范例句子"),
        ("Taking quick notes", "快速记笔记"),
        ("Grouping words by meaning", "按意义归类单词"),
        ("Discussing one example at a time", "逐个讨论例句"),
        ("Reviewing after class", "课后复盘"),
    ]
    predicates = [
        ("helps", "有助于"),
        ("allows", "能帮助"),
        ("encourages", "能促进"),
        ("enables", "能使"),
        ("teaches", "能让人学会"),
        ("reminds", "会提醒"),
    ]
    objects = [
        ("many learners build confidence", "许多学习者建立信心"),
        ("students notice tense changes", "学生注意到时态变化"),
        ("beginners follow long sentences", "初学者跟上长句结构"),
        ("the whole class remember the rule", "全班记住这个规则"),
        ("careful readers catch hidden clues", "认真阅读的人抓住隐藏线索"),
        ("new users organize their notes", "新用户整理好自己的笔记"),
    ]
    adverbials = [
        ("over time", "随着时间推进"),
        ("during revision", "在复习时"),
        ("in a short lesson", "在短短一节课里"),
        ("before the final test", "在最终测试前"),
        ("in daily practice", "在日常练习中"),
        ("with less pressure", "在更小压力下"),
    ]
    summary = "动名词短语既可以作主语，也可以作宾语。这里重点观察“动名词短语作主语”的表达。"
    tags = ["动名词", "非谓语", "作主语"]
    result = []
    for index in range(COUNT_PER_POINT):
        gerund = _pick(gerunds, index, 1)
        predicate = _pick(predicates, index, 2)
        object_item = _pick(objects, index, 3)
        adverbial = _pick(adverbials, index, 5)
        segments = [
            _segment(
                gerund[0],
                gerund[1],
                "gerund",
                label="动名词短语作主语",
                explanation=f"{gerund[0]} 是动名词短语，在这里整体充当主语。",
                color_token="gerund",
            ),
            _segment(predicate[0], predicate[1], "predicate", label="谓语", explanation=f"{predicate[0]} 说明前面这个动作带来的影响。"),
            _segment(object_item[0], object_item[1], "object", label="宾语/结果", explanation=f"{object_item[0]} 是动名词行为带来的结果或影响。"),
            _segment(adverbial[0], adverbial[1], "adverbial", label="状语", explanation=f"{adverbial[0]} 补充说明发生条件或范围。"),
        ]
        translation_cn = f"{gerund[1]}{adverbial[1]}{predicate[1]}{object_item[1]}。"
        analysis = f"整句把 {gerund[0]} 放在句首，提醒学习者注意：非谓语结构也可以直接充当主语。"
        result.append(
            _build_entry(
                point_meta,
                index + 1,
                segments,
                translation_cn,
                summary,
                analysis,
                tags,
                _pick(DEFAULT_SCENES, index, 1),
            )
        )
    return result


def _generate_relative_clause(point_meta):
    subjects = [
        ("The teacher", "老师"),
        ("The article", "文章"),
        ("The student", "学生"),
        ("The coach", "教练"),
        ("The report", "报告"),
        ("The paragraph", "段落"),
        ("The app", "这个应用"),
        ("The exercise", "这道练习"),
        ("The example", "这个例句"),
        ("The outline", "提纲"),
        ("The classmate", "同学"),
        ("The speaker", "发言人"),
    ]
    clauses = [
        ("who checks our essays every week", "每周检查我们作文的"),
        ("that we discussed yesterday", "我们昨天讨论过的"),
        ("who always asks careful questions", "总会提出细致问题的"),
        ("that explains the pattern clearly", "把这个结构讲得很清楚的"),
        ("who organizes the review session", "负责组织复习会的"),
        ("that contains several long clauses", "包含多个长从句的"),
        ("who records every useful phrase", "会记录每个有用短语的"),
        ("that many beginners find difficult", "许多初学者觉得很难的"),
    ]
    predicates = [
        ("offers", "提供"),
        ("gives", "给出"),
        ("shows", "展示"),
        ("brings", "带来"),
        ("keeps", "保留"),
        ("shares", "分享"),
    ]
    objects = [
        ("clear advice", "清晰的建议"),
        ("a better example", "一个更好的例子"),
        ("extra practice", "额外练习"),
        ("useful feedback", "有用的反馈"),
        ("strong support", "强有力的支持"),
        ("practical ideas", "实用思路"),
    ]
    adverbials = [
        ("before class", "在课前"),
        ("after the lecture", "在讲解之后"),
        ("during the meeting", "在讨论时"),
        ("for the whole team", "面向整个团队"),
        ("in every lesson", "在每节课里"),
        ("at the right moment", "在合适的时候"),
    ]
    summary = "定语从句放在名词后面，用来进一步限定或说明这个名词。"
    tags = ["定语从句", "关系代词", "名词修饰"]
    result = []
    for index in range(COUNT_PER_POINT):
        subject = _pick(subjects, index, 1)
        clause = _pick(clauses, index, 2)
        predicate = _pick(predicates, index, 3)
        object_item = _pick(objects, index, 5)
        adverbial = _pick(adverbials, index, 7)
        segments = [
            _segment(subject[0], subject[1], "subject", label="先行词", explanation=f"{subject[0]} 是被定语从句进一步说明的核心名词。"),
            _segment(
                clause[0],
                clause[1],
                "clause",
                label="定语从句",
                explanation=f"{clause[0]} 放在先行词后面，对前面的名词进行限定。",
                is_core=False,
            ),
            _segment(predicate[0], predicate[1], "predicate", label="主句谓语", explanation=f"{predicate[0]} 是主句的真正谓语。"),
            _segment(object_item[0], object_item[1], "object", label="宾语", explanation=f"{object_item[0]} 是主句谓语的宾语。"),
            _segment(adverbial[0], adverbial[1], "adverbial", label="状语", explanation=f"{adverbial[0]} 补充动作发生的时间或范围。"),
        ]
        translation_cn = f"{clause[1]}{subject[1]}{adverbial[1]}{predicate[1]}{object_item[1]}。"
        analysis = f"阅读这句话时，先抓主干 {subject[0]} {predicate[0]} {object_item[0]}，再把 {clause[0]} 还原成修饰语。"
        result.append(
            _build_entry(
                point_meta,
                index + 1,
                segments,
                translation_cn,
                summary,
                analysis,
                tags,
                _pick(DEFAULT_SCENES, index, 1),
                is_long_sentence=True,
            )
        )
    return result


def _generate_adverbial_clause(point_meta):
    clauses = [
        ("When the lesson begins", "当课程开始时"),
        ("Because the example is familiar", "因为这个例子很熟悉"),
        ("Although the sentence looks long", "虽然这个句子看起来很长"),
        ("If the topic is clear", "如果主题很明确"),
        ("Before the discussion starts", "在讨论开始之前"),
        ("After the teacher pauses", "在老师停顿之后"),
        ("While the group is reading", "当小组正在阅读时"),
        ("Since the notes are ready", "既然笔记已经准备好了"),
    ]
    subjects = [
        ("the students", "学生们"),
        ("the coach", "这位教练"),
        ("the whole team", "整个团队"),
        ("the new learner", "这位新学习者"),
        ("the writing group", "写作小组"),
        ("the class", "全班同学"),
    ]
    predicates = [
        ("open", "打开"),
        ("review", "复习"),
        ("compare", "比较"),
        ("check", "检查"),
        ("underline", "画出"),
        ("rewrite", "改写"),
    ]
    objects = [
        ("their notebooks", "自己的笔记本"),
        ("the key pattern", "关键结构"),
        ("the sample answer", "范例答案"),
        ("the verb form", "动词形式"),
        ("the main clause", "主句"),
        ("the difficult paragraph", "较难的段落"),
    ]
    adverbials = [
        ("immediately", "立刻"),
        ("with more confidence", "更有信心地"),
        ("step by step", "一步一步地"),
        ("without extra help", "不借助额外帮助地"),
        ("much more carefully", "更加仔细地"),
        ("in the right order", "按照正确顺序"),
    ]
    summary = "状语从句负责交代时间、原因、条件、让步等背景信息，主句才是核心判断。"
    tags = ["状语从句", "时间原因条件", "主从结构"]
    result = []
    for index in range(COUNT_PER_POINT):
        clause = _pick(clauses, index, 1)
        subject = _pick(subjects, index, 2)
        predicate = _pick(predicates, index, 3)
        object_item = _pick(objects, index, 5)
        adverbial = _pick(adverbials, index, 7)
        segments = [
            _segment(clause[0], clause[1], "clause", label="状语从句", explanation=f"{clause[0]} 先交代背景，再进入主句内容。", is_core=False),
            _segment(",", "", "connector", annotate=False, joiner=""),
            _segment(subject[0], subject[1], "subject", label="主句主语", explanation=f"{subject[0]} 是主句的主语。"),
            _segment(predicate[0], predicate[1], "predicate", label="主句谓语", explanation=f"{predicate[0]} 是主句真正要判断的动作。"),
            _segment(object_item[0], object_item[1], "object", label="主句宾语", explanation=f"{object_item[0]} 是主句谓语的宾语。"),
            _segment(adverbial[0], adverbial[1], "adverbial", label="方式状语", explanation=f"{adverbial[0]} 进一步说明动作进行的方式。"),
        ]
        translation_cn = f"{clause[1]}，{subject[1]}{adverbial[1]}{predicate[1]}{object_item[1]}。"
        analysis = f"分析这类句子时，先把 {clause[0]} 识别为背景成分，再抓住主干 {subject[0]} {predicate[0]} {object_item[0]}。"
        result.append(
            _build_entry(
                point_meta,
                index + 1,
                segments,
                translation_cn,
                summary,
                analysis,
                tags,
                _pick(DEFAULT_SCENES, index, 1),
                is_long_sentence=True,
            )
        )
    return result


def _generate_noun_clause(point_meta):
    subjects = [
        ("We", "我们"),
        ("The teacher", "老师"),
        ("The report", "报告"),
        ("Many learners", "许多学习者"),
        ("The guide", "这份指南"),
        ("The coach", "教练"),
        ("The research team", "研究团队"),
        ("The article", "这篇文章"),
    ]
    predicates = [
        ("know", "知道"),
        ("shows", "表明"),
        ("explains", "解释"),
        ("confirms", "确认"),
        ("reminds us", "提醒我们"),
        ("suggests", "说明"),
    ]
    clauses = [
        ("that the pattern appears in daily conversation", "这个结构会出现在日常表达中"),
        ("that the final clause changes the tone", "最后一个从句会改变语气"),
        ("that careful reading improves accuracy", "仔细阅读会提高准确度"),
        ("that the verb form carries the tense", "动词形式承载着时态信息"),
        ("that the writer hides the main idea in the middle", "作者把主旨藏在了中间部分"),
        ("that shorter chunks are easier to remember", "较短的意群更容易记住"),
        ("that examples make grammar rules clearer", "例句会让语法规则更清楚"),
        ("that long sentences still have a simple core", "长句同样有简单主干"),
    ]
    adverbials = [
        ("after several lessons", "在上了几节课之后"),
        ("during revision week", "在复习周里"),
        ("in the reading section", "在阅读部分"),
        ("through repeated practice", "通过反复练习"),
        ("after one careful explanation", "经过一次仔细讲解后"),
        ("in real communication", "在真实交流中"),
    ]
    summary = "名词性从句可以在句中充当宾语、主语或表语。这里重点展示“宾语从句”的识别方法。"
    tags = ["名词性从句", "宾语从句", "that 从句"]
    result = []
    for index in range(COUNT_PER_POINT):
        subject = _pick(subjects, index, 1)
        predicate = _pick(predicates, index, 2)
        clause = _pick(clauses, index, 3)
        adverbial = _pick(adverbials, index, 5)
        segments = [
            _segment(subject[0], subject[1], "subject", label="主语", explanation=f"{subject[0]} 是主句主语。"),
            _segment(predicate[0], predicate[1], "predicate", label="主句谓语", explanation=f"{predicate[0]} 引出后面的判断或观点。"),
            _segment(
                clause[0],
                clause[1],
                "clause",
                label="宾语从句",
                explanation=f"{clause[0]} 作为整句的宾语，承接前面的认知类动词。",
            ),
            _segment(adverbial[0], adverbial[1], "adverbial", label="状语", explanation=f"{adverbial[0]} 补充句子的时间或场景。"),
        ]
        translation_cn = f"{subject[1]}{adverbial[1]}{predicate[1]}，{clause[1]}。"
        analysis = f"句子的核心动作是 {subject[0]} {predicate[0]}，后面的 {clause[0]} 整体充当宾语，不能拆成独立句。"
        result.append(
            _build_entry(
                point_meta,
                index + 1,
                segments,
                translation_cn,
                summary,
                analysis,
                tags,
                _pick(DEFAULT_SCENES, index, 1),
                is_long_sentence=True,
            )
        )
    return result


def _generate_comparative(point_meta):
    subjects = [
        ("This summary", "这份总结"),
        ("The new chart", "这张新图表"),
        ("Her explanation", "她的讲解"),
        ("The short passage", "这篇短文"),
        ("Our reading plan", "我们的阅读计划"),
        ("The final answer", "最终答案"),
        ("This grammar note", "这条语法笔记"),
        ("The guided practice", "这个引导练习"),
    ]
    predicates = [
        ("is much clearer", "清楚得多"),
        ("works far better", "效果好得多"),
        ("sounds more natural", "听起来更自然"),
        ("feels more practical", "感觉更实用"),
        ("is slightly easier", "稍微更容易"),
        ("looks more organized", "看起来更有条理"),
    ]
    comparisons = [
        ("than the previous version", "比上一版"),
        ("than the old worksheet", "比旧练习纸"),
        ("than the first draft", "比第一稿"),
        ("than the earlier plan", "比更早的计划"),
        ("than the long paragraph", "比那段长文"),
        ("than the rough answer", "比初步答案"),
    ]
    adverbials = [
        ("for beginners", "对初学者来说"),
        ("in daily review", "在日常复习中"),
        ("during the mock test", "在模拟测试里"),
        ("for a busy learner", "对忙碌的学习者来说"),
        ("in speaking practice", "在口语练习中"),
        ("under exam pressure", "在考试压力下"),
    ]
    summary = "比较结构通常由比较级和 than 短语组成，用于说明两个对象在同一维度上的差异。"
    tags = ["比较级", "than 结构", "程度表达"]
    result = []
    for index in range(COUNT_PER_POINT):
        subject = _pick(subjects, index, 1)
        predicate = _pick(predicates, index, 2)
        comparison = _pick(comparisons, index, 3)
        adverbial = _pick(adverbials, index, 5)
        segments = [
            _segment(subject[0], subject[1], "subject", label="主语", explanation=f"{subject[0]} 是被拿来比较的对象。"),
            _segment(predicate[0], predicate[1], "complement", label="比较级结构", explanation=f"{predicate[0]} 说明主语在某一方面更强或更明显。"),
            _segment(comparison[0], comparison[1], "comparison", label="比较对象", explanation=f"{comparison[0]} 用 than 引出比较对象。"),
            _segment(adverbial[0], adverbial[1], "adverbial", label="适用场景", explanation=f"{adverbial[0]} 补充比较发生的情境。"),
        ]
        translation_cn = f"{subject[1]}{adverbial[1]}{predicate[1]}，{comparison[1]}。"
        analysis = f"读比较句时，先找到比较级核心 {predicate[0]}，再看 {comparison[0]} 说明它是与谁相比。"
        result.append(
            _build_entry(
                point_meta,
                index + 1,
                segments,
                translation_cn,
                summary,
                analysis,
                tags,
                _pick(DEFAULT_SCENES, index, 1),
            )
        )
    return result


def _generate_conditionals(point_meta):
    clauses = [
        ("If you review the notes tonight", "如果你今晚复习这些笔记"),
        ("If the topic sentence is clear", "如果主题句很清楚"),
        ("If we simplify the long clause", "如果我们把长从句简化"),
        ("If the speaker slows down", "如果说话者放慢速度"),
        ("Unless the team checks the verb form", "除非团队检查动词形式"),
        ("If the summary includes examples", "如果总结里包含例句"),
        ("If the reader follows the chunks", "如果读者按照意群来读"),
        ("Provided that the key idea is marked", "只要关键意思被标出来"),
    ]
    subjects = [
        ("you", "你"),
        ("the class", "全班同学"),
        ("the new learner", "这位新学习者"),
        ("the study group", "学习小组"),
        ("the reader", "读者"),
        ("the speaker", "说话者"),
    ]
    predicates = [
        ("will remember", "会记住"),
        ("will understand", "会理解"),
        ("will notice", "会注意到"),
        ("will organize", "会整理好"),
        ("will solve", "会解决"),
        ("will improve", "会提升"),
    ]
    objects = [
        ("the pattern tomorrow", "这个结构"),
        ("the author's main point", "作者的主旨"),
        ("the hidden connector", "隐藏的连接词"),
        ("the whole paragraph", "整段文字"),
        ("the final answer", "最终答案"),
        ("the speaking task", "这项口语任务"),
    ]
    adverbials = [
        ("more easily", "更轻松地"),
        ("with less confusion", "更少困惑地"),
        ("in the right order", "按正确顺序"),
        ("much faster", "更快地"),
        ("during the test", "在测试时"),
        ("without extra hints", "不借助额外提示地"),
    ]
    summary = "条件句先提出条件，再给出结果。阅读时要分清“条件部分”和“结果部分”。"
    tags = ["条件句", "if 结构", "结果预测"]
    result = []
    for index in range(COUNT_PER_POINT):
        clause = _pick(clauses, index, 1)
        subject = _pick(subjects, index, 2)
        predicate = _pick(predicates, index, 3)
        object_item = _pick(objects, index, 5)
        adverbial = _pick(adverbials, index, 7)
        segments = [
            _segment(clause[0], clause[1], "clause", label="条件从句", explanation=f"{clause[0]} 提供条件或限制。", is_core=False),
            _segment(",", "", "connector", annotate=False, joiner=""),
            _segment(subject[0], subject[1], "subject", label="结果主语", explanation=f"{subject[0]} 是结果部分的主语。"),
            _segment(predicate[0], predicate[1], "predicate", label="结果谓语", explanation=f"{predicate[0]} 说明条件满足后会发生什么。"),
            _segment(object_item[0], object_item[1], "object", label="结果对象", explanation=f"{object_item[0]} 是结果动作作用的对象。"),
            _segment(adverbial[0], adverbial[1], "adverbial", label="结果状语", explanation=f"{adverbial[0]} 补充结果的方式或程度。"),
        ]
        translation_cn = f"{clause[1]}，{subject[1]}{adverbial[1]}{predicate[1]}{object_item[1]}。"
        analysis = f"处理条件句时，先把 {clause[0]} 当作背景，再集中识别主干 {subject[0]} {predicate[0]} {object_item[0]}。"
        result.append(
            _build_entry(
                point_meta,
                index + 1,
                segments,
                translation_cn,
                summary,
                analysis,
                tags,
                _pick(DEFAULT_SCENES, index, 1),
                is_long_sentence=True,
            )
        )
    return result


def _generate_long_sentences(point_meta):
    subjects = [
        ("The students", "这些学生"),
        ("The report", "这份报告"),
        ("The coach", "这位教练"),
        ("The readers", "这些读者"),
        ("The course team", "课程团队"),
        ("The writer", "作者"),
        ("The learners", "这些学习者"),
        ("The article", "这篇文章"),
    ]
    relative_clauses = [
        ("who reviewed the passage several times", "反复复习了这篇文章的"),
        ("that the research group released last week", "研究团队上周发布的"),
        ("who carefully marked every connector", "仔细标记了每个连接词的"),
        ("that many beginners usually skip", "许多初学者通常会跳过的"),
        ("who had already sorted the key examples", "已经整理好关键例句的"),
        ("that contains two nested clauses", "包含两个嵌套从句的"),
    ]
    predicates = [
        ("understood", "理解了"),
        ("shows", "表明"),
        ("noticed", "注意到了"),
        ("explains", "解释了"),
        ("remembered", "记住了"),
        ("reveals", "揭示了"),
    ]
    objects = [
        ("the author's point more quickly", "作者观点得更快"),
        ("that learners remember structures better", "学习者会更牢地记住结构这件事"),
        ("the main clause with less effort", "主句，而且花费更少精力"),
        ("why the final sentence changes the tone", "为什么最后一句会改变语气"),
        ("the hidden logic in the paragraph", "段落里的隐藏逻辑"),
        ("how the argument develops step by step", "论证是如何一步步展开的"),
    ]
    tail_clauses = [
        ("because they had already identified the main clause", "因为他们已经先找到了主句"),
        ("after they grouped the details into smaller chunks", "在他们把细节拆成更小意群之后"),
        ("when the difficult modifiers were moved aside", "当那些难修饰语被暂时移开时"),
        ("since the key verb had been highlighted in advance", "因为关键动词提前被高亮了"),
        ("once the comparison between clauses became clear", "一旦从句之间的关系变清楚"),
        ("because the supporting details were read in the right order", "因为支撑细节是按正确顺序阅读的"),
    ]
    summary = "长难句并不难在单词数量，而难在修饰层级。拆句时先找主干，再回填从句和修饰语。"
    tags = ["长难句", "主干提取", "层级拆解"]
    result = []
    for index in range(COUNT_PER_POINT):
        subject = _pick(subjects, index, 1)
        relative_clause = _pick(relative_clauses, index, 2)
        predicate = _pick(predicates, index, 3)
        object_item = _pick(objects, index, 5)
        tail_clause = _pick(tail_clauses, index, 7)
        segments = [
            _segment(subject[0], subject[1], "subject", label="主干主语", explanation=f"{subject[0]} 是整句主干的主语。"),
            _segment(
                relative_clause[0],
                relative_clause[1],
                "modifier",
                label="前置修饰信息",
                explanation=f"{relative_clause[0]} 是附加在主语后的修饰信息，阅读时可暂时放到一边。",
                is_core=False,
            ),
            _segment(predicate[0], predicate[1], "predicate", label="主干谓语", explanation=f"{predicate[0]} 是整句最重要的谓语。"),
            _segment(object_item[0], object_item[1], "object", label="主干宾语/内容", explanation=f"{object_item[0]} 承接主干谓语，是理解整句意义的关键。"),
            _segment(
                tail_clause[0],
                tail_clause[1],
                "clause",
                label="补充从句",
                explanation=f"{tail_clause[0]} 进一步解释原因、条件或过程，是在抓住主干后再回填的信息。",
                is_core=False,
            ),
        ]
        translation_cn = f"{relative_clause[1]}{subject[1]}{tail_clause[1]}，因此更快{predicate[1]}{object_item[1]}。"
        analysis = (
            f"先把主干抽出来：{subject[0]} {predicate[0]} {object_item[0]}。"
            f"再回头处理 {relative_clause[0]} 和 {tail_clause[0]} 这两层附加信息，长句就会清晰很多。"
        )
        result.append(
            _build_entry(
                point_meta,
                index + 1,
                segments,
                translation_cn,
                summary,
                analysis,
                tags,
                _pick(DEFAULT_SCENES, index, 1),
                is_long_sentence=True,
            )
        )
    return result


def _build_point_meta():
    return [
        {
            "code": "simple_present",
            "title": "一般现在时与主谓宾",
            "category": "时态基础",
            "difficulty": 1,
            "sort_order": 1,
            "description": "通过高频学习场景句子识别主语、谓语、宾语和常见状语，建立基本句子主干意识。",
            "learning_tip": "先看谁在做事，再看做了什么，最后看动作作用到谁或什么上。",
            "practice_prompt": "这句话主要体现了哪种时态？",
            "practice_options": ["一般现在时", "一般过去时", "现在进行时", "现在完成时"],
            "practice_answer": "一般现在时",
            "practice_explanation": "一般现在时常用于表达习惯、常态或客观事实。",
        },
        {
            "code": "simple_past",
            "title": "一般过去时",
            "category": "时态基础",
            "difficulty": 1,
            "sort_order": 2,
            "description": "观察过去时间状语与动词过去式之间的对应关系。",
            "learning_tip": "看到 yesterday、last week、earlier 等提示时，优先确认谓语是否已经变成过去式。",
            "practice_prompt": "句中的谓语为什么要用过去式？",
            "practice_options": ["因为动作发生在过去", "因为动作正在进行", "因为动作会在将来发生", "因为动作表示习惯"],
            "practice_answer": "因为动作发生在过去",
            "practice_explanation": "一般过去时用于表达过去某一时间已经发生并结束的动作。",
        },
        {
            "code": "present_continuous",
            "title": "现在进行时",
            "category": "时态基础",
            "difficulty": 1,
            "sort_order": 3,
            "description": "通过 be + doing 结构识别“正在进行”的动作。",
            "learning_tip": "抓住 be 动词和 -ing 形式是识别现在进行时的最快方法。",
            "practice_prompt": "下面哪个结构最能体现“动作正在发生”？",
            "practice_options": ["be + doing", "did", "has done", "will do"],
            "practice_answer": "be + doing",
            "practice_explanation": "现在进行时由 be 动词和现在分词构成，表示此刻或当前阶段正在进行的动作。",
        },
        {
            "code": "future_expression",
            "title": "将来表达",
            "category": "时态基础",
            "difficulty": 1,
            "sort_order": 4,
            "description": "通过 will / be going to 等结构表达计划、预测和安排。",
            "learning_tip": "先找将来标记，再判断句子是在说计划、承诺还是预测。",
            "practice_prompt": "这句话主要在表达什么？",
            "practice_options": ["将来安排或预测", "过去经历", "正在发生的动作", "已经完成的结果"],
            "practice_answer": "将来安排或预测",
            "practice_explanation": "将来表达常用于说明尚未发生但预计会发生的动作或安排。",
        },
        {
            "code": "present_perfect",
            "title": "现在完成时",
            "category": "时态进阶",
            "difficulty": 2,
            "sort_order": 5,
            "description": "通过 has done 结构理解“过去发生、影响现在”的表达。",
            "learning_tip": "现在完成时重点不只是过去，而是过去的动作对现在仍然有影响。",
            "practice_prompt": "现在完成时最突出的语义特点是什么？",
            "practice_options": ["过去动作对现在有影响", "动作只发生在未来", "动作只是一种习惯", "动作正在发生"],
            "practice_answer": "过去动作对现在有影响",
            "practice_explanation": "现在完成时把过去动作和当前结果连接起来，是考试阅读里非常常见的时态。",
        },
        {
            "code": "passive_voice",
            "title": "被动语态",
            "category": "语态",
            "difficulty": 2,
            "sort_order": 6,
            "description": "通过被动结构识别“动作承受者”为句子重点的表达方式。",
            "learning_tip": "看到 be + 过去分词时，先判断主语是不是动作承受者。",
            "practice_prompt": "被动语态里，句首主语通常是什么？",
            "practice_options": ["动作承受者", "动作发出者", "时间状语", "连接词"],
            "practice_answer": "动作承受者",
            "practice_explanation": "被动语态会把原来的宾语提前到句首，让结果或对象成为焦点。",
        },
        {
            "code": "infinitive",
            "title": "不定式作目的或补足",
            "category": "非谓语",
            "difficulty": 2,
            "sort_order": 7,
            "description": "通过 to do 结构理解目的、计划和补充说明。",
            "learning_tip": "看到 to do 时，先问自己：它是在补充目的，还是补全前面的动作？",
            "practice_prompt": "句中的 to do 结构主要说明了什么？",
            "practice_options": ["目的或补足信息", "过去动作", "被动关系", "比较关系"],
            "practice_answer": "目的或补足信息",
            "practice_explanation": "不定式常放在主句后面，补充说明“为了做什么”或“要去做什么”。",
        },
        {
            "code": "gerund",
            "title": "动名词短语作主语",
            "category": "非谓语",
            "difficulty": 2,
            "sort_order": 8,
            "description": "通过动名词短语作主语的句子，理解非谓语也能承担名词功能。",
            "learning_tip": "句首出现 doing 短语时，不要急着把它当谓语，先看它是否整体作主语。",
            "practice_prompt": "这类句子中，doing 短语在主句里通常充当什么成分？",
            "practice_options": ["主语", "连接词", "状语", "宾语补足语"],
            "practice_answer": "主语",
            "practice_explanation": "动名词短语具有名词性质，因此可以整体放在句首充当主语。",
        },
        {
            "code": "relative_clause",
            "title": "定语从句",
            "category": "从句",
            "difficulty": 2,
            "sort_order": 9,
            "description": "通过 who / that 引导的从句学习如何给名词添加限制信息。",
            "learning_tip": "先行词和定语从句要一起看，但做长句拆解时先抓主句，再补回从句。",
            "practice_prompt": "定语从句最核心的作用是什么？",
            "practice_options": ["修饰前面的名词", "表示过去时间", "替代主句谓语", "引出比较对象"],
            "practice_answer": "修饰前面的名词",
            "practice_explanation": "定语从句贴在名词后面，用来说明“哪一个”“什么样的”人或物。",
        },
        {
            "code": "adverbial_clause",
            "title": "状语从句",
            "category": "从句",
            "difficulty": 2,
            "sort_order": 10,
            "description": "通过时间、原因、条件等状语从句学习主从句层级。",
            "learning_tip": "主句是核心，状语从句是背景。阅读时先区分两层，再看逻辑关系。",
            "practice_prompt": "状语从句在句中主要承担什么功能？",
            "practice_options": ["提供背景信息", "充当宾语", "充当主语", "引出比较对象"],
            "practice_answer": "提供背景信息",
            "practice_explanation": "状语从句负责交代时间、原因、条件、让步等背景，主句负责承载主要判断。",
        },
        {
            "code": "noun_clause",
            "title": "名词性从句",
            "category": "从句",
            "difficulty": 3,
            "sort_order": 11,
            "description": "重点展示 that 引导的宾语从句，帮助学习者理解“整句作宾语”的结构。",
            "learning_tip": "看到 know / think / show / explain 这类动词时，后面很容易跟一个完整从句作宾语。",
            "practice_prompt": "名词性从句在这里主要充当什么成分？",
            "practice_options": ["宾语", "状语", "定语", "比较成分"],
            "practice_answer": "宾语",
            "practice_explanation": "名词性从句具有名词功能，因此可以整体充当主语、宾语或表语。",
        },
        {
            "code": "comparative",
            "title": "比较结构",
            "category": "形容词与副词",
            "difficulty": 2,
            "sort_order": 12,
            "description": "通过比较级和 than 短语学习程度差异表达。",
            "learning_tip": "先找到比较级核心，再看 than 后面是谁，最后再看适用场景。",
            "practice_prompt": "than 后面的部分通常表示什么？",
            "practice_options": ["比较对象", "动作发出者", "主句谓语", "时间状语"],
            "practice_answer": "比较对象",
            "practice_explanation": "比较级结构通过 than 引出比较对象，让差异关系更明确。",
        },
        {
            "code": "conditionals",
            "title": "条件句",
            "category": "从句",
            "difficulty": 3,
            "sort_order": 13,
            "description": "通过 if / unless / provided that 等结构理解条件与结果的对应。",
            "learning_tip": "看到条件连接词时，优先把条件块圈出来，再回头找结果主干。",
            "practice_prompt": "条件句阅读时最先要分清哪两部分？",
            "practice_options": ["条件部分和结果部分", "主语和宾语", "单词和音标", "定语和表语"],
            "practice_answer": "条件部分和结果部分",
            "practice_explanation": "条件句的关键就是先找条件，再找结果，两层关系清楚后理解就会快很多。",
        },
        {
            "code": "long_sentences",
            "title": "长难句拆解",
            "category": "阅读强化",
            "difficulty": 3,
            "sort_order": 14,
            "description": "通过层级较深的句子练习主干提取、从句回填和修饰语剥离。",
            "learning_tip": "所有长难句都能先还原成一个短主干，再慢慢把修饰层一层层加回去。",
            "practice_prompt": "拆长难句时，第一步通常应该做什么？",
            "practice_options": ["先找主干", "先背每个单词", "先忽略谓语", "先翻译所有从句"],
            "practice_answer": "先找主干",
            "practice_explanation": "长难句的核心是主干。先抓主干，再看修饰层级，效率会明显更高。",
        },
    ]


def build_grammar_seed_data():
    metas = _build_point_meta()

    basic_subjects = [
        ("The new teacher", "新来的老师"),
        ("The study group", "学习小组"),
        ("The language coach", "语言教练"),
        ("The careful reader", "认真阅读的人"),
        ("The course tutor", "课程导师"),
        ("The online class", "线上课堂"),
        ("The team leader", "小组长"),
        ("The exam candidate", "备考生"),
        ("The office trainer", "职场培训师"),
        ("The class monitor", "班长"),
        ("The beginner", "初学者"),
        ("The project assistant", "项目助理"),
    ]
    simple_present = _generate_basic_svo(
        metas[0],
        basic_subjects,
        [
            ("explains", "讲解"),
            ("reviews", "复习"),
            ("records", "记录"),
            ("checks", "检查"),
            ("organizes", "整理"),
            ("compares", "比较"),
            ("highlights", "标出"),
            ("summarizes", "总结"),
        ],
        [
            ("the grammar rule", "这个语法规则"),
            ("the key sentence pattern", "这个关键句型"),
            ("the main clause", "主句"),
            ("the difficult paragraph", "较难的段落"),
            ("the review task", "复习任务"),
            ("the speaking notes", "口语笔记"),
            ("the sample answer", "范例答案"),
            ("the class outline", "课堂提纲"),
        ],
        [
            ("in class", "在课堂上"),
            ("every morning", "每天早上"),
            ("with great patience", "耐心地"),
            ("during revision", "在复习时"),
            ("for the whole team", "面向整个团队"),
            ("after each lesson", "每节课后"),
        ],
        "一般现在时常用于描述习惯性动作、固定流程或普遍事实。",
        ["一般现在时", "主谓宾", "基础语法"],
    )
    simple_past = _generate_basic_svo(
        metas[1],
        basic_subjects,
        [
            ("explained", "讲解了"),
            ("reviewed", "复习了"),
            ("recorded", "记录了"),
            ("checked", "检查了"),
            ("organized", "整理了"),
            ("compared", "比较了"),
            ("highlighted", "标出了"),
            ("summarized", "总结了"),
        ],
        [
            ("the grammar rule", "这个语法规则"),
            ("the key sentence pattern", "这个关键句型"),
            ("the main clause", "主句"),
            ("the difficult paragraph", "较难的段落"),
            ("the review task", "复习任务"),
            ("the speaking notes", "口语笔记"),
            ("the sample answer", "范例答案"),
            ("the class outline", "课堂提纲"),
        ],
        [
            ("yesterday morning", "昨天早上"),
            ("last night", "昨晚"),
            ("during the workshop", "在工作坊期间"),
            ("before the test", "在测试前"),
            ("after class", "下课后"),
            ("earlier this week", "本周早些时候"),
        ],
        "一般过去时用于描述已经发生并结束的动作，通常伴随明确的过去时间线索。",
        ["一般过去时", "过去动作", "时间线索"],
    )
    present_continuous = _generate_basic_svo(
        metas[2],
        basic_subjects,
        [
            ("is reviewing", "正在复习"),
            ("is checking", "正在检查"),
            ("is rewriting", "正在改写"),
            ("is marking", "正在标记"),
            ("is reading", "正在阅读"),
            ("is organizing", "正在整理"),
            ("is discussing", "正在讨论"),
            ("is practicing", "正在练习"),
        ],
        [
            ("the grammar rule", "这个语法规则"),
            ("the key sentence pattern", "这个关键句型"),
            ("the main clause", "主句"),
            ("the difficult paragraph", "较难的段落"),
            ("the review task", "复习任务"),
            ("the speaking notes", "口语笔记"),
            ("the sample answer", "范例答案"),
            ("the class outline", "课堂提纲"),
        ],
        [
            ("right now", "此刻"),
            ("at the moment", "此时此刻"),
            ("in the study room", "在自习室里"),
            ("during the live lesson", "在直播课上"),
            ("with the whole class", "和全班一起"),
            ("before the deadline", "在截止前"),
        ],
        "现在进行时强调动作正在进行，be + doing 是最显眼的形式标记。",
        ["现在进行时", "be doing", "进行中的动作"],
    )
    future_expression = _generate_basic_svo(
        metas[3],
        basic_subjects,
        [
            ("will review", "会复习"),
            ("will explain", "会讲解"),
            ("will organize", "会整理"),
            ("will compare", "会比较"),
            ("will finish", "会完成"),
            ("is going to check", "准备检查"),
            ("is going to rewrite", "准备改写"),
            ("will highlight", "会标出"),
        ],
        [
            ("the grammar rule", "这个语法规则"),
            ("the key sentence pattern", "这个关键句型"),
            ("the main clause", "主句"),
            ("the difficult paragraph", "较难的段落"),
            ("the review task", "复习任务"),
            ("the speaking notes", "口语笔记"),
            ("the sample answer", "范例答案"),
            ("the class outline", "课堂提纲"),
        ],
        [
            ("tomorrow morning", "明天早上"),
            ("next week", "下周"),
            ("after lunch", "午饭后"),
            ("before the final test", "在期末测试前"),
            ("during the next lesson", "在下一节课中"),
            ("very soon", "很快"),
        ],
        "将来表达常用于说明计划、安排或预测，常见标记包括 will 和 be going to。",
        ["将来表达", "计划安排", "预测"],
    )
    present_perfect = _generate_basic_svo(
        metas[4],
        basic_subjects,
        [
            ("has completed", "已经完成"),
            ("has reviewed", "已经复习"),
            ("has summarized", "已经总结"),
            ("has improved", "已经提升"),
            ("has remembered", "已经记住"),
            ("has noticed", "已经注意到"),
            ("has organized", "已经整理好"),
            ("has compared", "已经比较过"),
        ],
        [
            ("the grammar rule", "这个语法规则"),
            ("the key sentence pattern", "这个关键句型"),
            ("the main clause", "主句"),
            ("the difficult paragraph", "较难的段落"),
            ("the review task", "复习任务"),
            ("the speaking notes", "口语笔记"),
            ("the sample answer", "范例答案"),
            ("the class outline", "课堂提纲"),
        ],
        [
            ("so far", "到目前为止"),
            ("over the past week", "在过去一周里"),
            ("through repeated practice", "通过反复练习"),
            ("by this stage", "到这个阶段"),
            ("for today's lesson", "针对今天这节课"),
            ("in recent study sessions", "在最近的学习过程中"),
        ],
        "现在完成时把过去的动作和当前结果联系起来，强调“已经产生的影响”。",
        ["现在完成时", "has done", "结果影响"],
    )

    generators = {
        "passive_voice": _generate_passive,
        "infinitive": _generate_infinitive,
        "gerund": _generate_gerund,
        "relative_clause": _generate_relative_clause,
        "adverbial_clause": _generate_adverbial_clause,
        "noun_clause": _generate_noun_clause,
        "comparative": _generate_comparative,
        "conditionals": _generate_conditionals,
        "long_sentences": _generate_long_sentences,
    }

    point_payloads = [
        {**metas[0], "sentences": simple_present},
        {**metas[1], "sentences": simple_past},
        {**metas[2], "sentences": present_continuous},
        {**metas[3], "sentences": future_expression},
        {**metas[4], "sentences": present_perfect},
    ]

    for meta in metas[5:]:
        point_payloads.append({**meta, "sentences": generators[meta["code"]](meta)})

    return point_payloads
