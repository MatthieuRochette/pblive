#    PBLive
#    Copyright © 2017  RunasSudo (Yingtong Li)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import threading
import time

server_ip = None

sessions = {}
users = {}
admins = {}


class Session:
    def __init__(
        self, name=None, title=None, questions=None, colours=None, question_num=0
    ):
        if questions is None:
            questions = []
        if colours is None:
            colours = [
                (1,  "#00BAFA"),
                (2,  "#980AFA"),
                (3,  "#6DFA96"),
                (4,  "#FA8000"),
                (5,  "#DAFA02"),
                (6,  "#0EFA00"),
                (7,  "#0AFAF4"),
                (8,  "#FAE56D"),
                (9,  "#FA0090"),
                (10, "#FA5B02"),
                (11, "#FAC113"),
                (12, "#75FA7B"),
                (13, "#FA6311"),
                (14, "#6681FA"),
                (15, "#FA4D97"),
                (16, "#ff0000"),
                (17, "#f9c0e0"),
                (18, "#3609c4"),
                (19, "#c12f2c"),
                (20, "#e28d38"),
                (21, "#00ff00"),
                (22, "#00b300"),
                (23, "#1ac0c6"),
                (24, "#fdfa66"),
                (25, "#fb7756"),
                (26, "#0000ff"),
                (27, "#bfcfff"),
                (28, "#809fff"),
                (29, "#008f7a"),
                (30, "#fbeaff"),
                (31, "#00c9a7"),
                (32, "#b0a8b9"),
                (33, "#4e8397"),
                (34, "#4ffbdf"),
                (35, "#926d00"),
            ]

        self.name = name
        self.title = title
        self.questions = questions
        self.colours = colours
        self.question_num = question_num

    @classmethod
    def from_dict(cls, obj, name):
        return cls(
            name=name,
            title=obj["title"],
            questions=[Question.from_dict(x) for x in obj["questions"]],
        )


class Question:
    def __init__(self, *args, **kwargs):
        self.type = None
        self.prompt = kwargs.get("prompt", None)
        self.image = kwargs.get("image", None)
        self.answers = kwargs.get("answers", [])

        self.revealed = False

    @staticmethod
    def from_dict(obj):
        question_types = {
            "landing": LandingQuestion,
            "mcq": MCQQuestion,
            "draw": DrawQuestion,
            "random": RandomQuestion,
            "type": TypeQuestion,
            "speed": SpeedQuestion,
            "speed_review": SpeedReviewQuestion,
        }
        question = question_types[obj["type"]]()
        question.load_dict(obj)
        return question

    def load_dict(self, obj):
        self.type = obj["type"]

        self.prompt = obj.get("prompt", self.prompt)
        self.image = obj.get("image", self.image)
        self.answers = obj.get("answers", self.answers)


class LandingQuestion(Question):
    # Not actually a question
    template = "session_landing.html"
    template_admin = "session_landing_admin.html"


class MCQQuestion(Question):
    template = "question_mcq.html"
    template_admin = "question_mcq_admin.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.maximum = kwargs.get("maximum", 1)

    def load_dict(self, obj):
        super().load_dict(obj)

        self.maximum = obj.get("maximum", self.maximum)


class DrawQuestion(Question):
    template = "question_draw.html"
    template_admin = "question_draw_admin.html"


class RandomQuestion(Question):
    template = "question_random.html"
    template_admin = "question_random_admin.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.answerer = kwargs.get("answerer", None)


class TypeQuestion(Question):
    template = "question_type.html"
    template_admin = "question_type_admin.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.answer_form = kwargs.get("answer_form", "$1")
        self.answer_type = kwargs.get("answer_type", None)
        self.answer_range = kwargs.get("answer_range", None)

    def load_dict(self, obj):
        super().load_dict(obj)

        self.answer_form = obj.get("answer_form", self.answer_form)
        self.answer_type = obj.get("answer_type", self.answer_type)
        self.answer_range = obj.get("answer_range", self.answer_range)


class SpeedQuestion(MCQQuestion):
    template = "question_speed.html"
    template_admin = "question_speed_admin.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.timer_thread = None


class SpeedQuestionTimerThread(threading.Thread):
    def __init__(self, do_goto_question, session, next_question):
        super().__init__()

        self.do_goto_question = do_goto_question
        self.session = session
        self.next_question = next_question

        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        time.sleep(4)
        if self._stop.isSet():
            return
        self.do_goto_question(self.session, self.next_question)


class SpeedReviewQuestion(Question):
    template = "question_speed_review.html"
    template_admin = "question_speed_review_admin.html"


class User:
    def __init__(self, sid=None, session=None, answers=None, colour=None):
        if answers is None:
            answers = {}

        self.sid = sid
        self.session = session
        self.answers = answers
        self.colour = colour


class Admin(User):
    pass


def responses_for_question(session, question_num):
    return len(
        [
            user
            for _, user in users.items()
            if user.session == session and question_num in user.answers
        ]
    )


def unique_answers_for_question(session, question_num):
    answers = {}
    for _, user in users.items():
        if (
            user.session == session
            and question_num in user.answers
            and user.answers[question_num] != ""
            and user.answers[question_num] is not None
        ):
            if user.answers[question_num] in answers:
                answers[user.answers[question_num]].append(user)
            else:
                answers[user.answers[question_num]] = [user]
    return answers


class DummyLock:
    def acquire(self):
        pass

    def release(self):
        pass


users_lock = DummyLock()


def iterate_users():
    users_lock.acquire()
    yield from list(users.items())
    users_lock.release()


admins_lock = DummyLock()


def iterate_admins():
    admins_lock.acquire()
    yield from list(admins.items())
    admins_lock.release()
