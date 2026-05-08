import os
import random
import sys
from datetime import timedelta
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.books.models import Book, Word, WordExample  # noqa: E402
from apps.exams.models import TestAnswer, TestQuestion, TestSession  # noqa: E402
from apps.learn.models import LearningRecord, WordProgress  # noqa: E402
from apps.plans.models import DailyTask, UserPlan  # noqa: E402
from apps.review.models import WrongWord  # noqa: E402
from apps.stats.models import CheckinRecord, StudyDailyStat  # noqa: E402
from apps.users.models import UserSetting, WxUser  # noqa: E402


BOOK_DATA = [
    {
        "name": "四级高频词汇测试集",
        "category": "CET-4",
        "level": "基础",
        "description": "适用于大学英语四级常见高频词的测试与练习。",
        "cover_color": "#4F7CFF",
        "words": [
            {"word": "resilient", "phonetic": "/rɪˈzɪliənt/", "pos": "adj.", "meaning": "有韧性的；恢复快的", "example": "A resilient student can recover after setbacks.", "translation": "有韧性的学生能在受挫后快速恢复。", "difficulty": 2},
            {"word": "concise", "phonetic": "/kənˈsaɪs/", "pos": "adj.", "meaning": "简洁的；简明的", "example": "Please write a concise summary.", "translation": "请写一段简洁的总结。", "difficulty": 2},
            {"word": "subtle", "phonetic": "/ˈsʌtl/", "pos": "adj.", "meaning": "微妙的；不明显的", "example": "There is a subtle difference between the two words.", "translation": "这两个词之间有细微差别。", "difficulty": 3},
            {"word": "abundant", "phonetic": "/əˈbʌndənt/", "pos": "adj.", "meaning": "大量的；充足的", "example": "The region has abundant natural resources.", "translation": "这个地区拥有丰富的自然资源。", "difficulty": 2},
            {"word": "scarce", "phonetic": "/skeəs/", "pos": "adj.", "meaning": "稀缺的；不足的", "example": "Fresh water is scarce in some areas.", "translation": "在一些地区淡水很稀缺。", "difficulty": 2},
            {"word": "coherent", "phonetic": "/koʊˈhɪrənt/", "pos": "adj.", "meaning": "连贯的；有条理的", "example": "Her speech was clear and coherent.", "translation": "她的演讲清晰而连贯。", "difficulty": 3},
            {"word": "cultivate", "phonetic": "/ˈkʌltɪveɪt/", "pos": "v.", "meaning": "培养；养成", "example": "Reading helps cultivate good habits.", "translation": "阅读有助于培养良好习惯。", "difficulty": 2},
            {"word": "infer", "phonetic": "/ɪnˈfɜːr/", "pos": "v.", "meaning": "推断；推论", "example": "We can infer the answer from the context.", "translation": "我们可以从上下文推断答案。", "difficulty": 3},
            {"word": "allocate", "phonetic": "/ˈæləkeɪt/", "pos": "v.", "meaning": "分配；拨给", "example": "The manager will allocate tasks to each member.", "translation": "经理会给每位成员分配任务。", "difficulty": 2},
            {"word": "retain", "phonetic": "/rɪˈteɪn/", "pos": "v.", "meaning": "保留；保持拥有", "example": "It is important to retain key information.", "translation": "保留关键信息很重要。", "difficulty": 2},
            {"word": "alter", "phonetic": "/ˈɔːltər/", "pos": "v.", "meaning": "改变；更改", "example": "We need to alter the plan slightly.", "translation": "我们需要稍微调整一下计划。", "difficulty": 2},
            {"word": "compile", "phonetic": "/kəmˈpaɪl/", "pos": "v.", "meaning": "整理；汇编", "example": "She compiled a list of useful expressions.", "translation": "她整理了一份常用表达清单。", "difficulty": 2},
        ],
    },
    {
        "name": "考研核心词汇测试集",
        "category": "考研",
        "level": "进阶",
        "description": "适用于考研英语场景的核心词汇测试数据。",
        "cover_color": "#17C7A3",
        "words": [
            {"word": "inevitable", "phonetic": "/ɪnˈevɪtəbl/", "pos": "adj.", "meaning": "不可避免的", "example": "Change is inevitable in modern society.", "translation": "在现代社会中变化不可避免。", "difficulty": 3},
            {"word": "controversial", "phonetic": "/ˌkɒntrəˈvɜːʃl/", "pos": "adj.", "meaning": "有争议的", "example": "The decision remains controversial.", "translation": "这项决定仍然存在争议。", "difficulty": 3},
            {"word": "feasible", "phonetic": "/ˈfiːzəbl/", "pos": "adj.", "meaning": "可行的；行得通的", "example": "We need a feasible solution.", "translation": "我们需要一个可行的解决方案。", "difficulty": 3},
            {"word": "fragile", "phonetic": "/ˈfrædʒaɪl/", "pos": "adj.", "meaning": "脆弱的；易损的", "example": "The economy is still fragile.", "translation": "经济仍然相对脆弱。", "difficulty": 3},
            {"word": "robust", "phonetic": "/rəʊˈbʌst/", "pos": "adj.", "meaning": "强健的；稳固的", "example": "The system is robust enough for heavy use.", "translation": "这个系统足够稳健，能承受高负载。", "difficulty": 3},
            {"word": "vague", "phonetic": "/veɪɡ/", "pos": "adj.", "meaning": "模糊的；不明确的", "example": "His answer was too vague to be useful.", "translation": "他的回答过于模糊，没什么帮助。", "difficulty": 2},
            {"word": "alleviate", "phonetic": "/əˈliːvieɪt/", "pos": "v.", "meaning": "缓解；减轻", "example": "The new policy may alleviate the burden.", "translation": "新政策可能会减轻负担。", "difficulty": 4},
            {"word": "constrain", "phonetic": "/kənˈstreɪn/", "pos": "v.", "meaning": "限制；约束", "example": "Lack of funds may constrain growth.", "translation": "资金不足可能限制增长。", "difficulty": 3},
            {"word": "discard", "phonetic": "/dɪˈskɑːd/", "pos": "v.", "meaning": "丢弃；抛弃", "example": "You should discard outdated ideas.", "translation": "你应该摒弃过时的想法。", "difficulty": 2},
            {"word": "clarify", "phonetic": "/ˈklærəfaɪ/", "pos": "v.", "meaning": "澄清；阐明", "example": "Could you clarify your point?", "translation": "你能澄清一下你的观点吗？", "difficulty": 2},
            {"word": "undertake", "phonetic": "/ˌʌndəˈteɪk/", "pos": "v.", "meaning": "承担；着手进行", "example": "They will undertake a major project.", "translation": "他们将承担一个重大项目。", "difficulty": 3},
            {"word": "sustain", "phonetic": "/səˈsteɪn/", "pos": "v.", "meaning": "维持；支撑", "example": "It is hard to sustain rapid growth.", "translation": "维持快速增长并不容易。", "difficulty": 3},
        ],
    },
    {
        "name": "雅思场景词汇测试集",
        "category": "IELTS",
        "level": "强化",
        "description": "适用于雅思阅读和写作场景的词汇测试数据。",
        "cover_color": "#FF7A59",
        "words": [
            {"word": "authentic", "phonetic": "/ɔːˈθentɪk/", "pos": "adj.", "meaning": "真实的；可信的", "example": "The museum displays authentic artifacts.", "translation": "博物馆展出了真实的文物。", "difficulty": 3},
            {"word": "adjacent", "phonetic": "/əˈdʒeɪsnt/", "pos": "adj.", "meaning": "邻近的；毗连的", "example": "Our office is adjacent to the library.", "translation": "我们的办公室紧邻图书馆。", "difficulty": 2},
            {"word": "temporary", "phonetic": "/ˈtemprəri/", "pos": "adj.", "meaning": "暂时的；临时的", "example": "The arrangement is only temporary.", "translation": "这项安排只是暂时的。", "difficulty": 2},
            {"word": "permanent", "phonetic": "/ˈpɜːmənənt/", "pos": "adj.", "meaning": "永久的；长期的", "example": "She is looking for a permanent job.", "translation": "她在寻找一份长期工作。", "difficulty": 2},
            {"word": "explicit", "phonetic": "/ɪkˈsplɪsɪt/", "pos": "adj.", "meaning": "明确的；清楚表达的", "example": "The instructions were explicit and easy to follow.", "translation": "说明很明确，容易照做。", "difficulty": 3},
            {"word": "implicit", "phonetic": "/ɪmˈplɪsɪt/", "pos": "adj.", "meaning": "含蓄的；未明说的", "example": "There was an implicit warning in his words.", "translation": "他的话里有一种隐含的警告。", "difficulty": 3},
            {"word": "simulate", "phonetic": "/ˈsɪmjuleɪt/", "pos": "v.", "meaning": "模拟；仿真", "example": "The software can simulate real traffic conditions.", "translation": "该软件可以模拟真实交通状况。", "difficulty": 3},
            {"word": "emphasize", "phonetic": "/ˈemfəsaɪz/", "pos": "v.", "meaning": "强调；着重指出", "example": "Teachers often emphasize critical thinking.", "translation": "老师常常强调批判性思维。", "difficulty": 2},
            {"word": "eliminate", "phonetic": "/ɪˈlɪmɪneɪt/", "pos": "v.", "meaning": "消除；排除", "example": "We need to eliminate unnecessary costs.", "translation": "我们需要消除不必要的成本。", "difficulty": 3},
            {"word": "accelerate", "phonetic": "/əkˈseləreɪt/", "pos": "v.", "meaning": "加速；促进", "example": "Technology can accelerate social change.", "translation": "技术可以加速社会变革。", "difficulty": 3},
            {"word": "comprehend", "phonetic": "/ˌkɒmprɪˈhend/", "pos": "v.", "meaning": "理解；领会", "example": "Young children may not comprehend the concept.", "translation": "年幼的孩子可能无法理解这个概念。", "difficulty": 3},
            {"word": "hamper", "phonetic": "/ˈhæmpə(r)/", "pos": "v.", "meaning": "妨碍；阻碍", "example": "Bad weather may hamper the rescue effort.", "translation": "恶劣天气可能妨碍救援工作。", "difficulty": 3},
        ],
    },
]


SEED_USERS = [
    {"openid": "seed_alpha", "nickname": "测试用户A", "avatar_url": "", "gender": "unknown"},
    {"openid": "seed_beta", "nickname": "测试用户B", "avatar_url": "", "gender": "unknown"},
]


def pick_distractors(word, count=3):
    used_ids = {word.id}
    used_meanings = {word.meaning_cn}
    distractors = []
    groups = [
        Word.objects.filter(book=word.book, part_of_speech=word.part_of_speech).exclude(id=word.id),
        Word.objects.filter(part_of_speech=word.part_of_speech).exclude(id=word.id),
        Word.objects.filter(book=word.book).exclude(id=word.id),
        Word.objects.exclude(id=word.id),
    ]
    for queryset in groups:
        candidates = list(queryset.order_by("id"))
        random.shuffle(candidates)
        for item in candidates:
            if item.id in used_ids or item.meaning_cn in used_meanings:
                continue
            distractors.append(item)
            used_ids.add(item.id)
            used_meanings.add(item.meaning_cn)
            if len(distractors) >= count:
                return distractors
    return distractors


def build_option_map(word):
    distractors = pick_distractors(word, 3)
    meanings = [item.meaning_cn for item in distractors] + [word.meaning_cn]
    while len(meanings) < 4:
        filler = f"备用干扰项{len(meanings)}"
        if filler not in meanings:
            meanings.append(filler)
    random.shuffle(meanings)
    option_map = {chr(65 + idx): value for idx, value in enumerate(meanings)}
    correct = next(key for key, value in option_map.items() if value == word.meaning_cn)
    return option_map, correct


def create_or_update_books():
    books = []
    for book_payload in BOOK_DATA:
        book, _ = Book.objects.update_or_create(
            name=book_payload["name"],
            defaults={
                "category": book_payload["category"],
                "level": book_payload["level"],
                "description": book_payload["description"],
                "status": "active",
                "cover_color": book_payload["cover_color"],
            },
        )
        for index, word_payload in enumerate(book_payload["words"], start=1):
            word, _ = Word.objects.update_or_create(
                book=book,
                word=word_payload["word"],
                defaults={
                    "phonetic": word_payload["phonetic"],
                    "part_of_speech": word_payload["pos"],
                    "meaning_cn": word_payload["meaning"],
                    "example_sentence": word_payload["example"],
                    "example_translation": word_payload["translation"],
                    "difficulty": word_payload["difficulty"],
                    "synonyms": "",
                    "order_in_book": index,
                },
            )
            WordExample.objects.update_or_create(
                word=word,
                example_sentence=word_payload["example"],
                defaults={
                    "example_translation": word_payload["translation"],
                    "sort_order": 1,
                },
            )
        book.word_count = book.words.count()
        book.save(update_fields=["word_count", "updated_at"])
        books.append(book)
    return books


def create_or_update_users():
    users = []
    for payload in SEED_USERS:
        user, _ = WxUser.objects.update_or_create(
            openid=payload["openid"],
            defaults={
                "nickname": payload["nickname"],
                "avatar_url": payload["avatar_url"],
                "gender": payload["gender"],
                "status": "active",
                "last_login_at": timezone.now(),
            },
        )
        UserSetting.objects.get_or_create(user=user)
        users.append(user)
    return users


def reset_user_related_data(user):
    TestAnswer.objects.filter(user=user).delete()
    sessions = list(TestSession.objects.filter(user=user))
    if sessions:
        TestQuestion.objects.filter(test_session__in=sessions).delete()
        TestSession.objects.filter(id__in=[item.id for item in sessions]).delete()
    LearningRecord.objects.filter(user=user).delete()
    WordProgress.objects.filter(user=user).delete()
    WrongWord.objects.filter(user=user).delete()
    DailyTask.objects.filter(user=user).delete()
    UserPlan.objects.filter(user=user).delete()
    CheckinRecord.objects.filter(user=user).delete()
    StudyDailyStat.objects.filter(user=user).delete()


def seed_learning_data(user, book, learned_words):
    plan = UserPlan.objects.create(
        user=user,
        book=book,
        daily_target=20,
        start_date=timezone.localdate() - timedelta(days=7),
        status="active",
        finished_word_count=len(learned_words),
    )
    task = DailyTask.objects.create(
        user=user,
        plan=plan,
        task_date=timezone.localdate(),
        new_word_target=20,
        review_word_target=10,
        learned_count=min(len(learned_words), 20),
        reviewed_count=6,
        test_count=2,
        is_started=True,
        is_finished=False,
    )

    now = timezone.now()
    for idx, word in enumerate(learned_words, start=1):
        occurred_at = now - timedelta(days=max(1, idx % 5), minutes=idx * 3)
        is_wrong = idx % 4 == 0
        LearningRecord.objects.create(
            user=user,
            word=word,
            plan=plan,
            source="learn",
            action_type="unknown" if is_wrong else "known",
            result="wrong" if is_wrong else "correct",
            duration=15 + idx,
            occurred_at=occurred_at,
        )
        progress = WordProgress.objects.create(
            user=user,
            book=book,
            word=word,
            mastery_level=1 if is_wrong else 3,
            learn_count=1,
            review_count=1 if idx % 2 == 0 else 0,
            correct_count=0 if is_wrong else 1,
            wrong_count=1 if is_wrong else 0,
            last_learned_at=occurred_at,
            last_reviewed_at=occurred_at + timedelta(days=1) if idx % 2 == 0 else None,
            review_due_at=now - timedelta(hours=2) if is_wrong else now + timedelta(days=2),
            is_favorite=(idx % 5 == 0),
            is_mastered=(not is_wrong and idx % 3 == 0),
        )
        if is_wrong:
            WrongWord.objects.create(
                user=user,
                word=word,
                wrong_count=1,
                source="learn",
                last_wrong_at=occurred_at,
                is_active=True,
            )

    CheckinRecord.objects.create(
        user=user,
        checkin_date=timezone.localdate(),
        finished_new_count=min(len(learned_words), 20),
        finished_review_count=6,
        total_minutes=28,
        status="success",
    )
    StudyDailyStat.objects.create(
        user=user,
        stat_date=timezone.localdate(),
        learned_count=min(len(learned_words), 20),
        review_count=6,
        test_count=2,
        correct_count=max(len(learned_words) - 2, 0),
        total_minutes=28,
    )
    return plan, task


def seed_test_sessions(user, book, words, session_total=3, questions_per_session=6):
    created_sessions = []
    for session_index in range(session_total):
        selected_words = random.sample(words, min(questions_per_session, len(words)))
        started_at = timezone.now() - timedelta(days=session_total - session_index, hours=1)
        session = TestSession.objects.create(
            user=user,
            book=book,
            title=f"{book.name}-模拟测试-{session_index + 1}",
            question_count=len(selected_words),
            status="completed",
            started_at=started_at,
            completed_at=started_at + timedelta(minutes=12),
        )

        correct_count = 0
        for word in selected_words:
            option_map, correct_option = build_option_map(word)
            question = TestQuestion.objects.create(
                test_session=session,
                word=word,
                question_type="word_to_meaning",
                stem=word.word,
                option_a=option_map["A"],
                option_b=option_map["B"],
                option_c=option_map["C"],
                option_d=option_map["D"],
                correct_option=correct_option,
                explanation=word.meaning_cn,
            )

            choose_correct = random.random() > 0.35
            if choose_correct:
                selected_option = correct_option
                is_correct = True
                correct_count += 1
            else:
                wrong_keys = [key for key in option_map.keys() if key != correct_option]
                selected_option = random.choice(wrong_keys)
                is_correct = False
                wrong_word, created = WrongWord.objects.get_or_create(
                    user=user,
                    word=word,
                    defaults={
                        "wrong_count": 1,
                        "source": "test",
                        "last_wrong_at": started_at,
                        "is_active": True,
                    },
                )
                if not created:
                    wrong_word.wrong_count += 1
                    wrong_word.last_wrong_at = started_at
                    wrong_word.is_active = True
                    wrong_word.save()

            TestAnswer.objects.create(
                test_session=session,
                question=question,
                user=user,
                selected_option=selected_option,
                is_correct=is_correct,
                answered_at=started_at + timedelta(minutes=2),
            )

        session.correct_count = correct_count
        session.score = round((correct_count / session.question_count) * 100, 2) if session.question_count else 0
        session.save(update_fields=["correct_count", "score", "updated_at"])
        created_sessions.append(session)
    return created_sessions


@transaction.atomic
def main():
    random.seed(20260409)
    books = create_or_update_books()
    users = create_or_update_users()

    for user_index, user in enumerate(users):
        reset_user_related_data(user)
        book = books[user_index % len(books)]
        words = list(book.words.order_by("order_in_book", "id"))
        seed_learning_data(user, book, words[:10])
        seed_test_sessions(user, book, words, session_total=3, questions_per_session=6)

    print(
        {
            "books": Book.objects.count(),
            "words": Word.objects.count(),
            "word_examples": WordExample.objects.count(),
            "seed_users": WxUser.objects.filter(openid__startswith="seed_").count(),
            "test_sessions": TestSession.objects.count(),
            "test_questions": TestQuestion.objects.count(),
            "test_answers": TestAnswer.objects.count(),
            "wrong_words": WrongWord.objects.count(),
        }
    )


if __name__ == "__main__":
    main()
