import time
from openai import OpenAI

client = OpenAI(
    # This is the default and can be omitted
    base_url='https://api.openai-proxy.org/v1',
    api_key='sk-Yoqw2HYA1q6k0TPA2ObQuMvRi2sYkiPkDXHbXNcZ2B4gv1S3',
)


def send_message(system_message: str, user_message: str,model='gpt-3.5-turbo'):

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": 'system',
                "content": system_message
            },
            {
                "role": 'user',
                "content": user_message
            }
        ],
        model=model,
    )
    # timestamp =time.strftime("%Y-%m-%dT%H:%M",time.localtime())
    # filename=f"response_{timestamp}.txt"
    # final_answer = chat_completion.choices[0].message.content
    # with open(filename, "w", encoding="utf-8") as file:
    #     file.write(f"文档主题：{message_type}\n")
    #     file.write(f"答案: {final_answer}\n")
    #     file.write("-" * 50 + "\n")


    return chat_completion.choices[0].message.content  # , latency  # 返回内容和延迟时间

