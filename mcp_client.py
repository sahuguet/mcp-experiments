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