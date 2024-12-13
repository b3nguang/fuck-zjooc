import base64
from itertools import chain
from pprint import pprint
from rich.console import Console
from rich.progress import Progress

import ddddocr
import html2text
import requests

Headers = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "SignCheck": "935465b771e207fd0f22f5c49ec70381",
    "TimeDate": "1694747726000",
    # 这里的TimeDate 和 SignCheck 是时间戳和加密后的token
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/111.0.0.0 Safari/537.36",
}


def get_captcha() -> dict:  # 获取验证码信息
    captcha_headers = {
        "User-Agent": "Mozilla/5.0(WindowsNT10.0;Win64;x64)AppleWebKit/537.36(KHTML,likeGecko)Chrome/98.0.4758.102Safari/537.36",
    }
    captcha = requests.get(
        "https://centro.zjlll.net/ajax?&service=/centro/api/authcode/create&params=",
        headers=captcha_headers,
    ).json()["data"]
    #    img_bytes = base64.b64de(b64_img)
    #   with open("test.jpg", 'wb') as f:
    #         f.write(img_bytes)
    return captcha


class ZJOOC:
    def __init__(self, username="", pwd=""):
        # user = requests.session() session 实例化后可以不用一直填写 Header 和 cookies 太懒了不想改了
        self.session = requests.Session()
        self.session.verify = False
        self._batch_dict = dict()
        self.login(username, pwd)
        self.coursemsg

    def login(self, username="", pwd="") -> None:
        login_res: dict = {}
        while True:
            captcha_data = get_captcha()
            captcha_id = captcha_data["id"]  # 验证码ID
            ocr = ddddocr.DdddOcr(show_ad=False)
            captcha_code = ocr.classification(base64.b64decode((captcha_data["image"])))
            # pprint(f"captcha_code: {captcha_code}")

            login_data = {
                "login_name": username,
                "password": pwd,
                "captchaCode": captcha_code,
                "captchaId": captcha_id,
                "redirect_url": "https://www.zjooc.cn",
                "app_key": "0f4cbab4-84ee-48c3-ba4c-874578754b29",
                "utoLoginTime": "7",
            }
            # FIXME 这里并没有做异常处理 一般情况下你账号密码正确 没有什么问题 可能验证码错误重试即可。
            try:
                login_res = self.session.post(
                    "https://centro.zjlll.net/login/doLogin", data=login_data
                ).json()
            except Exception as ex:
                pprint(ex)
                print("Login failed.")
                break

            if login_res.get("resultCode", 1) == 0:
                break
            else:
                continue

        login_param = {
            # 'time': 'm6kxkKnDKxj7kP6yziFQiB8JcAXrsBC41646796129000',
            # time 可以不传 是一个时间戳加密后的数据
            "auth_code": login_res.get("authorization_code", ""),
            "autoLoginTime": "7",
        }
        self.session.get("https://www.zjooc.cn/autoLogin", params=login_param)
        # print("Login success.")
        # # dict_from_cookiejar 把cookies 对象 转换为python dict
        # self._cookies = requests.utils.dict_from_cookiejar(login_res.cookies)

    @property
    def infomsg(self) -> dict:
        params = {"service": "/centro/api/user/getProfile", "params[withDetail]": True}
        info_data = self.session.get(
            "https://www.zjooc.cn/ajax", params=params, headers=Headers
        ).json()

        info_data = info_data["data"]
        course_msg_dict = {
            "name": info_data["name"],
            "corpName": info_data["corpName"],
            "studentNo": info_data["studentNo"],
            "loginName": info_data["loginName"],
            "roleType": info_data["roleType"],
        }
        return course_msg_dict

    @property
    def coursemsg(self) -> list:
        params = {
            "service": "/jxxt/api/course/courseStudent/student/course",
            "params[pageNo]": 1,
            "params[pageSize]": 5,
            "params[coursePublished]=": "",
            "params[courseName]": "",
            "params[batchKey]": "",
        }
        course_msg_data = self.session.get(
            "https://www.zjooc.cn/ajax",
            params=params,
            headers=Headers,
        ).json()["data"]
        course_lst = [
            {
                "id": i,
                "courseId": course_msg_data[i]["id"],
                "courseName": course_msg_data[i]["name"],
                "courseBatchId": course_msg_data[i]["batchId"],
                "courseProcessStatus": course_msg_data[i]["processStatus"],
            }
            for i in range(len(course_msg_data))
        ]

        # 获取课程id对应的batchid
        self._batch_dict = {
            course_msg_data[i]["id"]: course_msg_data[i]["batchId"]
            for i in range(len(course_msg_data))
        }

        return course_lst

    def _get_msg(self, modes: str | int) -> list:
        """
        :param mode: 0-测验 1-考试 2-作业
        :return:  [{}]
        """
        # assert modes in (0, 1, 2)
        modes = str(modes)
        msg_lst: list = []
        for mode in modes:
            params = {
                "params[pageNo]": 1,
                "params[pageSize]": 20,
                "params[paperType]": mode,
                "params[batchKey]": 20231,
            }

            res_msg_data = self.session.get(
                "https://www.zjooc.cn/ajax?service=/tkksxt/api/admin/paper/student/page",
                params=params,
                headers=Headers,
            ).json()["data"]

            msg_lst.extend(
                [
                    {
                        "id": idx,
                        "courseName": data["courseName"],
                        "paperName": data["paperName"],
                        "classId": data["classId"],
                        "courseId": data["courseId"],
                        "paperId": data["paperId"],
                        "scorePropor": data["scorePropor"],
                    }
                    for idx, data in enumerate(res_msg_data)
                ]
            )

        if not msg_lst:
            print("🤣🤣🤣  Congrats!! all work you have done!!!")
        return msg_lst

    @property
    def quizemsg(self) -> list:
        return self._get_msg("0")

    @property
    def exammsg(self) -> list:
        return self._get_msg("1")

    @property
    def hwmsg(self) -> list:
        return self._get_msg("2")

    @property
    def scoremsg(self) -> list:
        score_lst = []
        params = {
            "service": "/report/api/course/courseStudentScore/scoreList",
            "params": {
                "pageNo": 1,
                "pageSize": 20,
                "courseId": "",
                "batchKey": "",
            },
            "checkTimeout": "true",
        }

        res_score_data = self.session.get(
            "https://www.zjooc.cn/ajax?",
            params=params,
            headers=Headers,
        ).json()["data"]
        score_lst = [
            {
                "courseId": data["courseId"],
                "courseName": data["courseName"],
                "finalScore": data["finalScore"],
                "videoScore": data["videoScore"],
                "onlineScore": data["onlineScore"],
                "offlineScore": data["offlineScore"],
                "testScore": data["testScore"],
                "homeworkScore": data["homeworkScore"],
            }
            for data in res_score_data
        ]

        return score_lst

    def get_video_msg(self, course_id) -> list:
        video_msg: list
        params = {
            "params[pageNo]": 1,
            "params[courseId]": course_id,
            "params[urlNeed]": "0",
        }
        video_data = self.session.get(
            "https://www.zjooc.cn/ajax?service=/jxxt/api/course/courseStudent/getStudentCourseChapters",
            params=params,
            headers=Headers,
        ).json()["data"]
        video_msg = [
            {
                "Name": f'{chapter["name"]}-{section["name"]}-{resource["name"]}',
                "courseId": course_id,
                "chapterId": resource["id"],
                "time": resource.get("vedioTimeLength", 0),
            }
            for chapter in video_data
            for section in chapter["children"]
            for resource in section["children"]
            if resource["learnStatus"] == 0
        ]

        return video_msg

    def do_video(self, course_id):
        """
        This function performs a video operation for a given course ID.

        Parameters:
            course_id (int): The ID of the course for which the video operation is performed.

        Returns:
            None
        """
        # 手动填入要做的video 的 courseid
        if not course_id:
            return

        video_lst = self.get_video_msg(course_id=course_id)
        video_cnt = len(video_lst)

        # Initialize a console and a progress bar
        console = Console()
        progress = Progress(
            "[progress.description]{task.description}",
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            "{task.completed}/{task.total}",
            console=console,
        )
        
        # Create the task for video progress
        task = progress.add_task("Processing videos...", total=video_cnt)

        with progress:
            for idx, video in enumerate(video_lst, start=1):
                if video["time"]:
                    params = {
                        "params[chapterId]": video["chapterId"],
                        "params[courseId]": video["courseId"],
                        "params[playTime]": str(video["time"]),
                        "params[percent]": "100",
                    }
                    self.session.get(
                        "https://www.zjooc.cn/ajax?service=/learningmonitor/api/learning/monitor/videoPlaying",
                        params=params,
                        headers=Headers,
                    ).json()
                else:
                    params = {
                        "params[courseId]=": video["courseId"],
                        "params[chapterId]=": video["chapterId"],
                    }
                    self.session.get(
                        "https://www.zjooc.cn/ajax?service=/learningmonitor/api/learning/monitor/finishTextChapter",
                        params=params,
                        headers=Headers,
                    ).json()

                # Update the progress bar
                progress.update(task, advance=1)

                # Show the current video being processed
                progress.console.print(
                    f"[bold green]{video['Name']}[/bold green] is being processed... "
                    f"[bold cyan]{(idx / video_cnt) * 100:.0f}%[/bold cyan]",
                    end="\r",
                )

        # Print final message
        console.print("\n[bold green]All videos processed successfully![/bold green]")
    def get_an(self, paperId, course_id) -> dict:
        """
        Retrieves the answer data for a given paper ID and course ID.

        Args:
            paperId (int): The ID of the paper.
            course_id (int): The ID of the course.

        Returns:
            dict: A dictionary containing the answer data, where the keys are the IDs of the answer data
                and the values are the corresponding right answers.
        """
        if not all([paperId, course_id]):
            return {}

        res_answer_data: list = []
        try:
            answer_data = {
                "service": "/tkksxt/api/student/score/scoreDetail",
                "body": "true",
                # FIXME 默认为 20231
                "params[batchKey]": self._batch_dict.get(course_id, 20231),
                "params[paperId]": paperId,
                "params[courseId]": course_id,
            }

            res_answer_data = self.session.post(
                "https://www.zjooc.cn/ajax",
                data=answer_data,
                headers=Headers,
            ).json()["data"]["paperSubjectList"]
        except Exception as ex:
            print("err:", ex)

        pprint(
            {
                html2text.html2text(an_data["subjectName"]): html2text.html2text(
                    an_data["subjectOptions"][ord(an_data["rightAnswer"]) - 65][
                        "optionContent"
                    ]
                )
                for an_data in res_answer_data
            }
        )
        return {an_data["id"]: an_data["rightAnswer"] for an_data in res_answer_data}

    def do_an(self, paper_id, course_id, class_id):
        if not all([paper_id, course_id, class_id]):
            return

        # 获取题目答案
        paper_an_data = self.get_an(paper_id, course_id)
        # 申请答题
        answesparams = {
            "service": "/tkksxt/api/admin/paper/getPaperInfo",
            "params[paperId]": paper_id,
            "params[courseId]": course_id,
            "params[classId]": class_id,
            "params[batchKey]": self._batch_dict[course_id],
        }
        paper_data = self.session.get(
            "https://www.zjooc.cn/ajax",
            params=answesparams,
            headers=Headers,
        ).json()["data"]

        send_data = {
            "service": "/tkksxt/api/student/score/sendSubmitAnswer",
            "body": "true",
            "params[batchKey]": self._batch_dict[course_id],
            "params[id]": paper_data["id"],
            "params[stuId]": paper_data["stuId"],
            "params[clazzId]": paper_data["paperSubjectList"],
            "params[scoreId]": paper_data["scoreId"],
            **{
                f"params[paperSubjectList][{idx}][id]": subject["id"]
                for idx, subject in enumerate(paper_data["paperSubjectList"])
                for k, v in {
                    "id": subject["id"],
                    "subjectType": subject["subjectType"],
                    "answer": paper_an_data[subject["id"]],
                }.items()
            },
        }
        try:
            res = self.session.post(
                "https://www.zjooc.cn/ajax", data=send_data, headers=Headers
            ).content.decode("utf-8")
            res.raise_for_status
        except requests.RequestException:
            print("Failed to send data!!")

    
    
    def do_ans(self):
        """
        # FIX 谨慎使用！！！
        """
    
        messages_lst = [self.exammsg, self.hwmsg, self.quizemsg]
        paper_cnt = sum(len(msg) for msg in messages_lst)
        for idx, msg in enumerate(chain(*messages_lst)):
            if msg["scorePropor"] != "100/100.0":
                self.do_an(
                    paper_id=msg["paperId"],
                    course_id=msg["courseId"],
                    class_id=msg["classId"],
                )
                progress = idx / paper_cnt
                progress_bar = f"{'😎' * int(progress * 10)}{'--' * (10 - int(progress * 10))}[{progress:.0%}]"
                print("\r", progress_bar, end="")
    def paser(self, commands: str):
        command_list = commands.split()

        def error_msg():
            print("paser err!!!")
            print("please enter your commands again!")

        try:
            match command_list[0]:
                case "msg":
                    """
                    0-测验 1-考试 2-作业
                    3-info 4-course 5-score
                    6-video 7-an
                    ex:
                        msg 0
                        msg 6 course_id
                        msg 7 paperId course_id
                    """
                    match command_list[1]:
                        case "0" | "1" | "2":
                            pprint(self._get_msg(command_list[1]))
                        case "3":
                            pprint(self.infomsg)
                        case "4":
                            return self.coursemsg
                        case "5":
                            pprint(self.scoremsg)
                        case "6":
                            if len(command_list) < 3:
                                error_msg()
                            else:
                                pprint(self.get_video_msg(command_list[2]))
                        case "7":
                            self.get_an(command_list[2], command_list[3])
                case "do":
                    """
                    0-测验、考试、作业 1-video 2-all[not suggest!!!]
                    ex：
                        do 0 paper_id course_id class_id
                        do 1 course_id
                        do 2 #FIX 谨慎使用！！！
                    """
                    match command_list[1]:
                        case "0":
                            self.do_an(
                                paper_id=command_list[2],
                                course_id=command_list[3],
                                class_id=command_list[4],
                            )
                        case "1":
                            self.do_video(command_list[2])
                        case "2":
                            self.do_ans()

                case _:
                    error_msg()
                    return
        except Exception as ex:
            error_msg()
            print(ex)
            return
