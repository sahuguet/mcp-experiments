# About the Model Context Protocol

## What it is
It is a protocol between a client and a server to help with:
- service discovery
- servuice execution

where service includes:
* tools,
* resources,
* resource templates, and
* prompts.

You define a set capabilities available from a server; you can discover them from the client.

## In practice

We are using Python `FastMCP` which provide decorators.

I define a server with some capabilities

```
# file = server.py

from mcp.server.fastmcp import FastMCP

# Create an MCP server
mcp = FastMCP("Demo")


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

# Add an random number tool
@mcp.tool()
def random_number(min_value: int, max_value: int) -> int:
    """Return a random number"""
    import random
    return random.randint(min_value, max_value)

@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"

@mcp.resource("greeting://")
def get_greeting() -> str:
    """Get a personalized greeting"""
    return f"Hello, Arnaud!"

@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run()
```

I can now discover the server capabilities from the client. In this example, the client spawns the server first and then does the discovery and the execution.

```
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="python",  # Executable
    args=["server.py"],  # Optional command line arguments
    env=None,  # Optional environment variables
)

async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(
            read, write, sampling_callback=None
        ) as session:
            # Initialize the connection
            await session.initialize()

            # DISCOVERY

            # List available prompts
            prompts = await session.list_prompts()
            print(prompts)

            # List available resources
            resources = await session.list_resources()
            print(resources)

            # List available resources templates
            resources_templates = await session.list_resource_templates()
            print(resources_templates)

            # List available tools
            tools = await session.list_tools()
            print(tools)

            # EXECUTION 

            content, mime_type = await session.read_resource("greeting://")
            print(content, mime_type)

            
            result = await session.call_tool("random_number", arguments={"min_value": 1, "max_value": 100})
            print(result)

if __name__ == "__main__":
    import asyncio

    asyncio.run(run())
```

When you bring everything together
```
% python mcp_client.py
[05/02/25 00:41:13] INFO     Processing request of type ListPromptsRequest                                                                     server.py:534
meta=None nextCursor=None prompts=[Prompt(name='review_code', description='', arguments=[PromptArgument(name='code', description=None, required=True)])]
                    INFO     Processing request of type ListResourcesRequest                                                                   server.py:534
meta=None nextCursor=None resources=[Resource(uri=Url('greeting://'), name='greeting://', description=None, mimeType='text/plain', size=None, annotations=None), Resource(uri=Url('config://app'), name='config://app', description=None, mimeType='text/plain', size=None, annotations=None)]
                    INFO     Processing request of type ListResourceTemplatesRequest                                                           server.py:534
meta=None nextCursor=None resourceTemplates=[ResourceTemplate(uriTemplate='greeting://{name}', name='get_greeting', description='Get a personalized greeting', mimeType=None, annotations=None), ResourceTemplate(uriTemplate='users://{user_id}/profile', name='get_user_profile', description='Dynamic user data', mimeType=None, annotations=None)]
                    INFO     Processing request of type ListToolsRequest                                                                       server.py:534
meta=None nextCursor=None tools=[Tool(name='add', description='Add two numbers', inputSchema={'properties': {'a': {'title': 'A', 'type': 'integer'}, 'b': {'title': 'B', 'type': 'integer'}}, 'required': ['a', 'b'], 'title': 'addArguments', 'type': 'object'}, annotations=None), Tool(name='random_number', description='Return a random number', inputSchema={'properties': {'min_value': {'title': 'Min Value', 'type': 'integer'}, 'max_value': {'title': 'Max Value', 'type': 'integer'}}, 'required': ['min_value', 'max_value'], 'title': 'random_numberArguments', 'type': 'object'}, annotations=None)]
                    INFO     Processing request of type ReadResourceRequest                                                                    server.py:534
('meta', None) ('contents', [TextResourceContents(uri=Url('greeting://'), mimeType='text/plain', text='Hello, Arnaud!')])
                    INFO     Processing request of type CallToolRequest                                                                        server.py:534
meta=None content=[TextContent(type='text', text='51', annotations=None)] isError=False
````
## What's the big deal?

Why is
```
@mcp.tool()
def random_number(min_value: int, max_value: int) -> int:
    """Return a random number"""
    import random
    return random.randint(min_value, max_value)
```
so much better than the FastAPI equivalent?
```
@app.get("/random/{min_value}/{max_value}")
async def get_random_number(min_value: int, max_value: int) -> int:
    """Get a random number between min_value and max_value"""
    return random.randint(min_value, max_value)
```

Becasue MCP gives you 2 useful features for free
- a standardized service discovery
- schema generation in a format that is understood by LLMs, i.e. JsonSchema (see `python mcp_client.py` example above).

This is not necessarily hard to do (e.g. using FastAPI or similar library); but MCP offers standardized way of doing it.

## Even with MCP, enriching an LLM with a new tool a laborious manual process
You need to:
1. tell LLM about the tool
1. invike the LLM
1. intercept the tool calling
1. execute the tool
1. inject the result in the context
1. call the LLM

This looks like this
```
async def run_with_openai():

    # You define your LLM client
    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY")
    )
    
    # You define the server that you want to spawn. 
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Get available tools
            tools = await session.list_tools()
            print("Available tools:", tools)
            
            # Get the tool description from MCP
            random_number_tool = await session.get_tool("random_number")
            
            # Convert MCP tool description to OpenAI format
            tool_description = {
                "type": "function",
                "function": {
                    "name": random_number_tool.name,
                    "description": random_number_tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            param.name: {
                                "type": param.type,
                                "description": param.description
                            }
                            for param in random_number_tool.parameters
                        },
                        "required": [param.name for param in random_number_tool.parameters if param.required]
                    }
                }
            }
            
            # Example conversation with the model
            messages = [
                {"role": "system", "content": "You are a helpful assistant that can generate random numbers."},
                {"role": "user", "content": "I need a random number between 1 and 10 for a game."}
            ]
            
            # Get response from OpenAI
            response = await client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                tools=[tool_description],     # <----- YOU ADVERTISE THE TOOL TO THE LLM.
                tool_choice="auto"
            )
            
            # Process the response
            assistant_message = response.choices[0].message
            
            if assistant_message.tool_calls: # <---------- YOU INTERCEPT TOOL CALLING FROM THE LLM.
                tool_call = assistant_message.tool_calls[0]
                tool_args = json.loads(tool_call.function.arguments)
                
                # Call the MCP tool
                result = await session.call_tool(
                    "random_number",
                    arguments=tool_args
                )
                
                # Add the tool result to the conversation
                messages.append(assistant_message)
                messages.append({
                    "role": "tool",
                    "content": str(result),
                    "tool_call_id": tool_call.id
                })
                
                # Get final response from OpenAI
                final_response = await client.chat.completions.create(
                    model="gpt-4",
                    messages=messages
                )
```



## A few more details about LLM
- local servers
- remote servers (SSE)
- client configuration 

Here is my personal Claude Desktop config, that defines 2 local MCP server.
```
{
  "mcpServers": {
    "statebook-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/sahuguet/Dev/GitHub/statebook/statebook-mcp",
        "run",
        "statebook-mcp"
      ]
    },
    "Demo": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "/Users/sahuguet/Dev/GitHub/mcp-experiments/server.py"
      ]
    }
  }
}
```


## So, what's the big deal really?

1. it makes things marginally eaisier when you build both client and servers.
1. when building clients
   - you simply "mount" MCP servers, do the discovery and you are in business
   - each server behaves the same; each capability inside a given server behaves the same
   - you can trivially enrich your LLM-based application with new capabilities.
1. when building servers
   - you have a straightforward way of packaging your service as an MCP server.
   - all MCP clients (e.g. Cursor, Claude Desktop, etc.) can call you (either locally or remotely).


## Are we there yet?
- still early days
- huge risks because you are running 3rd party code on your local machine
- authentication is an afterthought
- how do you discover the best MCP servers?
- danger of context pollution when you add too many tools

## Resources
- https://github.com/modelcontextprotocol
- [MCPs, Gatekeepers, and the Future of AI](https://iamcharliegraham.substack.com/p/mcps-gatekeepers-and-the-future-of)
- [Smithery MCP "marketplace"](https://smithery.ai/)
