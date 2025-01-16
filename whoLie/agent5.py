# 还没解决分数问题和反馈问题
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
        self.expert_memories = {}  # 为每个专家单独存储记忆

    def analyze(self, query):
        self.output = "no answer"
        self.round += 1

        # 初始化系统消息和用户消息
        init_system = (
            "请你输出各个所需要专家的领域，每个领域用专家结尾，使用','分隔开，确保至少有一位'结果检验与整合专家'来负责对所有专家的结果进行检验与整合，不要输出任何其它无关的信息"
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
                # 获取专家相关的历史记忆
                expert_history = self.get_expert_memory(expert)

                expert_system = (
                    f"请你为{expert}布置任务。注意：\n"
                    f"1. 只提供与该专家工作相关的信息\n"
                    f"2. 如果这位专家之前参与过讨论，请告知其历史贡献\n"
                    f"3. 明确说明需要改进的地方"
                )

                expert_user = (
                    f"问题：{query}\n"
                    f"专家历史记忆：{expert_history}\n"
                    f"请为专家布置明确的任务"
                )

                expert_memory = send_message(expert_system, expert_user, self.model)
                print(expert_memory)

                # 获取专家回答
                response = self.ask(expert, expert_memory)
                print(response)

                # 只保存与当前专家相关的任务信息
                self.add_expert_memory(expert, expert_memory)
                expert_responses[expert] = response

        # 结果检验与整合专家进行整合和评分
        judge_system = (
            "你是结果检验与整合专家，请：\n"
            "1. 对每个专家的答案进行独立评分（1-10分）\n"
            "2. 详细说明每个评分的理由\n"
            "3. 给出具体的改进建议\n"
            "4. 将所有专家的答案整合成一个完整的解决方案\n"
            "5. 对整体方案进行评分"
        )
        judge_user = (
            f"对于用户提出的问题{query},你和你的团队进行了探讨，探讨过程如下，{self.memory_service.get_all_memories()} "
            f"以下是各个专家给出的回答，{expert_responses} "
            "请你对各个专家的答案进行整合输出，并对每个专家的解答进行评分（1-10分），"
            "评分格式为：'评分: <分数> 分'，例如 '评分: 9 分'并请给出评分理由。"
        )
        judge_response = send_message(judge_system, judge_user, self.model)
        print(judge_response)

        # 提取评分
        final_score = self.extract_score_from_judge(judge_response)
        print(f"专家平均评分为：{final_score}")
        if final_score >= 7:
            self.output = judge_response
        else:
            self.output = self.generate_feedback(final_score, judge_response)

        # 若评分不够高，进入第二轮
        # 我希望第二回合不要改专家，而且专家可以看到之前自己的代码，以及别人给的反馈优化方案，从而可以进行优化
        while self.output == "no answer" and self.round < 3:
            print(f"当前是第{self.round}轮，继续生成任务。")
            # 若评分不合格，进行反馈生成，继续第二轮生成
            expert_system = "请你根据反馈优化方案，生成新的任务并给专家布置新任务"
            expert_user = f"你需要根据以下反馈改进���的解答：{self.output}. 请为专家生成新的任务，并继续工作。"
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
        return 0  # 如果没有有效的评分，返回认分数0

    def generate_feedback(self, final_score, judge_response):
        feedback_system = (
            "请根据评分和评语生成建设性的反馈：\n"
            "1. 指出具体的问题\n"
            "2. 提供明确的改进方向\n"
            "3. 建议具体的优化步骤"
        )

        feedback_user = (
            f"评分：{final_score}\n"
            f"评语：{judge_response}\n"
            "请生成有针对性的反馈"
        )

        feedback = send_message(feedback_system, feedback_user, self.model)
        return feedback

    def ask(self, expert, memory):
        expert_system = f"你是一个{expert}，你具有严谨的思维能力和逻辑能力。你的领导给你布置了一个任务，请你给出详细回答。"
        response = send_message(expert_system, memory, self.model)
        self.memory_service.add_memory(f"{expert}认为，{response}")
        return response

    def get_expert_memory(self, expert):
        """获取指定专家的相关记忆"""
        if expert == "结果检验与整合专家":
            return self.memory_service.get_all_memories()
        return self.expert_memories.get(expert, [])

    def add_expert_memory(self, expert, memory):
        """为指定专家添加记忆"""
        if expert not in self.expert_memories:
            self.expert_memories[expert] = []
        self.expert_memories[expert].append(memory)


# 示例运行
meta_prompt = MetaPrompt('gpt-4o-mini')
user_query = "怎么用python实现一个24点小游戏？给我具体实现"
final_response = meta_prompt.analyze(user_query)
print("\n\n\n\n\n\n\n\n\n最终结果：")
print(final_response)
