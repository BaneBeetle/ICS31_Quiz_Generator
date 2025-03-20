import json
import openai
import os
from dotenv import load_dotenv

# Prompt used to ensure GPT returns JSON with specified quiz questions and answers
prompt = ("You are tasked with generating a realistic, exam-like, and engaging multiple-choice question for a given Python topic/subject. "
          "You will generate both the multiple choice question and 4 possible answers, with one being correct. The question will quiz a specific "
          "Python topic (e.g., mutability, printing, data structures). Generate a simple multiple choice question related to the inputted Python topic. "
          "The generated question must include an element of obvious related topics. Use Pythonic terminology (e.g., mutable, immutable, print, output) "
          "for the questions. Generate a JSON file containing 5 pairs of realistic exam-like questions and 4 corresponding answers with 1 being correct. "
          "The questions should be stated first then followed up by 4 potential answers multiple choice style (e.g., a: b: c: d:) each separated by '\\n'. "
          "After stating the question and the potential answers, identify the correct answer including the letter (e.g., a: b: c: d:). Each question must include elements "
          "of the given topic. Only provide the JSON format, do not provide any filler or other messages. Example: { 'questions': [{ \"input\": \"Mutability\", \"question\": "
          "\"Which of the following data types is mutable in Python? \\n\", \"choices\": \"a: Tuple\\nb: String\\nc: List\\nd: Integer\", \"correct\": \"c: List\" }, { "
          "\"input\": \"Printing\", \"question\": \"What will be the output of the following code? \\nprint('Hello' + 'World')\\n\", \"choices\": \"a: Hello World\\nb: HelloWorld\\n"
          "c: Hello+World\\nd: Error\", \"correct\": \"b: HelloWorld\" }, { \"input\": \"Data structures\", \"question\": \"What is the output of the following code? \\na = [1, 2, 3]\\n"
          "b = a\\nb.append(4)\\nprint(a)\\n\", \"choices\": \"a: [1, 2, 3]\\nb: [1, 2, 3, 4]\\nc: [4]\\nd: [1, 2]\", \"correct\": \"b: [1, 2, 3, 4]\" }, { \"input\": \"Functions\", "
          "\"question\": \"What is the correct syntax to define a function in Python? \\n\", \"choices\": \"a: def functionName[]:\\nb: def functionName:\\nc: functionName():\\n"
          "d: def functionName():\", \"correct\": \"d: def functionName():\" }, { \"input\": \"Loops\", \"question\": \"How many times will the following loop execute? \\nfor i in range(3):\\n"
          "\\tprint(i)\\n\", \"choices\": \"a: 1\\nb: 2\\nc: 3\\nd: 4\", \"correct\": \"c: 3\" }, { \"input\": \"Conditionals\", \"question\": \"Which of the following will evaluate as True in Python? "
          "\\n\", \"choices\": \"a: 5 > 10\\nb: 'apple' == 'Apple'\\nc: 7 != 5\\nd: 3 > 3\", \"correct\": \"c: 7 != 5\" }]}")


def generate_script(user_input):
    '''Function that simply calls GPT with the provided prompt in combination with user input specifying what topic they want.
    This is how we will generate the script to put in the videos as well as TTS'''

    dotenv_path = "C:\\Users\\lolly\\OneDrive\\Desktop\\Projects\\ICS31_QuizGenerator\\gptkey.env"
    load_dotenv(dotenv_path, override=True) # override set to true if API key updated
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY")) # Grab the API key from the .env file

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Generate 5 questions about this Python topic: {user_input}. ENSURE QUESTIONS DO NOT EXCEED 20 WORDS."
            }
        ]
    )
    response = json.loads(completion.choices[0].message.content)

    return response['questions']

if __name__ == "__main__":
    script = generate_script("Loops")
    print(script)
