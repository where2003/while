from memory import MemoryService  # 假设你将 Memory.py 保存为 memory.py
from llm_base import send_message


class MetaPrompt:
    def __init__(self, model='gpt-3.5-turbo'):
        self.model = model
        self.memory_service = MemoryService()
        self.expert_template = "You are an expert in {expert_area}. Your task is to assist with the following: {task}"
        self.expert_library = []  # 存储专家库
        self.output = "no answer"
        self.expert_attitude = "no attitude"
        self.previous_expert = None  # 存储上一次询问的专家

    def analyze(self, query):
        self.output = "no answer"
        init_system = (
            "请你输出各个所需要专家的field，每个领域用“专家”结尾，使用','分隔开，确保一定有至少一位'结果检验与整合专家'来负责对所有专家的结果进行检验与整合，不要输出任何其它无关的信息"
        )
        init_user = (
            f'你是一个经验丰富的团队管理专家，具有很强的逻辑能力和批判性思维，你正要组织团队解决一个问题：{query}。'
            f'现在，请你输出多个用于解决这个问题的专家，确保团队成员具有解决问题的能力和检验能力'
        )
        field = send_message(init_system, init_user, self.model)
        self.expert_library = field.split(',')
        print(f"已生成专家库：{self.expert_library}")

        # 将用户问题和专家库存储到记忆中
        self.memory_service.add_memory(f"用户问题: {query}")
        self.memory_service.add_memory(f"生成专家库: {self.expert_library}")

        # 每个专家进行一轮解答
        expert_responses={} # 存储每个专家的回答
        for expert in self.expert_library:
            if "结果检验与整合专家" not in expert:
                expert_system = f"请你为{expert}布置任务，假设他不知道你们的讨论内容，请你给出适当的、需要告知他的讨论信息。"
                expert_user = (
                    f"在之前的问答中，用户提出了问题：{query}，你和你的团队进行了探讨。"
                    f"你们之前的讨论信息如下：{self.memory_service.get_all_memories()}"
                    f"现在，请你编辑说给{expert}的话，告诉他目前的讨论进展，并为他布置任务。如果之前的讨论信息中这个专家有参与过，要把他曾经参与的部分告诉他"
                )
                expert_memory = send_message(expert_system, expert_user, self.model)
                print(expert_memory)

                response = self.ask(expert, expert_memory)
                print(response)
                expert_responses[expert]=response

        # 结果检验与整合专家进行整合和评分
        judge_system = "你是结果检验与整合专家，负责对所有专家的解答进行综合和评分。请你对每个专家的答案进行整合，然后对这个整合好的方案进行评分，评分范围为1-10分，满分10分，评分标准是答案的质量和可操作性，并且给出评分原因"
        judge_user=(
            f"对于用户提出的问题{query},你和你的团队进行了探讨，探讨过程如下，{self.memory_service.get_all_memories()}"
            f"以下是各个专家给出的回答，{expert_responses}"
            "请你对每个专家的解答进行评分（1-10分），格式为评分+分数，并给出评分理由。"
        )
        judge_response=send_message(judge_system,judge_user,self.model)
        print(judge_response)

        # 如果评分高，就输出，不够高就继续生成
        final_score=self.extract_score_from_judge(judge_response)
        if final_score>=7:
            self.output=judge_response
        else:






        while self.output == "no answer":
            print(f"上一位专家：{self.previous_expert}")
            judge_system = "检查是否存在一个：经过'结果检验与整合专家'检验与整合，且完美回答了用户问题的答案，如果有，输出YES，否则输出NO，并给出原因"
            judge_user = (
                f"对于用户提出的问题：{query}, 你和你的团队进行了探讨，探讨过程如下：{self.memory_service.get_all_memories()}"
                f"检查探讨过程中是否存在由结果检验专家给出的、且完美回答了用户问题的答案。注意，不是由结果检验与整合专家本人给出的，应当视为错误答案")
            judge = send_message(judge_system, judge_user,self.model).lower()

            print(f"当前问题是否解决：{judge}")

            if 'no' in judge:
                expert_system = "仅输出你选择的专家的名字，不要输出任何其它内容。结果检验与整合专家不能检验自己的回答，也不能检验空回答"
                expert_user = (f"在之前的问答中，用户提出了问题：{query}，你和你的团队进行了探讨。"
                               f"你认为你们目前的讨论尚不能发送给用户，因为：{judge}"
                               f"最近的讨论内容是：{self.memory_service.get_all_memories()}"
                               f"现在你需要挑选一位新的专家，来继续讨论")
                expert = send_message(expert_system, expert_user,self.model)
                print(expert)

                expert_memory_system = "请你为选定的专家布置任务，假设他不知道你们的讨论内容，请你给出适当的、需要告知他的讨论信息。"
                expert_memory_user = (
                    f"在之前的问答中，用户提出了问题：{query}，你和你的团队进行了探讨。"
                    f"你们挑选的上一位专家是：{self.previous_expert}, 他的观点是：{self.expert_attitude}"
                    f"现在，你挑选了另一位专家：{expert}发表意见，"
                    f"你们曾经的讨论信息如下：{self.memory_service.get_all_memories()}"
                    f"现在，请你编辑说给这个专家的话，告诉他目前的讨论进展，并为他布置任务。")
                expert_memory = send_message(expert_memory_system, expert_memory_user, self.model)
                print(expert_memory)

                response = self.ask(expert, expert_memory)
                print(response)

                refresh_system = "请你保证答案的简练干净，同时要点清晰明确，符合用户要求。"
                refresh_user = (
                    f"对于你给定的任务：{expert_memory}，专家{expert}的回答如下：{response}。"
                    f"你们的讨论过程如下：{self.memory_service.get_all_memories()}"
                    f"现在，你需要根据这些内容，整理你们团队的最新讨论结果。")
                refresh = send_message(refresh_system, refresh_user,self.model)
                self.expert_attitude = refresh
                print(refresh)
                self.previous_expert = expert
            else:
                self.output = self.expert_attitude

        output_system = "根据给出的讨论结果，输出一份答案，用以直接地回答用户的问题"
        output_user = f"讨论过程是：{self.memory_service.get_all_memories()}，用户的问题是：{query}"
        # return send_message(output_system, output_user)
        final_answer =send_message(output_system, output_user)

        with open("answer.txt","a",encoding="utf-8") as file:
            file.write(f"问题：{query}\n  答案：{final_answer}\n")
            file.write("-"*50+"\n")
        return  final_answer

    def extract_score_from_judge(self, judge_response):
        score = 0
        if ("评分") in judge_response:
            score_str = judge_response.split("评分")[1].strip().split()[0]
            score = int(score_str)
        return score

    def generate_feedback(self,final_score,expert_response):


    def ask(self, expert, memory):
        expert_system = f"你是一个{expert}，你具有严谨的思维能力和逻辑能力。你的领导给你布置了一个任务，请你给出详细回答。"
        response = send_message(expert_system, memory,self.model)
        self.memory_service.add_memory(f"{expert}认为，{response}")
        return response


# 使用示例
meta_prompt = MetaPrompt('gpt-4o-mini')
user_query = "怎么用python实现一个24点小游戏？给我具体实现"

# 初始化计数和最终结果
count = 0
response = None
response_two = None
response_three = None

# 修改为 while count < 3，确保循环执行三次
while count < 3:
    if count == 0:
        # 第一次分析用户查询
        response = meta_prompt.analyze(user_query)
        print(f"第1次分析结果：{response}")
    elif count == 1:
        # 第二次分析：找出第一份解决方案的不足之处
        transformations = (
            f"这是我们要解决的问题：{user_query}，我们现在提供了一个解决方案：{response}，请分析这个解决方案的不足之处。"
        )
        response_two = meta_prompt.analyze(transformations)
        print(f"第2次分析结果：{response_two}")
    elif count == 2:
        # 第三次分析：改进解决方案
        alternatives = (
            f"这是我们要解决的问题：{user_query}，我们之前提出了一个解决方案：{response}，"
            f"但是我们发现这个解决方案有不足的地方：{response_two}，请给出一个更好的解决方案。"
        )
        response_three = meta_prompt.analyze(alternatives)
        print(f"第3次分析结果：{response_three}")

    # 增加计数器，防止死循环
    count += 1

# 最终输出
print("\n\n\n\n\n\n\n\n\n最终结果：")
if response:
    print(response)
elif response_two:
    print(response_two)
elif response_three:
    print(response_three)
else:
    print("没有生成有效的最终结果。")
