# Autonomous Research Agent

An AI-powered autonomous research agent that accepts a user topic, searches external web sources, filters relevant information, removes duplicate sources, and generates a structured research report in Markdown and PDF formats.

## Features

- Accepts any research topic from the user
- Uses an LLM to autonomously create research search queries
- Searches multiple external web sources using Tavily
- Performs parallel web searches
- Removes duplicate URLs
- Uses an LLM to analyze collected research information
- Generates structured research reports
- Exports reports as Markdown and PDF
- Stores previous research reports for future reference
- Uses OpenRouter as the primary LLM provider
- Uses Google Gemini models as a backup
- Handles temporary LLM/API failures with fallback logic

## Architecture

```text
User Topic
    ↓
OpenRouter LLM
    ↓
Autonomous Research Planner
    ↓
Dynamic Search Queries
    ↓
Parallel Tavily Web Search
    ↓
Duplicate URL Removal
    ↓
LLM Research Analysis
    ↓
Structured Research Report
    ↓
Markdown + PDF
    ↓
Research Memory

## LLM Fallback

OpenRouter (Primary)
        ↓
   If it fails
        ↓
Gemini 3.8 Flash
        ↓
Gemini 3.7 Flash
        ↓
Gemini 3.6 Flash
        ↓
Gemini 3.5 Flash

The Gemini backup models are tried sequentially with a delay between attempts.

## Report Structure

The generated report contains:

Key Points
Important Findings
References / Sources
Actionable Insights

The report is designed to be concise, evidence-based, and focused on the requested research topic.

## Technologies Used

Python
OpenRouter API
Google Gemini API
Tavily Search API
ReportLab
python-dotenv
OpenAI Python SDK

## Project Structure

AUTONOMOUS-RESEARCH-AGENT/
│
├── main.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
│
├── research_report.md
└── research_report.pdf

## Installation

1. Clone the repository

git clone <YOUR_GITHUB_REPOSITORY_URL>
cd AUTONOMOUS-RESEARCH-AGENT

2. Create a virtual environment

py -m venv venv

3. Activate the virtual environment

Windows:
venv\Scripts\activate

4. Install dependencies

pip install -r requirements.txt

## API Keys

Create a .env file in the project root:

GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
OPENROUTER_API_KEY=your_openrouter_api_key

Do not commit the .env file to GitHub.

## How to Run

Run the application using:

py main.py

Enter a research topic when prompted.

Example:

Impact of Artificial Intelligence on Software Development

The agent will:

Understand the research topic.
Generate search queries autonomously.
Search external sources.
Collect relevant information.
Remove duplicate sources.
Analyze the collected information.
Generate the final research report.
Save the report as Markdown and PDF.

## Output

The application generates:

research_report.md
research_report.pdf

The PDF report is formatted as a multi-page research document containing key points, important findings, references, and actionable insights.

## Error Handling

The application includes fallback handling for LLM failures.

OpenRouter is used as the primary LLM provider. If OpenRouter fails, the application switches to Gemini backup models sequentially.

Temporary API failures are handled without immediately terminating the entire research workflow.

## Future Improvements

Support additional search providers
Improve source quality ranking
Add richer research memory
Add more export formats
Add a web-based user interface
Improve source credibility evaluation
Support longer multi-step research workflows

## Author

Developed as an Autonomous AI Research Agent project for an AI Automation Engineering assessment.