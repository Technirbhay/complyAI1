import os

from dotenv import load_dotenv
from google import genai
from openai import OpenAI
from groq import Groq

from .schemas import ComplianceReport, Finding


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ============================================================
# CLIENTS
# ============================================================

groq_client = None
openai_client = None
gemini_client = None


if GROQ_API_KEY:
    groq_client = Groq(
        api_key=GROQ_API_KEY
    )


if OPENAI_API_KEY:
    openai_client = OpenAI(
        api_key=OPENAI_API_KEY
    )


if GEMINI_API_KEY:
    gemini_client = genai.Client(
        api_key=GEMINI_API_KEY
    )


if not GROQ_API_KEY and not OPENAI_API_KEY and not GEMINI_API_KEY:
    raise RuntimeError(
        "No AI API key configured. "
        "Add GROQ_API_KEY, OPENAI_API_KEY or GEMINI_API_KEY "
        "to backend/.env"
    )


# ============================================================
# MODELS
# ============================================================

GROQ_MODEL = "openai/gpt-oss-120b"
OPENAI_MODEL = "gpt-5.6-luna"
GEMINI_MODEL = "gemini-3.8-flash"


# ============================================================
# GROQ FREE-TIER CHUNK SETTINGS
# ============================================================

# Keep each request comfortably below Groq's 8K TPM limit.
CHUNK_SIZE = 12000

# Small overlap helps avoid cutting a clause exactly
# at a chunk boundary.
CHUNK_OVERLAP = 500


# ============================================================
# FRAMEWORK RULES
# ============================================================

FRAMEWORK_RULES = {

    "GDPR": """
Focus on:
- lawful processing
- purpose limitation
- data minimization
- retention
- data subject rights
- security
- international transfers
- sharing with processors/third parties
- breach handling
""",

    "HIPAA": """
Focus on:
- protected health information
- minimum necessary access
- safeguards
- disclosure restrictions
- business associates
- security incidents
- privacy requirements
""",

    "SOC 2": """
Focus on:
- access controls
- security
- availability
- confidentiality
- processing integrity
- change management
- monitoring
- incident response
- audit evidence
""",

    "ISO 27001": """
Focus on:
- information security controls
- access management
- asset management
- risk management
- incident management
- supplier security
- business continuity
- logging and monitoring
""",

    "CCPA": """
Focus on:
- consumer rights
- collection and use of personal information
- disclosure
- selling/sharing personal information
- deletion
- correction
- opt-out requirements
- sensitive personal information
"""
}


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are ComplyAI, an enterprise compliance analysis agent.

Analyze the supplied document against the selected compliance framework.

Rules:
1. Do NOT invent clauses or evidence.
2. Use only the supplied document.
3. Distinguish compliant, non_compliant and needs_review.
4. Give precise document citations.
5. If evidence is insufficient, use needs_review.
6. Do not claim legal certification.
7. This is compliance assistance, not legal advice.
8. Identify concrete compliance risks.
9. Suggest practical compliant alternative wording.
10. Be conservative when evidence is insufficient.
11. Return meaningful findings only.
12. Keep findings concise and traceable.
"""


# ============================================================
# BUILD PROMPT
# ============================================================

def build_prompt(
    document_name: str,
    framework: str,
    document_text: str,
    chunk_number: int = 1,
    total_chunks: int = 1,
) -> str:

    rules = FRAMEWORK_RULES.get(
        framework,
        FRAMEWORK_RULES["GDPR"]
    )

    return f"""
SELECTED FRAMEWORK:
{framework}

FRAMEWORK-SPECIFIC FOCUS:
{rules}

DOCUMENT NAME:
{document_name}

DOCUMENT PART:
{chunk_number} of {total_chunks}

DOCUMENT CONTENT:
----------------
{document_text}
----------------

Analyze this part of the document against the selected compliance framework.

For every meaningful compliance issue:

- quote or summarize the relevant clause
- identify the requirement
- classify status
- assign severity
- explain risk
- propose compliant replacement language
- provide document citation

STATUS VALUES:
- compliant
- non_compliant
- needs_review

SEVERITY VALUES:
- LOW
- MEDIUM
- HIGH
- CRITICAL

Calculate a compliance score from 0-100 for this document part.

IMPORTANT:
- Do not invent evidence.
- Use only information supported by the supplied document part.
- If evidence is unclear, use needs_review.
- Keep findings concise and traceable.
- Do not provide legal certification.
- Do not provide legal advice.

Return ONLY valid JSON matching the ComplianceReport schema.
"""


# ============================================================
# DOCUMENT CHUNKING
# ============================================================

def split_document(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
):
    """
    Split large documents into smaller overlapping chunks.

    This prevents Groq's free-tier TPM limit from being exceeded
    while still allowing ComplyAI to analyze the whole document.
    """

    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = min(
            start + chunk_size,
            text_length
        )

        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - overlap

    return chunks


# ============================================================
# STRICT JSON SCHEMA
# ============================================================

def make_strict_schema(schema):

    if not isinstance(schema, dict):
        return schema

    if schema.get("type") == "object":

        schema["additionalProperties"] = False

        properties = schema.get(
            "properties",
            {}
        )

        if properties:
            schema["required"] = list(
                properties.keys()
            )

        for value in properties.values():
            make_strict_schema(value)

    if "items" in schema:
        make_strict_schema(
            schema["items"]
        )

    if "$defs" in schema:
        for definition in schema["$defs"].values():
            make_strict_schema(
                definition
            )

    if "anyOf" in schema:
        for item in schema["anyOf"]:
            make_strict_schema(item)

    if "oneOf" in schema:
        for item in schema["oneOf"]:
            make_strict_schema(item)

    if "allOf" in schema:
        for item in schema["allOf"]:
            make_strict_schema(item)

    return schema


# ============================================================
# ERROR CLASSIFICATION
# ============================================================

def classify_provider_error(exc):

    error_text = str(exc).lower()

    if (
        "429" in error_text
        or "rate limit" in error_text
        or "too_many_requests" in error_text
        or "quota" in error_text
        or "insufficient_quota" in error_text
        or "credit_balance_exhausted" in error_text
        or "tokens per minute" in error_text
        or "rate_limit_exceeded" in error_text
    ):
        return "RATE_LIMIT"

    if (
        "503" in error_text
        or "service unavailable" in error_text
        or "temporarily unavailable" in error_text
        or "timeout" in error_text
    ):
        return "TEMPORARY"

    if (
        "404" in error_text
        or "not_found" in error_text
        or "model not found" in error_text
    ):
        return "MODEL_UNAVAILABLE"

    return "OTHER"


# ============================================================
# GROQ
# ============================================================

def analyze_with_groq(
    prompt: str,
) -> ComplianceReport:

    if not groq_client:
        raise RuntimeError(
            "Groq API key is not configured."
        )

    print(
        f"[AI ROUTER] Trying Groq: {GROQ_MODEL}"
    )

    try:

        groq_schema = make_strict_schema(
            ComplianceReport.model_json_schema()
        )

        response = groq_client.chat.completions.create(

            model=GROQ_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],

            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "compliance_report",
                    "strict": True,
                    "schema": groq_schema,
                },
            },

            temperature=0.1,

            max_tokens=3500,
        )

        raw = response.choices[0].message.content

        if not raw:
            raise RuntimeError(
                "Groq returned an empty response."
            )

        report = ComplianceReport.model_validate_json(
            raw
        )

        print(
            "[AI ROUTER] Groq SUCCESS"
        )

        return report

    except Exception as exc:

        print(
            "[AI ROUTER] Groq FAILED:",
            str(exc)
        )

        category = classify_provider_error(
            exc
        )

        raise RuntimeError(
            f"GROQ_{category}: {exc}"
        )


# ============================================================
# OPENAI
# ============================================================

def analyze_with_openai(
    prompt: str,
) -> ComplianceReport:

    if not openai_client:
        raise RuntimeError(
            "OpenAI API key is not configured."
        )

    print(
        f"[AI ROUTER] Trying OpenAI: {OPENAI_MODEL}"
    )

    try:

        openai_schema = make_strict_schema(
            ComplianceReport.model_json_schema()
        )

        response = openai_client.responses.create(

            model=OPENAI_MODEL,

            input=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],

            text={
                "format": {
                    "type": "json_schema",
                    "name": "compliance_report",
                    "description": (
                        "Structured ComplyAI compliance report"
                    ),
                    "schema": openai_schema,
                    "strict": True,
                }
            },
        )

        raw = response.output_text

        if not raw:
            raise RuntimeError(
                "OpenAI returned an empty response."
            )

        report = ComplianceReport.model_validate_json(
            raw
        )

        print(
            "[AI ROUTER] OpenAI SUCCESS"
        )

        return report

    except Exception as exc:

        print(
            "[AI ROUTER] OpenAI FAILED:",
            str(exc)
        )

        category = classify_provider_error(
            exc
        )

        raise RuntimeError(
            f"OPENAI_{category}: {exc}"
        )


# ============================================================
# GEMINI
# ============================================================

def analyze_with_gemini(
    prompt: str,
) -> ComplianceReport:

    if not gemini_client:
        raise RuntimeError(
            "Gemini API key is not configured."
        )

    print(
        f"[AI ROUTER] Trying Gemini: {GEMINI_MODEL}"
    )

    try:

        interaction = gemini_client.interactions.create(

            model=GEMINI_MODEL,

            input=prompt,

            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": ComplianceReport.model_json_schema(),
            },
        )

        raw = getattr(
            interaction,
            "output_text",
            None
        )

        if not raw:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        report = ComplianceReport.model_validate_json(
            raw
        )

        print(
            "[AI ROUTER] Gemini SUCCESS"
        )

        return report

    except Exception as exc:

        print(
            "[AI ROUTER] Gemini FAILED:",
            str(exc)
        )

        category = classify_provider_error(
            exc
        )

        raise RuntimeError(
            f"GEMINI_{category}: {exc}"
        )


# ============================================================
# MERGE REPORTS
# ============================================================

def merge_reports(
    reports,
    document_name: str,
    framework: str,
) -> ComplianceReport:

    all_findings = []

    summaries = []

    scores = []

    for report in reports:

        summaries.append(
            report.executive_summary
        )

        scores.append(
            report.compliance_score
        )

        all_findings.extend(
            report.findings
        )

    # --------------------------------------------------------
    # Re-number findings
    # --------------------------------------------------------

    normalized_findings = []

    for index, finding in enumerate(
        all_findings,
        start=1
    ):

        finding_data = finding.model_dump()

        finding_data["id"] = index

        normalized_findings.append(
            Finding.model_validate(
                finding_data
            )
        )

    # --------------------------------------------------------
    # Count risks
    # --------------------------------------------------------

    high_risk_count = sum(
        1
        for finding in normalized_findings
        if finding.severity == "HIGH"
    )

    critical_count = sum(
        1
        for finding in normalized_findings
        if finding.severity == "CRITICAL"
    )

    # --------------------------------------------------------
    # Average score
    # --------------------------------------------------------

    if scores:
        final_score = round(
            sum(scores) / len(scores)
        )
    else:
        final_score = 0

    # --------------------------------------------------------
    # Determine overall status
    # --------------------------------------------------------

    if critical_count > 0:
        overall_status = "NON_COMPLIANT"

    elif high_risk_count > 0:
        overall_status = "PARTIALLY_COMPLIANT"

    elif final_score >= 90:
        overall_status = "COMPLIANT"

    elif final_score >= 50:
        overall_status = "PARTIALLY_COMPLIANT"

    else:
        overall_status = "NEEDS_REVIEW"

    # --------------------------------------------------------
    # Executive summary
    # --------------------------------------------------------

    if summaries:

        executive_summary = (
            f"ComplyAI analyzed the document in "
            f"{len(reports)} sections against {framework}. "
            f"Overall estimated compliance score: "
            f"{final_score}/100. "
            f"The analysis identified "
            f"{len(normalized_findings)} meaningful findings. "
        )

        executive_summary += " ".join(
            summaries[:3]
        )

    else:

        executive_summary = (
            "No meaningful compliance findings were generated."
        )

    return ComplianceReport(

        document_name=document_name,

        framework=framework,

        executive_summary=executive_summary,

        overall_status=overall_status,

        compliance_score=final_score,

        total_findings=len(
            normalized_findings
        ),

        high_risk_count=high_risk_count,

        critical_count=critical_count,

        findings=normalized_findings,
    )


# ============================================================
# ANALYZE DOCUMENT
# ============================================================

def analyze_document(
    document_name: str,
    framework: str,
    document_text: str,
) -> ComplianceReport:

    # --------------------------------------------------------
    # Split document
    # --------------------------------------------------------

    chunks = split_document(
        document_text
    )

    if not chunks:
        raise RuntimeError(
            "Document contains no readable text."
        )

    total_chunks = len(chunks)

    print(
        f"[DOCUMENT] Split into {total_chunks} chunks"
    )

    reports = []

    # ========================================================
    # CHUNK LOOP
    # ========================================================

    for index, chunk in enumerate(
        chunks,
        start=1
    ):

        print(
            f"[ANALYSIS] Processing chunk "
            f"{index}/{total_chunks} "
            f"({len(chunk)} characters)"
        )

        prompt = build_prompt(
            document_name=document_name,
            framework=framework,
            document_text=chunk,
            chunk_number=index,
            total_chunks=total_chunks,
        )

        # ----------------------------------------------------
        # 1. GROQ
        # ----------------------------------------------------

        if groq_client:

            try:

                report = analyze_with_groq(
                    prompt
                )

                reports.append(
                    report
                )

                continue

            except RuntimeError as exc:

                print(
                    "[AI ROUTER] Groq unavailable:"
                )

                print(
                    f"[AI ROUTER] {exc}"
                )

                print(
                    "[AI ROUTER] Switching to OpenAI..."
                )

        # ----------------------------------------------------
        # 2. OPENAI
        # ----------------------------------------------------

        if openai_client:

            try:

                report = analyze_with_openai(
                    prompt
                )

                reports.append(
                    report
                )

                continue

            except RuntimeError as exc:

                print(
                    "[AI ROUTER] OpenAI unavailable:"
                )

                print(
                    f"[AI ROUTER] {exc}"
                )

                print(
                    "[AI ROUTER] Switching to Gemini..."
                )

        # ----------------------------------------------------
        # 3. GEMINI
        # ----------------------------------------------------

        if gemini_client:

            try:

                report = analyze_with_gemini(
                    prompt
                )

                reports.append(
                    report
                )

                continue

            except RuntimeError as exc:

                print(
                    "[AI ROUTER] Gemini unavailable:"
                )

                print(
                    f"[AI ROUTER] {exc}"
                )

        # ----------------------------------------------------
        # If this chunk failed everywhere
        # ----------------------------------------------------

        raise RuntimeError(
            f"All configured AI providers failed "
            f"for document chunk {index}/{total_chunks}."
        )

    # ========================================================
    # MERGE ALL CHUNKS
    # ========================================================

    final_report = merge_reports(
        reports=reports,
        document_name=document_name,
        framework=framework,
    )

    print(
        "[ANALYSIS] Completed successfully"
    )

    return final_report