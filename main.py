from dotenv import load_dotenv
from tavily import TavilyClient
from google import genai
from openai import OpenAI
import os
import time
import re
import json
from types import SimpleNamespace
from xml.sax.saxutils import escape
from concurrent.futures import ThreadPoolExecutor

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


# ---------------------------------------------------------
# Load environment variables
# ---------------------------------------------------------

load_dotenv()


# ---------------------------------------------------------
# Tavily - Web Search
# ---------------------------------------------------------

tavily = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)


# ---------------------------------------------------------
# Gemini - AI Backup
# ---------------------------------------------------------

gemini = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

# ---------------------------------------------------------
# OpenRouter - Primary LLM
# ---------------------------------------------------------

openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# ---------------------------------------------------------
# LLM helper: OpenRouter primary + Gemini backup
# ---------------------------------------------------------

def generate_with_fallback(prompt, purpose="LLM"):

    # -----------------------------------------------------
    # Primary LLM: OpenRouter
    # -----------------------------------------------------

    try:

        print(f"\n{purpose} | OpenRouter")

        response = openrouter.chat.completions.create(
            model="openrouter/free",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        content = response.choices[0].message.content

        if content and content.strip():

            print("\nOpenRouter succeeded.")

            return SimpleNamespace(
                text=content
            )

        raise ValueError("OpenRouter returned empty content.")

    except Exception as e:

        print(f"\nOpenRouter failed: {e}")
        print("Switching to Gemini backup...")

    # -----------------------------------------------------
    # Backup LLM: Gemini
    # One attempt per model + 30 second wait
    # -----------------------------------------------------

    models = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash"
    ]

    for model in models:

        try:

            print(f"\n{purpose} | Gemini: {model}")

            response = gemini.models.generate_content(
                model=model,
                contents=prompt
            )

            if response.text and response.text.strip():

                print(f"\nGemini {model} succeeded.")

                return response

            raise ValueError("Gemini returned empty content.")

        except Exception as e:

            error = str(e)

            print(f"{purpose} | Gemini {model} failed: {error}")

            if model != models[-1]:

                print("Waiting 30 seconds before trying next model...")
                time.sleep(30)

    print("\nAll LLM models failed.")

    return None


# ---------------------------------------------------------
# Research Memory
# ---------------------------------------------------------

MEMORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "search_memory.json"
)


def load_memory():

    if not os.path.exists(MEMORY_FILE):

        return []

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return []


def save_memory(topic, queries):

    memory = load_memory()

    memory.append({
        "topic": topic,
        "queries": queries
    })

    with open(
        MEMORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            memory,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(
        f"\nMemory saved to: {MEMORY_FILE}"
    )


# ---------------------------------------------------------
# Autonomous Research Planner
# ---------------------------------------------------------

def generate_research_plan(topic):

    prompt = f"""
You are an autonomous research planning agent.

Research Topic:
{topic}

Your job is to decide how this topic should be researched.

Create exactly 3 research searches.

For each search, decide:

1. A useful and specific search query.
2. The most appropriate external source domains for that query.

Choose source domains based on the actual research topic.

Examples:

- Technical topics:
  official documentation, standards, technical organizations

- Cybersecurity:
  CISA, NIST, official security documentation

- Cloud computing:
  AWS, Microsoft Azure, Google Cloud official documentation

- Scientific topics:
  research organizations, universities, scientific sources

- Government or policy topics:
  official government websites and trusted organizations

- General topics:
  reliable news, educational, government or industry sources

Do not blindly use the example domains.
Select domains that are actually appropriate for the given topic.

Return ONLY valid JSON in this exact structure:

{{
    "searches": [
        {{
            "query": "search query 1",
            "domains": ["example.com"]
        }},
        {{
            "query": "search query 2",
            "domains": ["example.com"]
        }},
        {{
            "query": "search query 3",
            "domains": ["example.com"]
        }}
    ]
}}

Important:
- Exactly 3 searches
- Each search must contain a query
- Domains must be relevant to the query
- Do not add explanations
- Do not use Markdown
"""

    response = generate_with_fallback(
        prompt,
        purpose="Autonomous Research Planner"
    )

    if response is None:

        print(
            "\nUnable to generate research plan."
        )

        return []

    try:

        plan_text = response.text.strip()

        # Remove Markdown code fences if Gemini adds them
        plan_text = re.sub(
            r"```json|```",
            "",
            plan_text
        ).strip()

        plan = json.loads(plan_text)

        searches = plan.get(
            "searches",
            []
        )

        # Validate the generated structure
        valid_searches = []

        for search in searches:

            if not isinstance(search, dict):

                continue

            query = search.get(
                "query",
                ""
            ).strip()

            domains = search.get(
                "domains",
                []
            )

            if not isinstance(domains, list):

                domains = []

            domains = [
                domain.strip()
                for domain in domains
                if isinstance(domain, str)
                and domain.strip()
            ]

            if query:

                valid_searches.append({
                    "query": query,
                    "domains": domains
                })

        return valid_searches[:3]

    except Exception as e:

        print(
            f"\nResearch plan parsing error: {e}"
        )

        return []


# ---------------------------------------------------------
# Get research topic from user
# ---------------------------------------------------------

topic = input(
    "Enter your research topic: "
)


# ---------------------------------------------------------
# Load previous research memory
# ---------------------------------------------------------

previous_memory = load_memory()

if previous_memory:

    print(
        "\nPrevious Research History:"
    )

    for item in previous_memory[-5:]:

        print(
            "-",
            item["topic"]
        )

else:

    print(
        "\nNo previous research history found."
    )


# ---------------------------------------------------------
# Step 1: Autonomous Research Planning
# ---------------------------------------------------------

research_plan = generate_research_plan(
    topic
)


if not research_plan:

    print(
        "\nNo research plan was generated."
    )

    exit()


# ---------------------------------------------------------
# Save successful research queries to memory
# ---------------------------------------------------------

print(
    "\nDEBUG: Saving research memory..."
)


queries = [
    search["query"]
    for search in research_plan
]


save_memory(
    topic,
    queries
)


# ---------------------------------------------------------
# Display Autonomous Research Plan
# ---------------------------------------------------------

print(
    "\nAutonomous Research Plan:"
)

for index, search in enumerate(
    research_plan,
    start=1
):

    print(
        f"\nSearch {index}:"
    )

    print(
        "Query:",
        search["query"]
    )

    if search["domains"]:

        print(
            "Selected Sources:",
            ", ".join(
                search["domains"]
            )
        )

    else:

        print(
            "Selected Sources: Tavily general web search"
        )


# ---------------------------------------------------------
# Step 2: Parallel Web Search
# ---------------------------------------------------------

all_results = []


def search_web(search_item):

    query = search_item["query"]

    domains = search_item.get(
        "domains",
        []
    )

    print(
        f"\nSearching: {query}"
    )

    if domains:

        print(
            "Selected sources:",
            ", ".join(domains)
        )

    try:

        search_parameters = {
            "query": query,
            "max_results": 4
        }

        # Only apply domain filtering when
        # Gemini selected specific domains.
        if domains:

            search_parameters[
                "include_domains"
            ] = domains

        search_response = tavily.search(
            **search_parameters
        )

        return search_response.get(
            "results",
            []
        )

    except Exception as e:

        print(
            f"Tavily search error: {e}"
        )

        return []


# Run the research searches in parallel
with ThreadPoolExecutor(
    max_workers=3
) as executor:

    results = executor.map(
        search_web,
        research_plan
    )

    for result in results:

        all_results.extend(
            result
        )


# ---------------------------------------------------------
# Step 3: Remove Duplicate Sources
# ---------------------------------------------------------

sources = ""

seen_urls = set()


for result in all_results:

    url = result.get(
        "url",
        ""
    )

    if not url:

        continue

    # Skip duplicate URLs
    if url in seen_urls:

        continue

    seen_urls.add(url)

    title = result.get(
        "title",
        "Untitled Source"
    )

    content = result.get(
    "content",
    ""
)

# Limit source content to keep Gemini requests lightweight
    content = content[:2500]

    sources += f"""
Title: {title}
URL: {url}
Content: {content}
---
"""


# ---------------------------------------------------------
# Check whether web search returned results
# ---------------------------------------------------------

if not sources.strip():

    print(
        "\nNo useful web search results were found."
    )

    exit()


# ---------------------------------------------------------
# Step 4: Ask the LLM to Analyze Sources
# ---------------------------------------------------------

prompt = f"""
You are an autonomous research assistant.

Research Topic:
{topic}

Here are the web search results:

{sources}

Your task is to analyze the provided sources and create a
structured research report.

Before writing the report, identify which sources are relevant
to the research topic.

Ignore sources that are:

- unrelated
- too general
- duplicated
- not useful for answering the research topic

Use only relevant sources for the final report.

Do not mention ignored sources.

Based ONLY on the information provided in the sources:

1. Give a clear, detailed summary of the research topic using the evidence collected.
2. Provide 8-12 substantial key points. Each point should explain the idea, not just name it.
3. Provide 6-10 important findings with supporting facts, comparisons, measurements, dates, or study observations when available.
4. Provide 5-8 actionable insights when they are applicable to the topic.
5. List 8-12 of the most relevant source URLs actually used in the report.

The final report should be approximately 1200-1600 words so that the exported PDF is a detailed 3-4 page report.
Use the available source evidence to add useful detail rather than repeating the same sentence in different ways.
If the sources do not contain enough evidence for a specific claim, do not invent it.

Structure the final answer clearly using headings and bullet points.
Use ONLY this structure:

# Research Summary
Write 2-3 detailed paragraphs introducing the topic and synthesizing the research evidence.

## Key Points
Provide 8-12 detailed bullet points covering the major aspects found across the relevant sources.

## Important Findings
Provide 6-10 detailed bullet points. Include quantitative results, study observations, technical findings, benefits, limitations, risks, or implementation considerations when the sources support them.

## References / Sources
List 8-12 relevant source URLs used in the report. Do not invent URLs.

## Actionable Insights
Provide 5-8 practical bullet points based directly on the research evidence.

Keep the report focused, professional, readable, and evidence-based.
Do not add extra sections.
Do not add filler, unsupported claims, or repeated information.
"""


# ---------------------------------------------------------
# Step 5: Generate Final Research Report
# ---------------------------------------------------------

response = generate_with_fallback(
    prompt,
    purpose="Final Research Report"
)


if response is None:

    print(
        "\nUnable to generate the research report right now."
    )

    exit()


# ---------------------------------------------------------
# Step 6: Display Final Report
# ---------------------------------------------------------

print(
    "\n" + "=" * 60
)

print(
    "AUTONOMOUS RESEARCH REPORT"
)

print(
    "=" * 60
)

print(
    response.text
)


# ---------------------------------------------------------
# Step 7: Save Report as Markdown
# ---------------------------------------------------------

with open(
    "research_report.md",
    "w",
    encoding="utf-8"
) as file:

    file.write(
        response.text
    )


print(
    "\nResearch report saved as research_report.md"
)


# ---------------------------------------------------------
# Step 8: Save Report as PDF
# ---------------------------------------------------------

styles = getSampleStyleSheet()

# Custom PDF typography for a clean, readable 3-4 page report
styles["Title"].fontSize = 20
styles["Title"].leading = 24
styles["Title"].spaceAfter = 14
styles["Heading1"].fontSize = 15
styles["Heading1"].leading = 19
styles["Heading1"].spaceBefore = 12
styles["Heading1"].spaceAfter = 8
styles["Heading2"].fontSize = 13
styles["Heading2"].leading = 17
styles["Heading2"].spaceBefore = 10
styles["Heading2"].spaceAfter = 6
styles["BodyText"].fontSize = 11
styles["BodyText"].leading = 16
styles["BodyText"].spaceAfter = 7

pdf = SimpleDocTemplate(
    "research_report.pdf",
    pagesize=A4,
    rightMargin=50,
    leftMargin=50,
    topMargin=45,
    bottomMargin=45
)


story = []


# ---------------------------------------------------------
# PDF Title
# ---------------------------------------------------------

story.append(
    Paragraph(
        "AUTONOMOUS RESEARCH REPORT",
        styles["Title"]
    )
)


story.append(
    Spacer(1, 10)
)


# ---------------------------------------------------------
# Research Topic
# ---------------------------------------------------------

story.append(
    Paragraph(
        f"<b>Research Topic:</b> {escape(topic)}",
        styles["Heading2"]
    )
)


story.append(
    Spacer(1, 20)
)


# ---------------------------------------------------------
# Convert Markdown-style Report into PDF
# ---------------------------------------------------------

for line in response.text.split(
    "\n"
):

    line = line.strip()


    # Empty line
    if not line:

        story.append(
            Spacer(1, 8)
        )

        continue


    # Horizontal separator
    if line == "---":

        story.append(
            Spacer(1, 10)
        )

        continue


    # Remove Markdown links
    line = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r"\1 (\2)",
        line
    )


    # Remove inline code backticks
    line = line.replace(
        "`",
        ""
    )


    # Main heading
    if line.startswith(
        "# "
    ):

        text = escape(
            line[2:]
        )

        text = re.sub(
            r"\*\*(.*?)\*\*",
            r"<b>\1</b>",
            text
        )

        story.append(
            Paragraph(
                text,
                styles["Title"]
            )
        )


    # Heading 2
    elif line.startswith(
        "## "
    ):

        text = escape(
            line[3:]
        )

        text = re.sub(
            r"\*\*(.*?)\*\*",
            r"<b>\1</b>",
            text
        )

        story.append(
            Paragraph(
                text,
                styles["Heading1"]
            )
        )


    # Heading 3
    elif line.startswith(
        "### "
    ):

        text = escape(
            line[4:]
        )

        text = re.sub(
            r"\*\*(.*?)\*\*",
            r"<b>\1</b>",
            text
        )

        story.append(
            Paragraph(
                text,
                styles["Heading2"]
            )
        )


    # Bullet using *
    elif line.startswith(
        "* "
    ):

        text = escape(
            line[2:]
        )

        text = re.sub(
            r"\*\*(.*?)\*\*",
            r"<b>\1</b>",
            text
        )

        story.append(
            Paragraph(
                "• " + text,
                styles["BodyText"]
            )
        )


    # Bullet using -
    elif line.startswith(
        "- "
    ):

        text = escape(
            line[2:]
        )

        text = re.sub(
            r"\*\*(.*?)\*\*",
            r"<b>\1</b>",
            text
        )

        story.append(
            Paragraph(
                "• " + text,
                styles["BodyText"]
            )
        )


    # Normal paragraph
    else:

        text = escape(
            line
        )

        text = re.sub(
            r"\*\*(.*?)\*\*",
            r"<b>\1</b>",
            text
        )

        story.append(
            Paragraph(
                text,
                styles["BodyText"]
            )
        )


# ---------------------------------------------------------
# Build PDF
# ---------------------------------------------------------

pdf.build(
    story
)


print(
    "\nResearch report saved as research_report.pdf"
)