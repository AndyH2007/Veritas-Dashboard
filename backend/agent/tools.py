from dotenv import load_dotenv
from agents import Agent, Runner, WebSearchTool
import asyncio

load_dotenv()

agent = Agent(
    name="Assistant",
    tools=[
        WebSearchTool(),
    ],
)

async def main():
    result = await Runner.run(agent, "What is the current stock price of APPL?")
    print(result.final_output)

if __name__ == "__main__":
    print("...")
    asyncio.run(main())