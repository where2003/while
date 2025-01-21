import re  # 导入正则表达式模块

from llm_base import send_message
from memory import MemoryService


class MetaPrompt:
    def __init__(self, model='gpt-3.5-turbo'):
        self.model = model
        self.memory_service = MemoryService()
        self.expert_template = "You are an expert in {expert_area}. Your task is to assist with the following: {task}"
        self.expert_library = []  # 存储专家库 
        self.output = "no answer"# 存储当前最新的方案结果
        self.expert_attitude = "no attitude"
        self.previous_expert = None  # 存储上一次询问的专家
        self.round = 0  # 记录当前是第几轮生成
        self.expert_memories = {}  # 为每个专家单独存储记忆
        self.feedback="no feedback"
        self.integration_results = []  # 存储每轮的整合结果
        self.init_query={}

    def init_expert(self, query, output=None):
        # self.output = "no answer"
        self.output = output
        self.round = 0
        self.init_query=query
        # self.query=query
        # 初始化系统消息和用户消息
#        init_system = (
#            "请你输出各个所需要专家的领域，每个领域用专家结尾，使用','分隔开，确保至少有一位'结果检验与整合专家'来负责对所有专家的结果进行检验与整合，不要输出任何其它无关的信息"
#            "同时请你找该领域"
#        )
#        init_user = (
#            f'你是一个经验丰富的团队管理专家，具有很强的逻辑能力和批判性思维，正要组织团队解决一个问题：{query}。'
#            f'请输出多个专家，确保团队成员具有解决问题的能力和检验能力'
#        )
        init_system=("You are a professional problem analysis expert, please help me analyze the user problem and determine which fields of experts are needed to answer it."
                     "And help me provide each expert with the identity of the most representative historical figure in the field."
                    )
        init_user=(f"You're an experienced problem analyst and you're organizing a team to solve a problem:{query}"
                   "Ask you to output multiple experts who are best suited to answer this question to ensure that team members have problem-solving skills and testing skills."
                   "The output format of the expert is: domain|name of expert|short description"
                   "Note: 1. Only output the above format, no other content."
                   "2. Select the most representative historical figures in the field."
                   "3. Ensure that the expert portfolio can solve the problem completely.")
          # 获取专家库
        expert_field = send_message(init_system, init_user, self.model)
        #self.expert_library = field.split(',')
        for line in expert_field.strip().split('\n'):
            if line:
                field,name,description=line.strip().split('|')
                expert=f"You are {name}, {description},the leading expert in the field of {field}."
                self.expert_library.append(expert)
                
        #将专家库存储到记忆中
        print(f"已生成专家库：{self.expert_library}")
        self.memory_service.add_memory(f"Generate a pool of experts: {self.expert_library}")

        return None


    def analyze(self, query):

        self.round += 1
        # self.query=query
        # 将用户问题和专家库存储到记忆中
        self.memory_service.add_memory(f"User Questions: {query}")

        # 每个专家进行一轮解答
        expert_responses = {}  # 存储每个专家的回答
        for expert in self.expert_library:
            if "Expert in results testing and integration" not in expert:
                # 获取专家相关的历史记忆
                expert_history = self.get_expert_memory(expert)
                
                expert_system = (
                    f"Please assign a task for {expert}. note:\n"
                    f"1. Provide only information that is relevant to the expert's work.\n"
                    f"2. If the expert has been involved in the discussion before, please inform him of his or her historical contributions.\n"
                    f"3. On the basis of the historical specific plan (if the historical specific plan is not empty), clearly indicate the areas for improvement."
                )
                
                expert_user = (
                    f"Issue:{query}\n"
                    f"Expert Historical Memory:{expert_history}\n"
                    f"Current concrete and feasible historical solutions:{self.output}"
                    f"Please assign clear tasks to the experts based on the above."
                )
                
                print(f"当前正在为{expert}布置任务")
                expert_memory = send_message(expert_system, expert_user, self.model)
                print(expert_memory)

                # 获取专家回答
                response = self.ask(expert, expert_memory)
                print(response)

                # 只保存与当前专家相关的任务信息
                self.add_expert_memory(expert, expert_memory)
                expert_responses[expert] = response

                # 将具体方案进行提取，然后更新历史具体方案
                response_system=("You are an integration expert, please extract the specific and feasible solutions according to the user's requirements in the text, and discard the rest."
                                  "For example, if you are asked to generate a code, only the specific code is kept, and everything else is removed.")
                response_user=f"This is the user question {self.init_query}, this is the generated solution text {response}, please extract the specific and feasible solution in the solution text according to the requirements of the user problem."
                self.output=send_message(response_system,response_user,self.model)

        # 结果检验与整合专家进行整合和评分
#        judge_system = (
#            "你是结果检验与整合专家，请：\n"
#            "1. 对每个专家的答案进行独立评分（1-100分）\n"
#            "2. 详细说明每个评分的理由\n"
#            "3. 给出具体的改进建议\n"
#            "4. 将所有专家的答案整合成一个完整的解决方案\n"
#            "5. 整合后的结果应该是一个能直接使用的答案，而不仅仅是一个实施方案。例如，我想要形成一首歌，就给我生成具体的一首歌的歌词。如果我想要一个演讲稿，就给我一个具体的演讲稿文字。"
#            "6. 如果有之前的方案结果，那么请你将本轮的改进建议和之前的方案结果结合起来，形成一个新的具体可行的结果，而不是一个告诉我应该怎么分配任务和时间的实施方案"
#            "7. 保持方案的完整性，如果有些方案的东西只在历史方案记录有记录，在最新的回答中没有涉及到相关的内容，那也要保留住历史记录的内容，与新回答一起整合，不可以直接忽略不计"
#            "8. 对新的整体方案进行评分"
#        )
#        judge_user = (
#            f"对于用户提出的问题{query},你和你的团队进行了探讨，探讨过程如下，{self.memory_service.get_all_memories()} "
#            f"这是历史方案记录{self.integration_results}"
#            f"以下是各个专家给出的最新回答，{expert_responses} "
#            "请你根据历史方案记录和当前专家给出的回答，对各个专家的答案进行整合输出，并对每个专家的解答进行评分（1-100分），"
#            "评分格式为：'评分: <分数> 分'，例如 '评分: 76 分'并请给出评分理由。"
#        )
        
        # 整合专家
        judge_system=(
             "You are an expert in the verification and integration of results, please complete the following requirements:\n"
             "Check whether the final concrete and feasible plan generated by the solidarity and cooperation of each expert is a concrete and feasible plan."
             "For example, if a user question asks for an experiment summary, the solution should only contain the text of the experiment summary and nothing else."
             "If it is not a concrete and feasible solution, it is integrated into a complete and concrete feasible solution based on the answers given by various experts."
             "Score the final concrete viable solution (1-100 points)"
        )
        judge_user=(
             f"You and your team discussed the {query} question asked by the user, and this is the latest answer from various experts{expert_responses}"
             f"This is the latest concrete and feasible solution{self.output}"
             "Please check whether the current solution results are a concrete and feasible result, and if not, integrate them into a concrete and feasible solution based on user questions and the latest answers given by various experts."
             "The scheme is then rated (1-100 points) in the format: 'Rating: <分数>points', e.g. 'Rating: 76 points' and the reason for the score."
        )
        judge_response = send_message(judge_system, judge_user, self.model)
        print(judge_response)
        
        # 存储当前轮次的整合结果
        # self.integration_results.append(judge_response)


        #把经过检验专家检验过的具体方案放入output中
        check_system=(
            "You're an integration expert, so you can extract the specific solution from the text that meets the user's requirements, and remove the rest."
            "For example, if you are asked to generate a code, only the specific code is kept, and everything else is removed."
        )
        check_user=(
            f"This is a user requirement{self.init_query}"
            f"This is the text that needs to be extracted{judge_response}"
            "Please extract specific and feasible content according to the user's requirements."
        )
        self.output=send_message(check_system,check_user,self.model)

        # 提取评分并判断
        score_result = self.extract_score_from_judge(judge_response)
        print(f"Overall Program Rating:{score_result['overall_score']}")
        print(f"Passed:{score_result['passed']}")

        #查看当前轮回是否可以输出答案
        if score_result['passed'] or self.round == 5:
            # self.output = judge_response
#            output_system ='''
#                            你是一个专业的答案整合专家，现在我将给你展示之前多轮专家讨论和方案整合的结果，请你仔细分析所有轮次的讨论内容
#                            提取其中最有价值的具体建议和可行答案，形成一个完整的、具体的、可执行的最终答案，
#                            要求：
#                            1、假设用户看不到专家讨论的结果，我们需要直接输出用户所需的具体内容（如演讲稿、代码、诗词、歌词等），并确保用户能看懂我们输出的内容
#                            2、不要添加任何额外的说明、建议或者评价
#                            3、确保方案的可行性和完整性，以及连贯性
#                            4、使用适合内容类型的格式直接呈现
#                            3、需要的是一个具体能用的答案，而不是一个分配任务和时间的实施方案。例如我需要一篇论文，就给我论文的内容。
#                            4、去除重复的内容，保留最优的内容
#                            '''
#            output_user = f"多轮讨论过程的整合后的结果是：{self.integration_results}，用户的问题是：{query} "
            final_answer = self.output
            # return final_answer
        else:
            self.feedback = self.generate_feedback(score_result['overall_score'], judge_response)
            # expert_system = "请你根据反馈优化方案，生成新的任务并给专家布置新任务"
            # expert_user = f"你需要根据以下反馈改进的解答：{self.feedback}. 请为专家生成新的任务，并继续工作。"
            # new_query = send_message(expert_system, expert_user, self.model)
            new_query=f"Now the user has a request: {self.init_query}, based on this we have generated a specific and feasible solution, but the generated solution is not good enough, this is the feedback of the improvement suggestions:{self.feedback}"
            final_answer=self.analyze(new_query)
        
        #不管是多少轮的结果都放在final_answer
        return final_answer
            # self.output = self.generate_feedback(score_result['expert_avg'], judge_response)

        # 若评分不够高，进入第二轮
        # 我希望第二回合不要改专家，而且专家可以看到之前自己的代码，以及别人给的反馈优化方案，从而可以进行优化
#        while self.feedback != "no feedback" and self.round < 3:
#            print(f"当前是第{self.round}轮，继续生成任务。")
#            # 若评分不合格，进行反馈生成，继续第二轮生成
#            expert_system = "请你根据反馈优化方案，生成新的任务并给专家布置新任务"
#            expert_user = f"你需要根据以下反馈改进的解答：{self.feedback}. 请为专家生成新的任务，并继续工作。"
#            new_query = send_message(expert_system, expert_user, self.model)

#            self.output = self.analyze(new_query)

        # 输出最终结果
#        output_system = "根据给出的讨论结果，输出一份答案，用以直接地回答用户的问题"
#        output_user = f"讨论过程是：{self.memory_service.get_all_memories()}，用户的问题是：{query} "
#        final_answer = send_message(output_system, output_user)

        # 保存结果
#        with open("answer.txt", "a", encoding="utf-8") as file:
#            file.write(f"问题：{query}\n  答案：{final_answer}\n")
#            file.write("-" * 50 + "\n")    

#        output_system = "根据给出的讨论结果，输出一份整合好的答案，用以直接地回答用户的问题。注意：不用告诉用户各个专家的回答，只需要告诉玩家整合后的答案。且不用告诉用户每个专家的评分和方案的整体评分"
#        output_user = f"讨论过程整合的结果是：{self.output}，用户的问题是：{query} "
#        final_answer = send_message(output_system, output_user)
#        return final_answer
       #  return self.output
    

    def extract_score_from_judge(self, judge_response):
        # 提取整体评分
        # matches = re.findall(r"评分：\s*(\d+(\.\d+)?)\s*分", judge_response)
        matches = re.findall(r"Rating:\s*(\d+(\.\d+)?)\s*points", judge_response)
        overall_score = float(matches[0][0]) if matches else 0
        
        # 判断评分是否达标（90分以上）
        score_status = {
            'overall_score': overall_score,
            'passed': overall_score >= 93
        }
        
        return score_status

    def generate_feedback(self, final_score, judge_response):
        feedback_system = (
            "Please generate constructive feedback based on ratings and comments:\n"
            "1. Point out specific issues\n"
            "2. Provide a clear direction for improvement\n"
            "3. Suggest specific optimization steps based on historical specific solutions"
        )
        
        feedback_user = (
            f"Score:{final_score}\n"
            f"Comments:{judge_response}\n"
            f"Historical specific programs{self.output}"
            "Please generate targeted feedback."
        )
        
        feedback = send_message(feedback_system, feedback_user, self.model)
        print(feedback)
        return feedback

    def ask(self, expert, memory):
        print(f"当前专家为：{expert}")
        expert_system = (f"You are a {expert} with rigorous thinking skills and logical skills. Your leader has assigned you a task,"
                        "It also gives you a concrete and feasible historical plan, and if the specific historical plan is not empty, please revise it on the basis of the specific historical plan to get a new specific plan."
                        "If it is empty, a concrete and feasible scenario result is generated. For example, if you want to generate a speech, only the specific content of the speech will be generated, and be careful not to generate the rest of the content that you don't need.")
        expert_user=f"This is your task {memory}, which is a concrete and feasible historical scheme: {self.output}, please generate a new concrete and feasible scheme based on the historical scheme according to the task requirements."
        response = send_message(expert_system, expert_user, self.model)
        self.memory_service.add_memory(f"{expert}think,{response}")
        # expert_responses[expert] = response

       # response_system=f"你是一个整合专家，请你在文本中根据用户要求提取出具体可行的方案，其他的都舍弃掉
        #                 比如要求生成一个代码，就只保留具体代码，其他的内容都去掉"
        # response_user=f"这是用户问题{self.query},这是生成的方案文本{response},请你根据用户问题的要求把方案文本中具体可行的方案提取出来"
        # return send_message(response_system,response_user,self.model)
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

    def reset(self):
        self.integration_results = []  # 重置整合结果列表


# 示例运行
meta_prompt = MetaPrompt('gpt-4o-mini')
# user_query = "怎么用python实现一个24点小游戏？给我具体实现"
# user_query="生成一首苏轼风格的诗词，内容是与山水有关的"
user_query = "Answer a question: How do the numbers 2, 6, 8, and 4 make up a mathematical formula so that the answer is 24. Note that these four numbers must be used regardless of whether they are repeated or not, and they can only be used once, and they must all appear once, and only those four numbers can be used."
meta_prompt.init_expert(user_query)
final_response = meta_prompt.analyze(user_query)
print("\n\n\n\n\n\n\n\n\n第一版方案最终结果：")
print(final_response)

#第二轮方案
meta_prompt2 = MetaPrompt('gpt-4o-mini')
user_query2 = (
    f"This is a user issue:{user_query}\n"
    f"Here's the answer generated from a user's question:{final_response}\n"
    "Please double-check the above scheme\n"
    "1. Evaluate whether the solution fully meets the user's original needs."
    "2. Point out the shortcomings of the current programme."
    "3. Based on the above analysis, a more complete scheme is given."
)
meta_prompt2.init_expert(user_query2)
final_response2=meta_prompt2.analyze(user_query2)
print("\n\n\n\n\n\n\n\n\n修改后的第二版方案最终结果：")
print(final_response2)

