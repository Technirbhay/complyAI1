import os

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.extractors import extract_document
from app.compliance import analyze_document


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="ComplyAI",
    description="Automated Compliance & Policy Checker Agent",
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",

        # Current Vite frontend
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        os.getenv(
            "FRONTEND_ORIGIN",
            "https://technirbhay.github.io",
        ).rstrip("/"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "name": "ComplyAI",
        "status": "online",
        "version": "1.0.0"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "service": "ComplyAI API"
    }


# ============================================================
# DOCUMENT ANALYSIS
# ============================================================

@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    framework: str = Form("GDPR")
):

    # ========================================================
    # SUPPORTED FRAMEWORKS
    # ========================================================

    allowed_frameworks = {
        "GDPR",
        "HIPAA",
        "SOC 2",
        "ISO 27001",
        "CCPA",
    }

    if framework not in allowed_frameworks:

        raise HTTPException(
            status_code=400,
            detail="Unsupported compliance framework"
        )


    # ========================================================
    # FILE NAME VALIDATION
    # ========================================================

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="File name is required"
        )


    # ========================================================
    # FILE TYPE VALIDATION
    # ========================================================

    allowed_extensions = {
        ".pdf",
        ".docx",
        ".txt",
        ".md",
    }

    extension = "." + file.filename.split(".")[-1].lower()

    if extension not in allowed_extensions:

        raise HTTPException(
            status_code=400,
            detail="Supported files: PDF, DOCX, TXT, MD"
        )


    try:

        # ====================================================
        # READ FILE
        # ====================================================

        file_data = await file.read()

        if not file_data:

            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )


        # ====================================================
        # EXTRACT DOCUMENT TEXT
        # ====================================================

        print(
            f"[DOCUMENT] Extracting: {file.filename}"
        )

        document_text = extract_document(
            file.filename,
            file_data
        )

        if not document_text.strip():

            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not extract readable text "
                    "from the document"
                )
            )


        # ====================================================
        # DOCUMENT SIZE LIMIT
        # ====================================================

        # Keep MVP responses faster.
        document_text = document_text[:60000]

        print(
            f"[DOCUMENT] Extracted "
            f"{len(document_text)} characters"
        )


        # ====================================================
        # AI ANALYSIS
        # ====================================================

        print(
            f"[ANALYSIS] Framework: {framework}"
        )

        report = analyze_document(
            document_name=file.filename,
            framework=framework,
            document_text=document_text,
        )


        # ====================================================
        # SUCCESS
        # ====================================================

        print(
            "[ANALYSIS] Completed successfully"
        )

        return report.model_dump()


    # ========================================================
    # HTTP ERRORS
    # ========================================================

    except HTTPException:

        raise


    # ========================================================
    # GENERAL / AI ERRORS
    # ========================================================

    except Exception as exc:

        error_message = str(exc)

        print(
            "[ANALYSIS ERROR]:",
            repr(exc)
        )


        # ====================================================
        # RATE LIMIT / QUOTA
        # ====================================================

        if (
            "rate limit" in error_message.lower()
            or "429" in error_message
            or "quota" in error_message.lower()
        ):

            raise HTTPException(
                status_code=429,
                detail=error_message
            )


        # ====================================================
        # SERVICE UNAVAILABLE
        # ====================================================

        if (
            "503" in error_message
            or "temporarily unavailable"
            in error_message.lower()
        ):

            raise HTTPException(
                status_code=503,
                detail=error_message
            )


        # ====================================================
        # MODEL NOT AVAILABLE
        # ====================================================

        if (
            "model" in error_message.lower()
            and (
                "not available"
                in error_message.lower()
                or "not_found"
                in error_message.lower()
            )
        ):

            raise HTTPException(
                status_code=503,
                detail=error_message
            )


        # ====================================================
        # ALL OTHER ERRORS
        # ====================================================

        raise HTTPException(
            status_code=500,
            detail=error_message
        )