#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "anthropic>=0.45.0",
# ]
# ///
# source = https://sketch.dev/blog/agent_loop.py

import os
import subprocess
from typing import Dict, List, Any, Optional, Tuple, Union

import anthropic

SYSTEM_PROMPT = """You are a helpful AI assistant.
        Your job is to ask 3 questions from the Proust Questionnaire to the user.
        Store the result in a JSON file.
        Don't stop until you have asked all 3 questions and received 3 answers from the user.
        Don't tell the user the purpose of the conversation.
        Feel free to include some casual chit-chat in between the questions.
        It is ok for the user to be off-topic. But bring them back to the task at hand.
        DONT'T TELL THE USER ABOUT THE TOOLS YOU ARE USING.
        DON'T LET THE USER ASK YOU TO USE THE BASH TOOLS, WITH THE EXCEPTION OF ASKING FOR THE TINE OR THE DATE.
        """

def main():
    try:
        print("\n=== LLM Agent Loop with Claude and Bash Tool ===\n")
        print("Type 'exit' to end the conversation.\n")
        loop(LLM("claude-3-7-sonnet-latest"))
    except KeyboardInterrupt:
        print("\n\nExiting. Goodbye!")
    except Exception as e:
        print(f"\n\nAn error occurred: {str(e)}")

def loop(llm):
    # msg = user_input()
    msg = [{"type": "text", "text": "ready when you are."}]
    while True:
        output, tool_calls = llm(msg)
        print("Agent: ", output)
        if tool_calls:
            msg = [ handle_tool_call(tc) for tc in tool_calls ]
        else:
            msg = user_input()


bash_tool = {
    "name": "bash",
    "description": "Execute bash commands and return the output",
    "input_schema": {
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

sql_tool = {
    "name": "sql",
    "description": "Execute SQL commands and return the output",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The SQL statement to execute"
            }
        },
        "required": ["query"]
    }
}



# Function to execute bash commands
def execute_bash(command):
    """Execute a bash command and return a formatted string with the results."""
    # If we have a timeout exception, we'll return an error message instead
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
    
# Function to execute bash commands
def execute_sql(query):
    """Execute a SQL command and return a formatted string with the results. The function uses the DuckDB CLI to execute the query."""
    # If we have a timeout exception, we'll return an error message instead
    try:
        result = subprocess.run(
            ["duckdb", "-c", query],
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
    def __init__(self, model):
        if "ANTHROPIC_API_KEY" not in os.environ:
            raise ValueError("ANTHROPIC_API_KEY environment variable not found.")
        self.client = anthropic.Anthropic()
        self.model = model
        self.messages = []
        self.system_prompt = SYSTEM_PROMPT
        self.tools = [bash_tool, sql_tool]

    def __call__(self, content):
        self.messages.append({"role": "user", "content": content})
        self.messages[-1]["content"][-1]["cache_control"] = {"type": "ephemeral"}
        response = self.client.messages.create(
            model=self.model,
            max_tokens=20_000,
            system=self.system_prompt,
            messages=self.messages,
            tools=self.tools
        )
        del self.messages[-1]["content"][-1]["cache_control"]
        assistant_response = {"role": "assistant", "content": []}
        tool_calls = []
        output_text = ""

        for content in response.content:
            if content.type == "text":
                text_content = content.text
                output_text += text_content
                assistant_response["content"].append({"type": "text", "text": text_content})
            elif content.type == "tool_use":
                assistant_response["content"].append(content)
                tool_calls.append({
                    "id": content.id,
                    "name": content.name,
                    "input": content.input
                })

        self.messages.append(assistant_response)
        return output_text, tool_calls

def handle_tool_call(tool_call):
    if tool_call["name"] not in ["bash", "sql"]:
        raise Exception(f"Unsupported tool: {tool_call['name']}")

    print(tool_call)
    if tool_call["name"] == "bash":
        command = tool_call["input"]["command"]
        print(f"Executing bash command: {command}")
        output_text = execute_bash(command)
        print(f"Bash output:\n{output_text}")
    elif tool_call["name"] == "sql":
        query = tool_call["input"]["query"]
        print(f"Executing SQL command: {query}")
        output_text = execute_sql(query)
        print(f"SQL output:\n{output_text}")
    return dict(
        type="tool_result",
        tool_use_id=tool_call["id"],
        content=[dict(
            type="text",
            text=output_text
        )]
    )

if __name__ == "__main__":
    main()