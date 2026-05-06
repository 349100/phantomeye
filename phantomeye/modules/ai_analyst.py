"""
PhantomEye — AI Analyst Module
Uses Claude claude-sonnet-4-20250514 to synthesize raw OSINT data into
actionable intelligence reports.
"""

import json
from typing import Optional

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are PhantomEye's AI Analyst — an expert OSINT intelligence officer.
Your task is to synthesize raw reconnaissance data into a structured, actionable intelligence report.

Guidelines:
- Be concise but comprehensive
- Highlight anomalies, risks, and notable findings
- Identify patterns across the collected data
- Suggest follow-up investigation vectors where appropriate
- Flag any indicators of compromise (IoC) or suspicious patterns
- Keep the report professional and objective
- Format your response in clear sections using markdown
- Never fabricate data; only analyze what was provided
- Include an "Intelligence Summary" section at the top with key findings
- End with "Recommended Next Steps" listing specific follow-up actions

Ethical reminder: This tool is for authorized security research, penetration testing,
and legitimate OSINT investigations only. Always operate within legal boundaries."""


PROMPT_TEMPLATES = {
    "username": """Analyse the following username OSINT data for target: {target}

Raw data:
{data}

Provide:
1. **Intelligence Summary** — Key findings in 3-5 bullet points
2. **Platform Footprint** — Analysis of where the user is active
3. **Digital Behaviour Pattern** — What the presence pattern reveals
4. **Risk Indicators** — Any concerning findings
5. **Recommended Next Steps** — Specific follow-up actions""",

    "email": """Analyse the following email address OSINT data for target: {target}

Raw data:
{data}

Provide:
1. **Intelligence Summary** — Key findings in 3-5 bullet points
2. **Breach Analysis** — Assessment of data breach exposure
3. **Account Legitimacy** — Is this a real, active account or throwaway?
4. **Social Footprint** — What the email's online presence reveals
5. **Risk Assessment** — Severity of any discovered issues
6. **Recommended Next Steps** — Specific follow-up actions""",

    "ip": """Analyse the following IP address OSINT data for target: {target}

Raw data:
{data}

Provide:
1. **Intelligence Summary** — Key findings in 3-5 bullet points
2. **Infrastructure Assessment** — What this IP represents (hosting, corporate, residential, etc.)
3. **Geopolitical Context** — Location and jurisdiction analysis
4. **Threat Indicators** — Abuse scores, proxy/VPN usage, malicious patterns
5. **Attack Surface** — Open ports, services, and vulnerabilities (if Shodan data present)
6. **Recommended Next Steps** — Specific follow-up actions""",

    "domain": """Analyse the following domain OSINT data for target: {target}

Raw data:
{data}

Provide:
1. **Intelligence Summary** — Key findings in 3-5 bullet points
2. **Domain Maturity** — Age, history, and legitimacy assessment
3. **Infrastructure Overview** — Hosting, CDN, technology stack
4. **Security Posture** — SSL, DNS security, headers analysis
5. **Technology Fingerprint** — What the tech stack reveals about the target
6. **Subdomains of Interest** — Notable subdomains discovered
7. **Recommended Next Steps** — Specific follow-up actions""",

    "phone": """Analyse the following phone number OSINT data for target: {target}

Raw data:
{data}

Provide:
1. **Intelligence Summary** — Key findings in 3-5 bullet points
2. **Number Attribution** — Region, carrier, line type analysis
3. **Legitimacy Assessment** — Is this a VoIP, burner, or real number?
4. **OSINT Vectors** — Best approaches for further investigation
5. **Recommended Next Steps** — Specific follow-up actions""",
}


class AIAnalyst:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        }

    def analyse(self, target_type: str, target: str, data: dict) -> str:
        template = PROMPT_TEMPLATES.get(target_type, PROMPT_TEMPLATES["username"])
        prompt = template.format(
            target=target,
            data=json.dumps(data, indent=2, default=str)
        )

        payload = {
            "model":      MODEL,
            "max_tokens": 2048,
            "system":     SYSTEM_PROMPT,
            "messages":   [{"role": "user", "content": prompt}],
        }

        with Progress(SpinnerColumn(), TextColumn("[magenta]AI analyst working…"),
                      console=console, transient=True) as prog:
            prog.add_task("", total=None)
            try:
                resp = requests.post(
                    ANTHROPIC_API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=60,
                )

                if resp.status_code == 200:
                    result = resp.json()
                    return result["content"][0]["text"]

                elif resp.status_code == 401:
                    return "❌ Invalid Anthropic API key. Run: phantomeye config --anthropic-key YOUR_KEY"

                elif resp.status_code == 429:
                    return "❌ Anthropic rate limit exceeded. Please wait and retry."

                else:
                    return f"❌ AI API error: HTTP {resp.status_code} — {resp.text[:200]}"

            except requests.exceptions.Timeout:
                return "❌ AI analysis timed out. The API did not respond within 60 seconds."

            except Exception as e:
                return f"❌ AI analysis failed: {str(e)}"
