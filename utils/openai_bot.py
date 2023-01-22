from config import openai_token
import openai
from typing import Union


class ChatGPT:
    completion = None

    def __init__(self):
        openai.api_key = openai_token
        self.completion = openai.Completion

    def get_answer(self, question) -> Union[str, None]:
        response = self.completion.create(
            model="text-davinci-003",
            prompt=question,
            temperature=0.9,
            max_tokens=1000,
            top_p=1,
            frequency_penalty=0.0,
            presence_penalty=0.6,
            stop=[" Human:", " AI:"]
        )

        if 'choices' in response and len(response['choices']) > 0:
            return response['choices'][0]['text'].strip()


if __name__ == '__main__':
    chat_1 = ChatGPT()
    answer_1_1 = chat_1.get_answer('Сколько звёзд на небе?')
    print(answer_1_1)

