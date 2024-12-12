import re  # 导入正则表达式模块

from llm_base import send_message
from memory import MemoryService


class MetaPrompt:
    def __init__(self, model='gpt-3.5-turbo'):
        self.model = model
        self.memory_service = MemoryService()
        self.expert_template = "You are an expert in {expert_area}. Your task is to assist with the following: {task}"
        self.expert_library = []  # 存储专家库
        self.output = "no answer"
        self.expert_attitude = "no attitude"
        self.previous_expert = None  # 存储上一次询问的专家
        self.round = 0  # 记录当前是第几轮生成

    def analyze(self, query):
        self.output = "no answer"
        self.round += 1

        # 初始化系统消息和用户消息
        init_system = (
            "请你输出各个所需要专家的领域，每个领域用“专家”结尾，使用','分隔开，确保至少有一位'结果检验与整合专家'来负责对所有专家的结果进行检验与整合，不要输出任何其它无关的信息"
        )
        init_user = (
            f'你是一个经验丰富的团队管理专家，具有很强的逻辑能力和批判性思维，正要组织团队解决一个问题：{query}。'
            f'请输出多个专家，确保团队成员具有解决问题的能力和检验能力'
        )

        # 获取专家库
        field = send_message(init_system, init_user, self.model)
        self.expert_library = field.split(',')
        print(f"已生成专家库：{self.expert_library}")

        # 将用户问题和专家库存储到记忆中
        self.memory_service.add_memory(f"用户问题: {query}")
        self.memory_service.add_memory(f"生成专家库: {self.expert_library}")

        # 每个专家进行一轮解答
        expert_responses = {}  # 存储每个专家的回答
        for expert in self.expert_library:
            if "结果检验与整合专家" not in expert:
                expert_system = f"请你为{expert}布置任务，假设他不知道你们的讨论内容，请你给出适当的、需要告知他的讨论信息。"
                expert_user = (
                    f"在之前的问答中，用户提出了问题：{query}，你和你的团队进行了探讨。"
                    f"你们的讨论信息如下：{self.memory_service.get_all_memories()}"
                    f"现在，请你编辑说给{expert}的话，告诉他目前的讨论进展，并为他布置任务。如果之前的讨论信息中这个专家有参与过，要把他曾经参与的部分告诉他"
                )
                expert_memory = send_message(expert_system, expert_user, self.model)
                print(expert_memory)

                # 获取专家回答
                response = self.ask(expert, expert_memory)
                print(response)

                # 只保存与当前专家相关的任务信息
                self.memory_service.add_memory(f"{expert}的回答: {response}")
                expert_responses[expert] = response

        # 结果检验与整合专家进行整合和评分
        judge_system = "你是结果检验与整合专家，负责对所有专家的解答进行整合和评分。请你对每个专家的答案进行整合，然后对这个整合好的方案进行评分，评分范围为1-10分，满分10分，评分标准是答案的质量和可操作性，并且给出评分原因"
        judge_user = (
            f"对于用户提出的问题{query},你和你的团队进行了探讨，探讨过程如下，{self.memory_service.get_all_memories()} "
            f"以下是各个专家给出的回答，{expert_responses} "
            "请你对各个专家的答案进行整合输出，并对每个专家的解答进行评分（1-10分），"
            "评分格式为：'评分: <分数> 分'，例如 '评分: 9 分'，并请给出评分理由。"
        )
        judge_response = send_message(judge_system, judge_user, self.model)
        print(judge_response)

        # 提取评分
        final_score = self.extract_score_from_judge(judge_response)
        print(f"专家平均评分为：{final_score}")
        if final_score >= 9:
            self.output = judge_response
        else:
            # self.output = self.generate_feedback(final_score, judge_response)
            self.output="no answer"

        # 若评分不够高，进入第二轮
        # 我希望第二回合不要改专家，而且专家可以看到之前自己的代码，以及别人给的反馈优化方案，从而可以进行优化
        while self.output == "no answer" and self.round < 3:
            print(f"当前是第{self.round}轮，继续生成任务。")
            # 若评分不合格，进行反馈生成，继续第二轮生成
            expert_system = "请你根据反馈优化方案，生成新的任务并给专家布置新任务"
            expert_user = f"你需要根据以下反馈改进你的解答：{self.output}. 请为专家生成新的任务，并继续工作。"
            new_query = send_message(expert_system, expert_user, self.model)

            self.output = self.analyze(new_query)

        # 输出最终结果
        output_system = "根据给出的讨论结果，输出一份答案，用以直接地回答用户的问题"
        output_user = f"讨论过程是：{self.memory_service.get_all_memories()}，用户的问题是：{query} "
        final_answer = send_message(output_system, output_user)

        # 保存结果
        with open("answer.txt", "a", encoding="utf-8") as file:
            file.write(f"问题：{query}\n  答案：{final_answer}\n")
            file.write("-" * 50 + "\n")
        return self.output

    def extract_score_from_judge(self, judge_response):
        # 使用正则表达式提取每个专家的评分
        scores = []
        matches = re.findall(r"评分: (\d+(\.\d+)?)\s*", judge_response)  # 匹配类似 "评分 8.5" 或 "评分 8" 的格式
        for match in matches:
            try:
                score = float(match[0])  # 将匹配到的评分字符串转换为浮动数字
                scores.append(score)
            except ValueError:
                continue  # 如果无法转换为数字，忽略

        # 计算平均分
        if scores:
            average_score = sum(scores) / len(scores)
            print(average_score)
            return round(average_score, 2)  # 返回平均分，保留两位小数
        return 0  # 如果没有有效的评分，返回默认分数0

    def generate_feedback(self, final_score, judge_response):
        feedback = f"结果评分为{final_score}分。反馈如下：{judge_response}。"
        return feedback

    def ask(self, expert, memory):
        expert_system = f"你是一个{expert}，你具有严谨的思维能力和逻辑能力。你的领导给你布置了一个任务，请你给出详细回答。"
        response = send_message(expert_system, memory, self.model)
        self.memory_service.add_memory(f"{expert}认为，{response}")
        return response


# 示例运行
meta_prompt = MetaPrompt('gpt-4o-mini')
user_query = "怎么用python实现一个24点小游戏？给我具体实现"

final_response = meta_prompt.analyze(user_query)
print("\n\n\n\n\n\n\n\n\n最终结果：")
print(final_response)
