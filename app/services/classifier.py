from typing import Optional

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.models.listing import MaterialGrade
from app.utils.restricted_materials import check_restricted


class ClassificationResult(BaseModel):
    material_category: str
    grade: MaterialGrade
    confidence: float
    needs_tpqc: bool
    is_blocked: bool
    block_reason: Optional[str]
    reasoning: str


SYSTEM_PROMPT = """
You are a recycling material classification specialist.

Grading rubric:
- A1: premium, >90% purity
- A2: good, 75-90% purity
- B1: standard, 60-75% purity
- B2: low grade, 40-60% purity
- C: reject / broker-only, <40% purity or poor quality confidence

Rules for 'confidence' (float between 0.0 and 1.0):
- If purity > 90% and description is clear, confidence MUST be > 0.85.
- If description is vague or purity is low, confidence should be < 0.70.

Before grading, always check if material is restricted/banned and treat as blocked.
Return concise but useful reasoning.

Few-shot examples:
1) Description: Clean HDPE regrind from post-industrial containers, Purity: 95
   Output: category Plastic/HDPE, grade A1, confidence 0.95.
2) Description: Mixed PET flakes with labels and caps residue, Purity: 82
   Output: category Plastic/PET, grade A2, confidence 0.85.
3) Description: Rusted mixed steel scrap with paint contamination, Purity: 68
   Output: category Metal/Steel, grade B1, confidence 0.75.
4) Description: Insulated copper wire bundles with plastics attached, Purity: 55
   Output: category Metal/Copper, grade B2, confidence 0.65.
5) Description: Mixed municipal plastic waste with food contamination, Purity: 35
   Output: category Mixed/Plastic Waste, grade C, confidence 0.40.
"""


def _fallback(reason: str) -> ClassificationResult:
    return ClassificationResult(
        material_category="Unknown/Unverified",
        grade=MaterialGrade.C,
        confidence=0.5,
        needs_tpqc=True,
        is_blocked=False,
        block_reason=None,
        reasoning=reason,
    )


from app.config import get_settings

def classify_material(description: str, quantity_kg: float, purity_pct: float) -> ClassificationResult:
    blocked, reason = check_restricted(description)
    if blocked:
        return ClassificationResult(
            material_category="Restricted",
            grade=MaterialGrade.C,
            confidence=1.0,
            needs_tpqc=True,
            is_blocked=True,
            block_reason=reason,
            reasoning="Listing blocked due to restricted material policy.",
        )

    try:
        settings = get_settings()
        model = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=settings.OPENAI_API_KEY)
        structured = model.with_structured_output(ClassificationResult)
        result = structured.invoke(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "user",
                    (
                        "Classify this listing and return structured output. "
                        f"Description: {description}\n"
                        f"Quantity (kg): {quantity_kg}\n"
                        f"Purity (%): {purity_pct}"
                    ),
                ),
            ]
        )
        
        if isinstance(result, dict):
            result = ClassificationResult(**result)
            
        result.is_blocked = False
        result.block_reason = None
        result.needs_tpqc = bool(result.confidence < 0.70)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Fallback with error
        return _fallback(f"LLM classification unavailable: {str(e)}")
