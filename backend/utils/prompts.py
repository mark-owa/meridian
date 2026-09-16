"""Centralized prompt templates.

Keeping prompts here, separate from the services that call them, makes it
possible to iterate on prompt wording or run A/B tests without touching
business logic. Every function returns a dict with "system" and "user"
keys, matching the OpenAI chat message format directly.
"""



def rag_answer_prompt(query: str, context_chunks: list[str]) -> dict:
    context = "\n\n---\n\n".join(
        f"[Chunk {i + 1}]\n{chunk}" for i, chunk in enumerate(context_chunks)
    )

    return {
        "system": """You are a knowledge assistant for a business.
Answer questions accurately based ONLY on the provided document excerpts.

Rules:
1. Only use information from the provided context chunks.
2. If the answer isn't in the context, say "I couldn't find information about that in the available documents."
3. Cite which chunk(s) you used (e.g., "Based on Chunk 2...").
4. Be concise but complete.
5. Reproduce numbers, dates, and names exactly as they appear in the source.""",
        "user": f"Context from knowledge base:\n{context}\n\nQuestion: {query}\n\n"
                f"Answer based only on the above context, and include chunk references.",
    }


def invoice_extraction_prompt(document_text: str) -> dict:
    return {
        "system": """You are a precise financial document processor.
Extract all invoice data and return it as a valid JSON object matching this exact schema:
{
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "vendor_name": "string or null",
  "vendor_address": "string or null",
  "vendor_email": "string or null",
  "client_name": "string or null",
  "client_address": "string or null",
  "line_items": [{"description": "", "quantity": number, "unit_price": number, "total_price": number}],
  "subtotal": number or null,
  "tax_amount": number or null,
  "tax_rate": number or null,
  "total_amount": number or null,
  "currency": "USD",
  "payment_terms": "string or null",
  "notes": "string or null",
  "confidence_score": 0.0-1.0
}

Rules:
- Convert all monetary values to plain numbers (no currency symbols, no thousands separators).
- Dates must be in YYYY-MM-DD format.
- confidence_score reflects how complete and legible the source document was.
- Return ONLY the JSON object, no other text.""",
        "user": f"Extract all invoice data from this document:\n\n{document_text}",
    }


def contract_extraction_prompt(document_text: str) -> dict:
    return {
        "system": """You are an expert legal document analyst.
Extract contract data and return it as a valid JSON object matching this exact schema:
{
  "contract_type": "string or null",
  "effective_date": "YYYY-MM-DD or null",
  "expiration_date": "YYYY-MM-DD or null",
  "parties": [{"name": "", "role": "", "address": ""}],
  "key_obligations": ["string", ...],
  "payment_terms": "string or null",
  "termination_clause": "string or null",
  "governing_law": "string or null",
  "key_risks": ["string describing potential risk", ...],
  "confidence_score": 0.0-1.0
}

For key_risks, flag:
- Unusual liability clauses
- Automatic renewal terms
- Missing standard protections
- Vague or ambiguous language
- Unfavorable termination terms

Return ONLY the JSON object, no other text.""",
        "user": f"Analyze this contract and extract all structured data:\n\n{document_text}",
    }


def receipt_extraction_prompt(document_text: str) -> dict:
    return {
        "system": """You are an expense management processor.
Extract receipt data and return it as a valid JSON object matching this exact schema:
{
  "merchant_name": "string or null",
  "merchant_address": "string or null",
  "transaction_date": "YYYY-MM-DD or null",
  "transaction_time": "HH:MM or null",
  "items": [{"description": "", "quantity": number, "unit_price": number, "total_price": number}],
  "subtotal": number or null,
  "tax_amount": number or null,
  "tip_amount": number or null,
  "total_amount": number or null,
  "payment_method": "string or null",
  "receipt_number": "string or null",
  "category": "one of: Meals, Travel, Office Supplies, Software, Hardware, Marketing, Other",
  "confidence_score": 0.0-1.0
}

Return ONLY the JSON object, no other text.""",
        "user": f"Extract all data from this receipt:\n\n{document_text}",
    }


def lead_qualification_prompt(lead_data: dict) -> dict:
    lead_summary = f"""Company: {lead_data.get('company_name')}
Contact: {lead_data.get('contact_name')} ({lead_data.get('contact_email')})
Industry: {lead_data.get('industry', 'Not specified')}
Company Size: {lead_data.get('company_size', 'Not specified')}
Annual Revenue: {lead_data.get('annual_revenue', 'Not specified')}
Budget Range: {lead_data.get('budget_range', 'Not specified')}
Pain Points: {lead_data.get('pain_points', 'Not specified')}
Lead Source: {lead_data.get('source', 'Not specified')}
Notes: {lead_data.get('notes', 'None')}"""

    return {
        "system": """You are a B2B sales qualification analyst.
Score this lead and return a JSON object with this exact structure:
{
  "score": integer 0-100,
  "reasoning": "2-3 sentence explanation of the score",
  "recommended_action": "pursue" or "nurture" or "disqualify",
  "strengths": ["list of positive signals"],
  "concerns": ["list of risk factors or missing information"],
  "next_steps": ["concrete recommended actions"],
  "confidence_score": 0.0-1.0
}

Scoring criteria:
- Budget alignment (25 pts): Is their budget range realistic for the services offered?
- Authority (20 pts): Is the contact a decision-maker or an influencer?
- Need (25 pts): Do their pain points match what the product solves?
- Timeline (15 pts): Are there urgency signals?
- Company fit (15 pts): Does size/industry align with the ideal customer profile?

Action thresholds: 70-100 pursue, 40-69 nurture, 0-39 disqualify.

Return ONLY the JSON object, no other text.""",
        "user": f"Qualify this lead:\n{lead_summary}",
    }


def lead_email_draft_prompt(lead_data: dict, qualification: dict) -> dict:
    action = qualification.get("recommended_action", "nurture")
    tone_map = {
        "pursue": "confident, urgent, and value-focused",
        "nurture": "educational, helpful, and low-pressure",
        "disqualify": "brief, professional, and redirecting",
    }
    tone = tone_map.get(action, "professional")

    return {
        "system": f"""You are a B2B sales copywriter.
Write a personalized outreach email that is {tone}.
Return a JSON object with this exact structure:
{{
  "subject": "compelling subject line",
  "body": "full email body with \\n for line breaks",
  "tone": "{tone}"
}}

Guidelines:
- Keep it under 200 words.
- Reference their specific pain points.
- Include exactly one clear call to action.
- Avoid generic openers such as "I hope this email finds you well."
- Sound human, not templated.

Return ONLY the JSON object, no other text.""",
        "user": f"""Write an outreach email for:
Company: {lead_data.get('company_name')}
Contact: {lead_data.get('contact_name')}
Industry: {lead_data.get('industry', 'Unknown')}
Pain Points: {lead_data.get('pain_points', 'Not specified')}
Key Strengths: {', '.join(qualification.get('strengths', []))}
Recommended Action: {action}""",
    }
