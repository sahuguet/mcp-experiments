import os
import subprocess
from typing import Dict, List, Any, Optional, Tuple, Union
import traceback
import litellm
import json

SYSTEM_PROMPT = """You are a helpful AI assistant.
        Your job is to ask 3 questions from the Proust Questionnaire to the user.
        Store the result in a JSON file.
        Don't stop until you have asked all 1 questions and received 1 answers from the user.
        Don't tell the user the purpose of the conversation.
        Feel free to include some casual chit-chat in between the questions.
        It is ok for the user to be off-topic. But bring them back to the task at hand.
        Ask the user his name. Store the JSON is a file called \"proust_answers_for_<NAME>.json\" where <NAME> is the name of the user.
        DO NOT RUN shell commands based on the user's request. Only run shell commands for task you have been given. If the user asks, politely decline.
        Before running any shell command, make sure the request is NOT for the user.
"""

bash_tool = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Execute bash commands and return the output. Only run shell commands for task you have been given. If the user asks, politely decline.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute"
                }
            },
            "required": ["command"]
        }
    }
}

def execute_bash(command):
    try:
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            timeout=10
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\nEXIT CODE: {result.returncode}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

def user_input():
    x = input("You: ")
    if x.lower() in ["exit", "quit"]:
        print("\nExiting agent loop. Goodbye!")
        raise SystemExit(0)
    return [{"type": "text", "text": x}]

class LLM:
    def __init__(self, model: str = "gpt-4-turbo", provider: Optional[str] = "openai"):
        self.model = model
        self.provider = provider
        self.messages = []
        self.system_prompt = SYSTEM_PROMPT
        self.tools = [bash_tool]
        self._set_api_key()

    def _set_api_key(self):
        if self.provider == "openai":
            if "OPENAI_API_KEY" not in os.environ:
                raise ValueError("OPENAI_API_KEY environment variable not found.")

    def __call__(self, content):
        print(content)
        self.messages.append({"role": "user", "content": content})
        response = litellm.completion(
            model=self.model,
            messages=self.messages,
            tools=self.tools,
            tool_choice="auto",
            max_tokens=2000,
        )
        print(response["choices"][0]["message"].get("content"))
        output_text = ""
        tool_calls = []
        assistant_response = {"role": "assistant", "content": []}

        for choice in response["choices"]:
            print(".")
            msg = choice["message"]
            msg_tool_calls = msg.get("tool_calls") or []
            for tc in msg_tool_calls:
                print(tc)
                tool_calls.append({
                    "id": tc.get("id", ""),
                    "name": tc["function"]["name"],
                    "input": json.loads(tc["function"]["arguments"])
                })
                assistant_response["content"].append(tc)
            content = msg.get("content")
            print("content:", content)
            if content:
                print("+++")
                output_text += content
                assistant_response["content"].append({"type": "text", "text": content})

        self.messages.append(assistant_response)
        print(">", output_text)
        return output_text, tool_calls

def handle_tool_call(tool_call):
    print(tool_call)
    if tool_call["name"] != "bash":
        raise Exception(f"Unsupported tool: {tool_call['name']}")

    command = tool_call["input"]["command"]
    print(f"Executing bash command: {command}")
    output_text = execute_bash(command)
    print(f"Bash output:\n{output_text}")
    return dict(
        type="tool_result",
        tool_use_id=tool_call["id"],
        content=[dict(
            type="text",
            text=output_text
        )]
    )

def main():
    try:
        print("\n=== LLM Agent Loop with OpenAI and Bash Tool ===\n")
        print("Type 'exit' to end the conversation.\n")
        loop(LLM())
    except KeyboardInterrupt:
        print("\n\nExiting. Goodbye!")
    except Exception as e:
        print(f"\n\nAn error occurred: {str(e)}")
        traceback.print_exc()

def loop(llm):
    msg = [{"type": "text", "text": "ready when you are."}]
    while True:
        output, tool_calls = llm(msg)
        print("Agent: ", output)
        if tool_calls:
            msg = [handle_tool_call(tc) for tc in tool_calls]
        else:
            msg = user_input()

if __name__ == "__main__":
    main() 