from dotenv import load_dotenv
from tavily import TavilyClient
import os

load_dotenv()

tavily = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)

topic = input("Enter your search topic: ")

response = tavily.search(
    query=topic,
    max_results=5
)

print("\nSearch Results:\n")

for result in response["results"]:
    print("Title:", result["title"])
    print("URL:", result["url"])
    print("Content:", result["content"][:300])
    print("-" * 50)