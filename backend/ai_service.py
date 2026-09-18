import os
import time
import json
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen


from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError
from google.genai import types
from pydantic import BaseModel, Field
from typing import Literal

try:
    from ddgs import DDGS
except ImportError:
    DDGS = None

load_dotenv()


def _gemini_status_code(error):
    status_code = (
        getattr(error, "code", None)
        or getattr(error, "status_code", None)
        or getattr(error, "http_status", None)
    )
    if status_code is not None:
        try:
            return int(status_code)
        except (TypeError, ValueError):
            pass

    message = str(error)
    match = re.search(r"\b(429|503)\b", message)
    return int(match.group(1)) if match else None


def _gemini_error_message(error, max_length=600):
    """Return a concise diagnostic message without dumping the full SDK error."""
    message = getattr(error, "message", None) or str(error)
    message = re.sub(r"\s+", " ", str(message)).strip()
    return message[:max_length] if message else "No error message returned by Gemini."


class TransformationGeneration(BaseModel):
    before_emotional_state: str = Field(
        description="How the target customer is likely to feel before solving the problem."
    )
    before_core_fear: str = Field(
        description="The main fear or consequence the target customer worries about before solving the problem."
    )
    before_daily_experience: str = Field(
        description="What an ordinary day or recurring situation looks like for the target customer before the transformation."
    )
    before_identity: str = Field(
        description="How the target customer is likely to see themselves before the transformation."
    )
    after_emotional_state: str = Field(
        description="How the target customer should realistically feel after achieving the promised transformation."
    )
    after_core_fear: str = Field(
        description="How the main fear or consequence becomes smaller, clearer, or more manageable after the transformation."
    )
    after_daily_experience: str = Field(
        description="What an ordinary day or recurring situation should look like after the transformation."
    )
    after_identity: str = Field(
        description="How the target customer should realistically see themselves after the transformation."
    )


_client = None


def get_gemini_client():
    global _client

    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY was not found. Make sure the backend .env file contains your Gemini API key."
            )

        _client = genai.Client(api_key=api_key)

    return _client


def generate_transformation_map(opportunity) -> TransformationGeneration:
    client = get_gemini_client()

    prompt = f"""
You are NOVA's Product Transformation Strategist.

Your job is to define the customer's realistic before-and-after transformation for a digital product opportunity.

Use only the opportunity information provided below. Do not invent statistics, credentials, research findings, or facts that are not present.

The transformation should be:
- specific to the audience and problem
- emotionally believable
- practical rather than exaggerated
- focused on a meaningful change in the customer's experience
- suitable as the foundation for a digital product
- written in natural, human language
- free of generic AI-sounding filler
- free of em dashes and en dashes

Do not promise that the customer will completely eliminate every difficulty. The AFTER state should describe a credible improvement, not a fantasy outcome.

OPPORTUNITY
Industry: {opportunity.industry}
Niche: {opportunity.niche}
Opportunity title: {opportunity.title}
Problem: {opportunity.problem}

Create the eight transformation fields:
1. BEFORE emotional state
2. BEFORE core fear
3. BEFORE daily experience
4. BEFORE identity
5. AFTER emotional state
6. AFTER core fear
7. AFTER daily experience
8. AFTER identity

Each field should be concise but specific. Usually one or two sentences is enough.
"""

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]

    last_error = None

    for model_name in models_to_try:
        try:
            print(
                f"Trying Gemini model for transformation map: {model_name}"
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TransformationGeneration,
                    temperature=0.6,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )

            if not response.parsed:
                raise RuntimeError(
                    f"{model_name} returned a response that NOVA could not parse."
                )

            print(
                f"Successfully generated transformation map with: "
                f"{model_name}"
            )

            return response.parsed

        except ServerError as error:
            status_code = (
                getattr(error, "code", None)
                or getattr(error, "status_code", None)
            )

            if status_code != 503:
                raise

            last_error = error

            print(
                f"{model_name} is temporarily unavailable. "
                "Trying the next model..."
            )

            time.sleep(1)

        except RuntimeError as error:
            last_error = error

            print(
                f"{model_name} did not produce a valid transformation map. "
                "Trying the next model..."
            )

    raise RuntimeError(
        "Gemini could not produce a valid transformation map. "
        "Please try generating the transformation again."
    ) from last_error



class ProductSummaryGeneration(BaseModel):
    title: str = Field(
        description="A clear, outcome-focused title for the digital product."
    )
    subtitle: str = Field(
        description="A concise subtitle explaining the method or transformation."
    )
    about: str = Field(
        description="A natural product description explaining who it is for, the problem, and the practical outcome."
    )
    what_youll_learn: str = Field(
        description="A concise list of the main things the customer will learn or be able to do, with each item on a new line."
    )
    estimated_reading_time: int = Field(
        description="A realistic estimated reading time in minutes for an eBook product."
    )
    section_count: int = Field(
        description="A sensible proposed number of main sections for the product."
    )
    bonus_materials: str = Field(
        description="A concise list of useful bonus materials that naturally support the product, with each item on a new line."
    )


def generate_product_summary(opportunity, transformation, product_format: str) -> ProductSummaryGeneration:
    client = get_gemini_client()

    prompt = f"""
You are NOVA's Product Strategist.

Create a concise product summary for a digital product using the opportunity
and customer transformation below.

The summary is a product planning artifact, not sales hype. Keep it specific,
credible, useful, and natural. Do not invent statistics, credentials, research
findings, testimonials, guarantees, or facts that are not provided.

The title should promise a meaningful outcome without making an unrealistic
guarantee. The subtitle should clarify the method or transformation.

The About section should clearly communicate who the product is for, the
problem it addresses, and what the customer will be able to do differently.

What You'll Learn should contain 4 to 7 concrete learning outcomes, one per
line. Start each line with a useful action or capability rather than generic
phrases such as 'understand the importance of'.

For an eBook, estimate a realistic reading time and propose a sensible number
of main sections. These are planning estimates, not claims about an existing
book.

Bonus materials should be practical resources that naturally support the
method. Do not add bonuses merely to make the offer sound bigger.

Use natural human language. Avoid generic AI-sounding filler. Avoid long dashes.

PRODUCT FORMAT
{product_format}

OPPORTUNITY
Industry: {opportunity.industry}
Niche: {opportunity.niche}
Opportunity title: {opportunity.title}
Problem: {opportunity.problem}

TRANSFORMATION
Before emotional state: {transformation.before_emotional_state}
Before core fear: {transformation.before_core_fear}
Before daily experience: {transformation.before_daily_experience}
Before identity: {transformation.before_identity}
After emotional state: {transformation.after_emotional_state}
After core fear: {transformation.after_core_fear}
After daily experience: {transformation.after_daily_experience}
After identity: {transformation.after_identity}

Create all seven product summary fields.
"""

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]

    last_error = None

    for model_name in models_to_try:
        try:
            print(f"Trying Gemini model for product summary: {model_name}")

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ProductSummaryGeneration,
                    temperature=0.6,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )

            if not response.parsed:
                raise RuntimeError(
                    f"{model_name} returned a response that NOVA could not parse."
                )

            print(f"Successfully generated product summary with: {model_name}")

            return response.parsed

        except ServerError as error:
            status_code = (
                getattr(error, "code", None)
                or getattr(error, "status_code", None)
            )

            if status_code != 503:
                raise

            last_error = error

            print(
                f"{model_name} is temporarily unavailable. "
                "Trying the next model..."
            )

            time.sleep(1)

    raise RuntimeError(
        "All configured Gemini models are temporarily unavailable. "
        "Please try again in a few minutes."
    ) from last_error


class ProductOutlineSectionGeneration(BaseModel):
    title: str = Field(
        description="A clear, specific section title that advances the product toward its promised transformation."
    )
    purpose: str = Field(
        description="What this section should help the reader understand, decide, practice, or accomplish."
    )


class ProductOutlineGeneration(BaseModel):
    sections: list[ProductOutlineSectionGeneration] = Field(
        min_length=7,
        max_length=12,
        description="The ordered main sections of the product outline. Use enough sections to teach the transformation properly without adding filler."
    )


def generate_product_outline(opportunity, transformation, summary, product_format: str) -> ProductOutlineGeneration:
    client = get_gemini_client()

    suggested_count = summary.section_count or 7
    suggested_count = max(4, min(suggested_count, 12))

    prompt = f"""
You are NOVA's Product Architect.

Create the main outline for a digital product using the product opportunity,
customer transformation, and approved product summary below.

The outline will become the structural blueprint for the eventual manuscript.
Do not write the manuscript yet.

The Product Summary contains a suggested section count. Treat that number as
a planning preference, NOT as a fixed requirement.

Use your judgment to choose the number of main sections that the product
actually needs. For an eBook, normally create 7 to 10 main sections. You may
use up to 12 when the transformation genuinely requires more room.

If the suggested count is too low to teach the transformation properly,
increase the number of sections. If it is unnecessarily high, reduce it.

Do not force the outline to match the suggested count.

The sections should form a logical progression from the customer's current
problem toward the promised transformation. Avoid redundant sections. Each
section should have a distinct job. Prefer practical progression over generic
topic lists.

For each section:
- write a clear, useful title
- explain its purpose in one or two natural sentences
- make sure it advances the transformation
- do not invent statistics, research findings, credentials, testimonials, or
  claims that are not supported by the supplied information
- do not use sales hype
- do not write generic filler
- use natural human language
- avoid long dashes

For an eBook, the outline should be suitable for a practical, readable guide.
The introduction and conclusion should only be included if they are genuinely
useful as main sections. Do not add them automatically just to fill the outline.

PRODUCT FORMAT
{product_format}

SUGGESTED SECTION COUNT
{suggested_count}

OPPORTUNITY
Industry: {opportunity.industry}
Niche: {opportunity.niche}
Opportunity title: {opportunity.title}
Problem: {opportunity.problem}

TRANSFORMATION
Before emotional state: {transformation.before_emotional_state}
Before core fear: {transformation.before_core_fear}
Before daily experience: {transformation.before_daily_experience}
Before identity: {transformation.before_identity}
After emotional state: {transformation.after_emotional_state}
After core fear: {transformation.after_core_fear}
After daily experience: {transformation.after_daily_experience}
After identity: {transformation.after_identity}

PRODUCT SUMMARY
Title: {summary.title}
Subtitle: {summary.subtitle}
About: {summary.about}
What the customer will learn:
{summary.what_youll_learn}
Bonus materials:
{summary.bonus_materials}

Return the complete ordered outline. Do not return fewer than 7 sections.
Do not add sections merely to reach a number.
"""

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]

    last_error = None

    for model_name in models_to_try:
        try:
            print(f"Trying Gemini model for product outline: {model_name}")

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ProductOutlineGeneration,
                    temperature=0.5,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )

            if not response.parsed:
                raise RuntimeError(
                    f"{model_name} returned a response that NOVA could not parse."
                )

            section_count = len(response.parsed.sections)

            if section_count < 7 or section_count > 12:
                raise RuntimeError(
                    f"{model_name} returned {section_count} sections. "
                    "NOVA requires between 7 and 12 sections for this outline."
                )

            print(
                f"Successfully generated product outline with: "
                f"{model_name} ({section_count} sections)"
            )

            return response.parsed

        except ServerError as error:
            status_code = (
                getattr(error, "code", None)
                or getattr(error, "status_code", None)
            )

            if status_code != 503:
                raise

            last_error = error

            print(
                f"{model_name} is temporarily unavailable. "
                "Trying the next model..."
            )

            time.sleep(1)

        except RuntimeError as error:
            last_error = error

            print(
                f"{model_name} did not produce a valid outline. "
                "Trying the next model..."
            )

    raise RuntimeError(
        "Gemini could not produce a valid 7 to 12 section outline. "
        "Please try generating the outline again."
    ) from last_error


class SectionBriefGeneration(BaseModel):
    position: int = Field(
        description="The position of the section in the approved product outline."
    )
    objective: str = Field(
        description="The specific job this section must accomplish for the reader."
    )
    key_concepts: str = Field(
        description="The key concepts, ideas, or distinctions that should be explained in this section, one per line."
    )
    practical_steps: str = Field(
        description="The practical actions, process, or exercises the reader should work through in this section, one per line."
    )
    example_scenario: str = Field(
        description="A concrete, believable scenario or example that would make the section easier to understand."
    )
    common_mistakes: str = Field(
        description="The realistic mistakes, misunderstandings, or obstacles this section should address, one per line."
    )
    reader_outcome: str = Field(
        description="What the reader should understand, decide, or be able to do after completing this section."
    )


class SectionBriefGenerationResponse(BaseModel):
    briefs: list[SectionBriefGeneration] = Field(
        min_length=7,
        max_length=12,
        description="One structured brief for every section in the approved outline."
    )


def generate_section_briefs(
    opportunity,
    transformation,
    summary,
    sections,
    product_format: str,
) -> SectionBriefGenerationResponse:
    client = get_gemini_client()

    outline_text = "\n\n".join(
        [
            f"SECTION {section.position}: {section.title}\n"
            f"Purpose already approved: {section.purpose or 'Not specified'}"
            for section in sections
        ]
    )

    prompt = f"""
You are NOVA's Section Brief Architect.

The product outline has already been approved by the user.

Your job is to create a detailed but concise writing blueprint for EVERY
section in that outline. These briefs will be used later by a manuscript
writer. Do not write the manuscript yet.

Do not change, merge, remove, or reorder the approved sections.

Every section needs a distinct job. The brief should tell the future writer
what the section needs to accomplish, what ideas need explanation, what the
reader should actually do, and what concrete example would make the material
clear.

This is a practical digital product, so favor useful teaching over abstract
discussion.

For every section provide:
1. objective
2. key concepts
3. practical steps
4. one believable example scenario
5. common mistakes or obstacles
6. reader outcome

Key concepts and practical steps should be written as separate items, one per
line.

Do not invent statistics, research findings, credentials, testimonials,
guarantees, or factual claims that are not supported by the supplied
information.

Use natural human language. Avoid generic AI-sounding filler. Avoid long dashes.
Do not make the writing sound like a textbook or a corporate training manual.

PRODUCT FORMAT
{product_format}

OPPORTUNITY
Industry: {opportunity.industry}
Niche: {opportunity.niche}
Opportunity title: {opportunity.title}
Problem: {opportunity.problem}

TRANSFORMATION
Before emotional state: {transformation.before_emotional_state}
Before core fear: {transformation.before_core_fear}
Before daily experience: {transformation.before_daily_experience}
Before identity: {transformation.before_identity}
After emotional state: {transformation.after_emotional_state}
After core fear: {transformation.after_core_fear}
After daily experience: {transformation.after_daily_experience}
After identity: {transformation.after_identity}

PRODUCT SUMMARY
Title: {summary.title}
Subtitle: {summary.subtitle}
About: {summary.about}
What the customer will learn:
{summary.what_youll_learn}
Bonus materials:
{summary.bonus_materials}

APPROVED PRODUCT OUTLINE
{outline_text}

Return exactly one brief for each approved section.
Use the section's existing position number.
Do not return fewer or more briefs than there are approved sections.
"""

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]

    last_error = None

    for model_name in models_to_try:
        try:
            print(
                f"Trying Gemini model for section briefs: {model_name}"
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SectionBriefGenerationResponse,
                    temperature=0.5,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )

            if not response.parsed:
                raise RuntimeError(
                    f"{model_name} returned a response that NOVA could not parse."
                )

            if len(response.parsed.briefs) != len(sections):
                raise RuntimeError(
                    f"{model_name} returned {len(response.parsed.briefs)} briefs "
                    f"for {len(sections)} approved sections."
                )

            expected_positions = [section.position for section in sections]
            actual_positions = [brief.position for brief in response.parsed.briefs]

            if actual_positions != expected_positions:
                raise RuntimeError(
                    f"{model_name} returned section positions that do not match "
                    "the approved outline."
                )

            print(
                f"Successfully generated section briefs with: "
                f"{model_name} ({len(response.parsed.briefs)} briefs)"
            )

            return response.parsed

        except ServerError as error:
            status_code = (
                getattr(error, "code", None)
                or getattr(error, "status_code", None)
            )

            if status_code != 503:
                raise

            last_error = error

            print(
                f"{model_name} is temporarily unavailable. "
                "Trying the next model..."
            )

            time.sleep(1)

        except RuntimeError as error:
            last_error = error

            print(
                f"{model_name} did not produce a valid set of section briefs. "
                "Trying the next model..."
            )

    raise RuntimeError(
        "Gemini could not produce a valid set of section briefs. "
        "Please try generating the section briefs again."
    ) from last_error



class ContentBlueprintGeneration(BaseModel):
    position: int = Field(
        description="The position of the section in the approved product outline."
    )
    hook_angle: str = Field(
        description="The most useful opening angle for the section. It should orient the reader through a concrete situation, question, tension, or observation, not a gimmicky hook."
    )
    core_explanation: str = Field(
        description="The central explanation the section must teach clearly before the reader moves on."
    )
    supporting_points: str = Field(
        description="The supporting points that need to be explained, one per line."
    )
    reader_action: str = Field(
        description="The concrete action, exercise, decision, or implementation step the reader should complete in this section."
    )
    example_scenario: str = Field(
        description="A realistic scenario with enough detail for a future writer to turn it into a natural example."
    )
    misconception_or_objection: str = Field(
        description="The most important misunderstanding, resistance, or reasonable objection this section should address."
    )
    transition_to_next: str = Field(
        description="The logical bridge from this section to the next section without using a forced summary."
    )
    avoid: str = Field(
        description="Topics, claims, tangents, or writing habits the future writer should avoid in this section, one per line."
    )
    target_word_count: int = Field(
        ge=400,
        le=1800,
        description="A practical target word count for the section."
    )


class ContentBlueprintGenerationResponse(BaseModel):
    blueprints: list[ContentBlueprintGeneration] = Field(
        min_length=7,
        max_length=12,
        description="One content blueprint for every section in the approved outline."
    )


def generate_content_blueprints(
    opportunity,
    transformation,
    summary,
    sections,
    section_briefs,
    product_format: str,
) -> ContentBlueprintGenerationResponse:
    client = get_gemini_client()

    brief_by_section = {
        brief.section_id: brief
        for brief in section_briefs
    }

    outline_text = "\n\n".join(
        [
            f"SECTION {section.position}: {section.title}\n"
            f"Approved purpose: {section.purpose or 'Not specified'}\n"
            f"Section brief objective: {brief_by_section[section.id].objective}\n"
            f"Key concepts: {brief_by_section[section.id].key_concepts}\n"
            f"Practical steps: {brief_by_section[section.id].practical_steps}\n"
            f"Example scenario: {brief_by_section[section.id].example_scenario}\n"
            f"Common mistakes: {brief_by_section[section.id].common_mistakes}\n"
            f"Reader outcome: {brief_by_section[section.id].reader_outcome}"
            for section in sections
        ]
    )

    prompt = f"""
You are NOVA's Content Blueprint Architect.

The product opportunity, transformation, summary, approved outline, and section
briefs below have already been reviewed by the user.

Create a content blueprint for EVERY approved section. This is the final planning
layer before manuscript generation. Do not write the manuscript itself.

Do not change, merge, remove, or reorder the approved sections.
Do not replace the section brief. Expand it into a more useful plan for a future
human-style writer.

The blueprint must help a writer produce a section that feels specific,
coherent, useful, and connected to the rest of the product.

For every section provide:
1. hook_angle: the best way to enter the section naturally
2. core_explanation: the central idea that must be taught
3. supporting_points: the important points that need explanation, one per line
4. reader_action: the concrete thing the reader should do or decide
5. example_scenario: one realistic scenario with useful detail
6. misconception_or_objection: the main misunderstanding or resistance to address
7. transition_to_next: the logical bridge into the next section
8. avoid: tangents, unsupported claims, repetition, or weak writing habits to avoid
9. target_word_count: a sensible length for the section

Important writing constraints:
- Build from the supplied material. Do not invent research, statistics, credentials,
  testimonials, guarantees, or unsupported factual claims.
- Do not assume a US setting, US currency, or American names unless the supplied
  product context requires them. Prefer neutral examples when the market is not
  specified.
- Keep examples believable and concrete rather than turning them into motivational
  stories.
- The reader action must be genuinely actionable, not a vague instruction such as
  "reflect on your goals."
- The hook should be useful and natural, not clickbait.
- The transition should create forward momentum rather than repeat the section's
  conclusion.
- Avoid generic AI phrasing, corporate language, textbook filler, and repetitive
  summaries.
- Avoid long dashes.

PRODUCT FORMAT
{product_format}

OPPORTUNITY
Industry: {opportunity.industry}
Niche: {opportunity.niche}
Opportunity title: {opportunity.title}
Problem: {opportunity.problem}

TRANSFORMATION
Before emotional state: {transformation.before_emotional_state}
Before core fear: {transformation.before_core_fear}
Before daily experience: {transformation.before_daily_experience}
Before identity: {transformation.before_identity}
After emotional state: {transformation.after_emotional_state}
After core fear: {transformation.after_core_fear}
After daily experience: {transformation.after_daily_experience}
After identity: {transformation.after_identity}

PRODUCT SUMMARY
Title: {summary.title}
Subtitle: {summary.subtitle}
About: {summary.about}
What the customer will learn:
{summary.what_youll_learn}
Bonus materials:
{summary.bonus_materials}

APPROVED OUTLINE AND SECTION BRIEFS
{outline_text}

Return exactly one blueprint for each approved section.
Use the section's existing position number.
Do not return fewer or more blueprints than there are approved sections.
"""

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]

    last_error = None

    for model_name in models_to_try:
        try:
            print(
                f"Trying Gemini model for content blueprints: {model_name}"
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ContentBlueprintGenerationResponse,
                    temperature=0.45,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )

            if not response.parsed:
                raise RuntimeError(
                    f"{model_name} returned a response that NOVA could not parse."
                )

            if len(response.parsed.blueprints) != len(sections):
                raise RuntimeError(
                    f"{model_name} returned {len(response.parsed.blueprints)} blueprints "
                    f"for {len(sections)} approved sections."
                )

            expected_positions = [section.position for section in sections]
            actual_positions = [
                blueprint.position
                for blueprint in response.parsed.blueprints
            ]

            if actual_positions != expected_positions:
                raise RuntimeError(
                    f"{model_name} returned section positions that do not match "
                    "the approved outline."
                )

            print(
                f"Successfully generated content blueprints with: "
                f"{model_name} ({len(response.parsed.blueprints)} blueprints)"
            )

            return response.parsed

        except ServerError as error:
            status_code = (
                getattr(error, "code", None)
                or getattr(error, "status_code", None)
            )

            if status_code != 503:
                raise

            last_error = error
            print(
                f"{model_name} is temporarily unavailable. "
                "Trying the next model..."
            )
            time.sleep(1)

        except RuntimeError as error:
            last_error = error
            print(
                f"{model_name} did not produce a valid set of content blueprints. "
                "Trying the next model..."
            )

    raise RuntimeError(
        "Gemini could not produce a valid set of content blueprints. "
        "Please try generating the content blueprints again."
    ) from last_error


class ReaderExperienceGeneration(BaseModel):
    position: int = Field(description="The exact approved section position this plan belongs to.")
    reader_job: str = Field(description="The one meaningful job this section must accomplish for this specific reader.")
    reader_question: str = Field(description="The question or uncertainty the reader is likely carrying into this section.")
    desired_reaction: str = Field(description="The concrete reader reaction NOVA wants to create, such as recognition, clarity, confidence, or readiness to act.")
    experience_type: str = Field(description="The primary experience mode for this section, such as explanation, scenario, framework, checklist, worksheet, decision tree, reflection, comparison, or mixed.")
    visual_decision: str = Field(description="Choose a purposeful visual or explicitly say no visual. Explain what the visual would help the reader understand or do.")
    interactive_element: str = Field(description="Choose a useful action artifact such as checklist, worksheet, template, decision tree, reflection, mini challenge, or none. Explain its purpose.")
    evidence_anchor: str = Field(description="Which supplied INTENT evidence, customer language, or validated problem signal should anchor this section. Do not invent evidence.")
    claim_boundary: str = Field(description="What the writer may state as observed evidence versus what must be framed as inference, recommendation, or hypothesis.")
    reader_action: str = Field(description="The concrete thing the reader should do, decide, build, test, or change after this section.")
    transition_intent: str = Field(description="Why the next section becomes useful after this one. Keep it natural and non-repetitive.")
    avoid: str = Field(description="Specific content or experience patterns to avoid in this section, including unsupported claims or unnecessary elements.")


class ReaderExperienceGenerationResponse(BaseModel):
    experiences: list[ReaderExperienceGeneration] = Field(
        min_length=7,
        max_length=12,
        description="One reader-experience plan for every approved product section."
    )


def generate_reader_experiences(
    opportunity,
    intent_brief,
    intent_evidence,
    transformation,
    summary,
    sections,
    section_briefs,
    content_blueprints,
    product_format="digital product",
) -> ReaderExperienceGenerationResponse:
    client = get_gemini_client()

    brief_by_section = {item.section_id: item for item in section_briefs}
    blueprint_by_section = {item.section_id: item for item in content_blueprints}

    evidence_blocks = []
    for item in (intent_evidence or [])[:10]:
        evidence_blocks.append(
            "SOURCE: " + getattr(item, "source_title", "Public source") + "\n"
            + "SIGNAL: " + (getattr(item, "signal_type", "") or "") + "\n"
            + "EVIDENCE: " + (getattr(item, "excerpt", "") or "")
        )

    evidence_text = "\n\n".join(evidence_blocks) or "No source excerpts supplied. Do not invent evidence."

    section_blocks = []
    for section in sections:
        brief = brief_by_section.get(section.id)
        blueprint = blueprint_by_section.get(section.id)
        section_blocks.append(
            f"SECTION {section.position}: {section.title}\n"
            f"Purpose: {section.purpose}\n"
            f"Brief objective: {getattr(brief, 'objective', '')}\n"
            f"Reader outcome: {getattr(brief, 'reader_outcome', '')}\n"
            f"Practical steps: {getattr(brief, 'practical_steps', '')}\n"
            f"Blueprint hook: {getattr(blueprint, 'hook_angle', '')}\n"
            f"Blueprint core explanation: {getattr(blueprint, 'core_explanation', '')}\n"
            f"Blueprint reader action: {getattr(blueprint, 'reader_action', '')}\n"
            f"Blueprint example: {getattr(blueprint, 'example_scenario', '')}\n"
            f"Blueprint avoid: {getattr(blueprint, 'avoid', '')}"
        )

    sections_text = "\n\n".join(section_blocks)

    prompt = f"""
You are NOVA's Reader Experience Architect.

Create one reader-experience plan for every approved section of a digital product.
This layer sits between Content Blueprints and the manuscript writer.

The purpose is NOT to decorate the product. It is to decide what each section should
make this particular reader understand, feel, notice, question, and do.

The product must remain specific to the customer problem validated by INTENT.
Do not broaden the audience into a generic market. Do not add random visuals.
Sometimes the correct decision is no visual and no interactive element.

CRITICAL EVIDENCE RULES
- Observed evidence is only what the supplied INTENT evidence actually supports.
- Inference is an interpretation of observed signals.
- Hypothesis is a proposed solution, workflow, format, or recommendation that still needs validation.
- Never turn a proposed solution into an industry fact.
- Never invent statistics, customer counts, time savings, percentages, testimonials, credentials, research findings, or market-size claims.
- If a useful recommendation is not directly supported by evidence, mark it as a recommendation or hypothesis in claim_boundary.
- Customer language should come from the supplied INTENT brief, not invented quotes.

READER EXPERIENCE PRINCIPLES
- Start from the reader's real situation, not from a generic chapter template.
- Give each section one primary job.
- Prefer believable situations, concrete decisions, examples, frameworks, checklists, worksheets, comparisons, or decision trees when they genuinely help.
- Do not force a visual into every section.
- Do not force a worksheet or checklist into every section.
- A visual is justified only when it makes a relationship, sequence, comparison, structure, or decision easier to understand.
- An interactive element is justified only when it helps the reader perform the intended transformation.
- The desired reaction should be specific, such as "that's exactly what keeps happening to me" or "I know what to change next", not generic praise.
- The reader action must be practical and possible for this customer.
- Avoid textbook filler, corporate language, motivational padding, repetitive summaries, and decorative content.
- Use natural human language. Avoid long dashes.

INTENT
Target customer: {intent_brief.target_customer}
Problem context: {intent_brief.problem_context}
Trigger: {intent_brief.trigger}
Current behavior: {intent_brief.current_behavior}
Failed alternatives: {intent_brief.failed_alternatives}
Desired outcome: {intent_brief.desired_outcome}
Constraints: {intent_brief.constraints}
Objections: {intent_brief.objections}
Customer language: {intent_brief.customer_language}
Existing solutions: {intent_brief.existing_solutions}
Solution gap: {intent_brief.solution_gap}
Potential solution: {intent_brief.potential_solution}
Evidence confidence: {intent_brief.evidence_confidence}
Evidence summary: {intent_brief.evidence_summary}

PUBLIC EVIDENCE SUPPLIED TO INTENT
{evidence_text}

PRODUCT
Format: {product_format}
Opportunity: {opportunity.title}
Problem: {opportunity.problem}
Product title: {summary.title}
Product subtitle: {summary.subtitle}
Product about: {summary.about}

TRANSFORMATION
Before: {transformation.before_daily_experience} | {transformation.before_identity}
After: {transformation.after_daily_experience} | {transformation.after_identity}

APPROVED SECTIONS
{sections_text}

Return exactly one experience plan for each approved section, preserving section positions and order.
Do not add, remove, rename, or reorder sections.
"""

    models_to_try = [
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]
    last_error = None

    for model_name in models_to_try:
        try:
            print(
                f"Trying Gemini model for reader experience: {model_name}"
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ReaderExperienceGenerationResponse,
                    temperature=0.35,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )

            if not response.parsed:
                raise RuntimeError(
                    f"{model_name} returned no structured reader experience."
                )

            result = response.parsed
            expected_positions = [section.position for section in sections]
            actual_positions = [item.position for item in result.experiences]

            if actual_positions != expected_positions:
                raise RuntimeError(
                    "Reader experience positions do not match the approved section order."
                )

            combined = " ".join(
                " ".join(
                    [
                        item.reader_job,
                        item.reader_question,
                        item.desired_reaction,
                        item.experience_type,
                        item.visual_decision,
                        item.interactive_element,
                        item.evidence_anchor,
                        item.claim_boundary,
                        item.reader_action,
                        item.transition_intent,
                        item.avoid,
                    ]
                )
                for item in result.experiences
            )

            if "—" in combined or "–" in combined:
                raise RuntimeError(
                    "Reader experience contained an em dash or en dash."
                )

            print(
                f"Successfully generated reader experience with: {model_name} "
                f"({len(result.experiences)} plans)"
            )
            return result

        except ServerError as error:
            status_code = getattr(error, "code", None) or getattr(error, "status_code", None)
            if status_code != 503:
                raise
            last_error = error
            print(
                f"{model_name} is temporarily unavailable. Trying the next model..."
            )
            time.sleep(1)

        except RuntimeError as error:
            last_error = error
            print(
                f"{model_name} did not produce a valid reader experience. "
                "Trying the next model..."
            )

    raise RuntimeError(
        "Gemini could not produce a valid reader-experience plan. "
        "Please try generating it again."
    ) from last_error


class ManuscriptSectionGeneration(BaseModel):
    content: str = Field(
        description=(
            "The complete manuscript section in polished Markdown prose. "
            "Write the actual section, not a plan, outline, notes, or commentary."
        )
    )


def _count_words(text: str) -> int:
    return len(text.split())


def _validate_manuscript_content(content: str) -> str:
    cleaned = content.strip()

    if not cleaned:
        raise RuntimeError("Gemini returned an empty manuscript section.")

    if "—" in cleaned:
        raise RuntimeError(
            "Gemini returned an em dash. The manuscript must not contain em dashes."
        )

    if "–" in cleaned:
        raise RuntimeError(
            "Gemini returned an en dash. The manuscript must not contain long dashes."
        )

    return cleaned


def generate_manuscript_section(
    opportunity,
    transformation,
    summary,
    section,
    section_brief,
    content_blueprint,
    product_format="digital product",
    previous_section=None,
    next_section=None,
    reader_experience=None,
    intent_brief=None,
) -> ManuscriptSectionGeneration:
    client = get_gemini_client()

    if reader_experience is None:
        class LegacyReaderExperience:
            reader_job = "Deliver the section's approved objective clearly and practically."
            reader_question = "What does the reader need to understand or decide here?"
            desired_reaction = "The reader feels clear about the next useful step."
            experience_type = "explanation with a concrete example or action"
            visual_decision = "No visual plan supplied. Do not add decorative visuals."
            interactive_element = "None unless the approved section material clearly requires one."
            evidence_anchor = "Use only the supplied opportunity and section planning context."
            claim_boundary = "Do not present unsupported measurements, statistics, testimonials, or industry facts as established evidence."
            reader_action = "Complete the concrete action specified by the section brief and content blueprint."
            transition_intent = "Connect naturally to the next approved section."
            avoid = "Generic filler, unsupported claims, repetition, and unnecessary decoration."

        reader_experience = LegacyReaderExperience()

    target_word_count = content_blueprint.target_word_count or 900
    target_word_count = max(400, min(target_word_count, 1800))

    previous_context = "None. This is the first section."
    if previous_section is not None:
        previous_context = (
            f"Previous section title: {previous_section.title}\n"
            f"Use its existence only to avoid repeating material and to make the opening feel connected."
        )

    next_context = "None. This is the final section."
    if next_section is not None:
        next_context = (
            f"Next section title: {next_section.title}\n"
            f"End this section with a natural forward-looking transition that makes the next section feel necessary."
        )

    prompt = f"""
You are NOVA's Manuscript Writer.

Write ONE finished manuscript section for a digital product.

This is not a planning task. Return the actual reader-facing prose that could be placed directly into the final product.
Do not describe what you are doing. Do not mention NOVA, AI, prompts, blueprints, or these instructions.

The writing must feel human, specific, useful, and naturally written. Favor clear explanations, concrete situations, varied sentence rhythm, and practical detail. Do not pad the section to reach the target length.

HARD WRITING RULES
- No long dashes.
- No generic AI filler.
- No fake statistics or unsupported factual claims.
- Do not present a proposed solution, workflow, measurement, or recommendation as an established industry fact.
- Follow the Reader Experience Plan for the intended reaction and reader action.
- If the plan says no visual or no interactive element, do not invent one in the prose.
- Respect the claim boundary: distinguish observed evidence from inference and recommendation.
- No invented testimonials, credentials, research findings, guarantees, or expert authority.
- Do not assume a US setting, US currency, or American names unless the supplied context requires them.
- Do not use a salesy or corporate training-manual tone.
- Do not begin with phrases such as "In this section, you will" or "Let's dive in".
- Do not repeat the same idea in multiple forms just to add length.
- Do not add a conclusion that merely summarizes every paragraph.
- Use headings only when they genuinely improve readability. Avoid a heading every few paragraphs.
- Checklists or short bullet lists are allowed when they make an action clearer.
- Address the supplied misconception or objection naturally rather than announcing it as a template field.
- Include the supplied example scenario when useful, but write it as a believable situation rather than a motivational story.
- The reader action must be concrete and usable.
- The transition to the next section should create forward momentum without repeating the current section's conclusion.

TARGET LENGTH
Aim for approximately {target_word_count} words. This is a target, not a quota.

PRODUCT FORMAT
{product_format}

OPPORTUNITY
Industry: {opportunity.industry}
Niche: {opportunity.niche}
Opportunity title: {opportunity.title}
Problem: {opportunity.problem}

PRODUCT PROMISE
Title: {summary.title}
Subtitle: {summary.subtitle}
About: {summary.about}
What the customer will learn:
{summary.what_youll_learn}

CUSTOMER TRANSFORMATION
Before emotional state: {transformation.before_emotional_state}
Before core fear: {transformation.before_core_fear}
Before daily experience: {transformation.before_daily_experience}
Before identity: {transformation.before_identity}
After emotional state: {transformation.after_emotional_state}
After core fear: {transformation.after_core_fear}
After daily experience: {transformation.after_daily_experience}
After identity: {transformation.after_identity}

CURRENT SECTION
Position: {section.position}
Title: {section.title}
Purpose: {section.purpose}

SECTION BRIEF
Objective: {section_brief.objective}
Key concepts:
{section_brief.key_concepts}
Practical steps:
{section_brief.practical_steps}
Example scenario: {section_brief.example_scenario}
Common mistakes:
{section_brief.common_mistakes}
Reader outcome: {section_brief.reader_outcome}

CONTENT BLUEPRINT
Hook angle: {content_blueprint.hook_angle}
Core explanation: {content_blueprint.core_explanation}
Supporting points:
{content_blueprint.supporting_points}
Reader action: {content_blueprint.reader_action}
Example scenario: {content_blueprint.example_scenario}
Misconception or objection: {content_blueprint.misconception_or_objection}
Transition to next: {content_blueprint.transition_to_next}
Avoid:
{content_blueprint.avoid}

READER EXPERIENCE PLAN
Reader job: {reader_experience.reader_job}
Reader question: {reader_experience.reader_question}
Desired reaction: {reader_experience.desired_reaction}
Experience type: {reader_experience.experience_type}
Visual decision: {reader_experience.visual_decision}
Interactive element: {reader_experience.interactive_element}
Evidence anchor: {reader_experience.evidence_anchor}
Claim boundary: {reader_experience.claim_boundary}
Reader action: {reader_experience.reader_action}
Transition intent: {reader_experience.transition_intent}
Avoid: {reader_experience.avoid}

INTENT VALIDATION CONTEXT
Target customer: {getattr(intent_brief, "target_customer", "")}
Specific problem context: {getattr(intent_brief, "problem_context", "")}
Customer language: {getattr(intent_brief, "customer_language", "")}
Solution gap: {getattr(intent_brief, "solution_gap", "")}
Evidence summary: {getattr(intent_brief, "evidence_summary", "")}

SEQUENCE CONTEXT
{previous_context}

{next_context}

WRITE THE SECTION NOW
Return only the manuscript content.
"""

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]

    last_error = None

    for model_name in models_to_try:
        try:
            print(
                f"Trying Gemini model for manuscript section {section.position}: "
                f"{model_name}"
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ManuscriptSectionGeneration,
                    temperature=0.65,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )

            if not response.parsed:
                raise RuntimeError(
                    f"{model_name} returned a response that NOVA could not parse."
                )

            content = _validate_manuscript_content(response.parsed.content)
            result = ManuscriptSectionGeneration(content=content)

            print(
                f"Successfully generated manuscript section {section.position} "
                f"with: {model_name} ({_count_words(content)} words)"
            )

            return result

        except ServerError as error:
            status_code = (
                getattr(error, "code", None)
                or getattr(error, "status_code", None)
            )

            if status_code != 503:
                raise

            last_error = error
            print(
                f"{model_name} is temporarily unavailable. "
                "Trying the next model..."
            )
            time.sleep(1)

        except RuntimeError as error:
            last_error = error
            print(
                f"{model_name} did not produce a valid manuscript section. "
                "Trying the next model..."
            )

    raise RuntimeError(
        "Gemini could not produce a valid manuscript section. "
        "Please try generating the section again."
    ) from last_error



class ProblemEvidenceItem(BaseModel):
    source_title: str = Field(description="Title of the public source that supports this problem.")
    source_url: str = Field(description="Exact public URL returned by Google Search for this source.")
    source_type: str = Field(description="Type of source, such as forum, Q&A, review, discussion, job posting, or article.")
    signal_type: str = Field(description="What this source demonstrates, such as pain, solution seeking, failed attempt, spending, workaround, or consequence.")
    excerpt: str = Field(description="A short faithful paraphrase of the relevant evidence. Do not invent a quote.")


class ProblemDiscoveryCandidate(BaseModel):
    market_direction: str = Field(description="Broad market direction. This is context, not proof of demand.")
    customer_group: str = Field(description="A specific customer group supported by the evidence.")
    situation: str = Field(description="The concrete recurring situation in which the problem appears.")
    problem: str = Field(description="One precise problem repeatedly demonstrated by the public evidence.")
    trigger: str = Field(description="The event or situation that causes the customer to urgently seek a solution.")
    current_behavior: str = Field(description="What people are actually doing now, including workarounds or failed attempts shown by the evidence.")
    pain_summary: str = Field(description="What the evidence indicates about the severity or frustration of the problem.")
    economic_consequence: str = Field(description="Documented or clearly described time, money, revenue, risk, or opportunity cost associated with the problem. Do not invent numbers.")
    existing_attempts: str = Field(description="Existing solutions, tools, services, or workarounds people report trying.")
    solution_seeking: str = Field(description="Evidence that people are actively asking for recommendations, alternatives, instructions, or a better solution.")
    spending_signal: str = Field(description="Evidence of existing spending, paid workarounds, or willingness-to-pay language. Say 'not found' if absent.")
    repeated_pattern: str = Field(description="Why this appears to be a repeated problem rather than one isolated complaint.")
    evidence_confidence: str = Field(description="Conservative confidence level based on source quality, repetition, and strength of buying signals. Use low, moderate, or high.")
    evidence_summary: str = Field(description="Short explanation of why the collected sources support investigating this exact problem.")
    evidence_items: list[ProblemEvidenceItem] = Field(
        min_length=3,
        max_length=8,
        description="At least three independent public sources that directly support the problem."
    )


class ProblemDiscoveryGeneration(BaseModel):
    problems: list[ProblemDiscoveryCandidate] = Field(
        min_length=4,
        max_length=6,
        description="A small set of evidence-backed problems. Quality is more important than quantity."
    )


class ResearchDirection(BaseModel):
    market_direction: str = Field(description="A broad market direction to investigate.")
    customer_group_hint: str = Field(description="A concrete customer group to investigate, without claiming that its problem is real yet.")
    search_queries: list[str] = Field(
        min_length=3,
        max_length=5,
        description="Public-web search queries designed to find pain, failed attempts, workarounds, and active solution seeking."
    )


class ResearchDirectionGeneration(BaseModel):
    directions: list[ResearchDirection] = Field(min_length=8, max_length=10)


def _value(item, name, default=None):
    if item is None:
        return default
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _extract_grounding_sources(response):
    """Compatibility helper retained for older callers."""
    sources = []

    candidates = _value(response, "candidates", []) or []
    for candidate in candidates:
        metadata = _value(candidate, "grounding_metadata")
        chunks = _value(metadata, "grounding_chunks", []) or []

        for chunk in chunks:
            web = _value(chunk, "web")
            if web is None:
                continue

            url = _value(web, "uri")
            title = _value(web, "title") or "Public web source"
            if not url:
                continue

            sources.append({"url": url, "title": title})

    return _dedupe_sources(sources)


def _dedupe_sources(sources):
    unique = []
    seen = set()

    for source in sources:
        url = (source.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(source)

    return unique


def _search_public_web(query, max_results=5):
    """Search public web sources without a paid search API or Gemini grounding."""
    if DDGS is None:
        raise RuntimeError(
            "The free web-search dependency is missing. Install it with: pip install ddgs"
        )

    results = []
    try:
        with DDGS(timeout=10) as search_client:
            for result in search_client.text(
                query,
                max_results=max_results,
                safesearch="moderate",
            ):
                url = result.get("href") or result.get("url")
                if not url:
                    continue
                results.append(
                    {
                        "url": url.strip(),
                        "title": (result.get("title") or "Public web source").strip(),
                        "snippet": (result.get("body") or result.get("snippet") or "").strip(),
                    }
                )
    except Exception as exc:
        print(f"Public web search failed for query '{query}': {exc}")
        return []

    return _dedupe_sources(results)


def _fetch_public_page(url, max_chars=6500):
    """Fetch a public page and extract readable text with only stdlib dependencies."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return ""

        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/153.0 Safari/537.36"
                )
            },
        )
        with urlopen(request, timeout=8) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower():
                return ""
            raw = response.read(1_500_000)

        html = raw.decode("utf-8", errors="ignore")
        html = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header).*?>.*?</\1>", " ", html)
        html = re.sub(r"(?is)<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", html).strip()
        return text[:max_chars]
    except Exception:
        return ""


def _collect_evidence_sources(direction, seed_sources=None, max_sources=16):
    """Collect independent public evidence, optionally starting with already-verified sources."""
    collected = []

    for source in seed_sources or []:
        url = source.get("url") or source.get("source_url")
        if not url:
            continue
        collected.append(
            {
                "url": url.strip(),
                "title": (source.get("title") or source.get("source_title") or "Public web source").strip(),
                "snippet": (source.get("snippet") or source.get("excerpt") or "").strip(),
                "page_text": (source.get("page_text") or "").strip(),
            }
        )

    collected = _dedupe_sources(collected)

    for query in direction.search_queries[:7]:
        if len(collected) >= max_sources:
            break

        print(f"Public web search: {query}")
        results = _search_public_web(query, max_results=5)
        collected.extend(results)
        collected = _dedupe_sources(collected)

    enriched = []

    for source in collected[:max_sources]:
        page_text = source.get("page_text", "")
        if not page_text:
            page_text = _fetch_public_page(source["url"])

        enriched.append(
            {
                "url": source["url"],
                "title": source["title"],
                "snippet": source.get("snippet", ""),
                "page_text": page_text,
            }
        )

    return enriched


def _format_evidence_bundle(sources):
    blocks = []
    for index, source in enumerate(sources, start=1):
        blocks.append(
            f"SOURCE {index}\n"
            f"TITLE: {source['title']}\n"
            f"URL: {source['url']}\n"
            f"SEARCH SNIPPET: {source.get('snippet', '')[:1200]}\n"
            f"PAGE TEXT: {source.get('page_text', '')[:5000]}"
        )
    return "\n\n".join(blocks)

def _source_domains(sources):
    from urllib.parse import urlparse

    domains = set()
    for source in sources:
        try:
            host = urlparse(source["url"]).netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            if host:
                domains.add(host)
        except Exception:
            continue
    return domains


def _contains_long_dash(text):
    return "—" in text or "–" in text


def _generate_research_directions(client):
    prompt = """
You are NOVA's market research planner.

Generate research directions for discovering REAL customer problems that people may pay to solve. Do not generate products and do not claim that any problem is already validated.

Explore widely across consumer, professional, education, finance, home, local services, hobbies, relationships, work, health-adjacent non-medical workflows, creator businesses, trades, small businesses, and other markets. There is no fixed industry list.

For each direction, give a concrete customer group and 3 to 5 public-web search queries designed to uncover:
- repeated complaints
- active requests for help or recommendations
- failed attempts
- manual or expensive workarounds
- existing spending
- lost time, money, revenue, opportunities, or increased risk

Prefer queries that can surface first-person discussions, public Q&A, reviews, community conversations, job postings, and other direct evidence. Avoid queries that mostly return generic marketing articles.

Do not use the user's technical background to choose directions. Do not use vague audiences such as 'everyone', 'busy people', or 'entrepreneurs'.
"""

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]

    last_error = None

    failures = []

    for attempt, model_name in enumerate(models_to_try):
        try:
            print(f"Trying Gemini planning model: {model_name}")

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ResearchDirectionGeneration,
                    temperature=0.8,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )

            if not response.parsed:
                raise RuntimeError("No structured research directions were returned.")

            direction_count = len(response.parsed.directions)
            if not 8 <= direction_count <= 10:
                raise RuntimeError(
                    f"Model returned {direction_count} research directions; NOVA requires 8 to 10."
                )

            print(
                f"Research directions generated with: {model_name} "
                f"({direction_count} directions)"
            )
            return response.parsed.directions

        except RuntimeError as error:
            # Structured-output/validation failures should also fall through to the
            # next planning model instead of aborting the entire discovery request.
            last_error = error
            failures.append(f"{model_name}: invalid response: {error}")
            print(
                f"{model_name} returned invalid research directions: {error}. "
                "Trying the next planning model..."
            )
            time.sleep(1)

        except Exception as error:
            status_code = _gemini_status_code(error)
            if status_code not in (429, 503):
                raise

            last_error = error
            error_message = _gemini_error_message(error)
            failures.append(
                f"{model_name}: HTTP {status_code}: {error_message}"
            )
            print(
                f"{model_name} returned {status_code}: {error_message}. "
                "Trying the next planning model..."
            )

            # Do not repeatedly hammer a model after a quota/service response.
            # A short delay gives transient failures a chance to recover while
            # still allowing the fallback chain to proceed quickly.
            time.sleep(2 ** min(attempt, 2))

    failure_summary = " | ".join(failures)
    raise RuntimeError(
        "Gemini could not create research directions with any configured planning "
        f"model. Model attempts: {failure_summary}"
    ) from last_error


def _verify_problem_with_web(client, direction):
    """Analyze independently collected public evidence with Gemini.

    Gemini is deliberately NOT the web-search layer here. The evidence has to
    exist first, so the model cannot manufacture URLs or pretend that a
    plausible scenario is evidence.
    """
    sources = _collect_evidence_sources(direction)

    if len(sources) < 6:
        print(
            f"Evidence collection rejected {direction.market_direction}: "
            f"only {len(sources)} usable public sources found."
        )
        return None, []

    domains = _source_domains(sources)
    if len(domains) < 2:
        print(
            f"Evidence collection rejected {direction.market_direction}: "
            f"only {len(domains)} source domain(s) found."
        )
        return None, []

    evidence_bundle = _format_evidence_bundle(sources)

    prompt = f"""
You are NOVA's evidence analyst. The web evidence below was collected independently by NOVA.
You MUST reason only from this supplied evidence. Do not browse, invent, or fill missing facts.

Your job is to determine whether the evidence demonstrates ONE genuine, specific customer problem
that is painful enough to plausibly create buying behavior.

RESEARCH DIRECTION
Market: {direction.market_direction}
Customer group hint: {direction.customer_group_hint}

EVIDENCE RULES
A candidate should only be accepted when the supplied sources support a meaningful combination of:
1. a specific identifiable customer group,
2. a recurring concrete situation,
3. a real pain or consequence,
4. active solution seeking OR a costly/manual workaround,
5. repeated independent evidence.

Stronger evidence includes existing spending, paid workarounds, failed attempts, lost revenue,
lost billable time, recurring costs, penalties, risk, or explicit willingness-to-pay language.

IMPORTANT
- Search snippets are leads, not proof. Prefer claims supported by actual page text.
- Do not treat generic SEO articles as direct evidence of customer pain.
- Do not invent source content that is not present below.
- Do not invent statistics, quotes, survey results, search volume, testimonials, spending, or willingness to pay.
- If the evidence is weak or contradictory, reject the problem rather than forcing an answer.
- If direct spending or willingness-to-pay evidence is absent, say "not found".
- Evidence items must use URLs from the supplied source list exactly.
- A source can support more than one signal, but do not pretend that one source represents many independent customers.
- Do not recommend a product or format.
- Do not call the problem profitable.
- Do not use em dashes or en dashes.

SUPPLIED PUBLIC EVIDENCE
{evidence_bundle}
"""

    models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash-lite"]
    last_error = None

    for attempt, model_name in enumerate(models_to_try):
        try:
            print(
                f"Analyzing collected evidence: {model_name} | "
                f"{direction.market_direction} | {len(sources)} sources"
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ProblemDiscoveryCandidate,
                    temperature=0.2,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )

            if not response.parsed:
                raise RuntimeError("No structured evidence analysis returned.")

            candidate = response.parsed
            supplied_urls = {source["url"].rstrip("/") for source in sources}
            valid_items = []

            for item in candidate.evidence_items:
                if item.source_url.rstrip("/") not in supplied_urls:
                    continue
                valid_items.append(item)

            if len(valid_items) < 3:
                raise RuntimeError(
                    f"Gemini could substantiate only {len(valid_items)} supplied sources."
                )

            candidate.evidence_items = valid_items[:8]

            evidence_domains = {
                urlparse(item.source_url).netloc.lower().removeprefix("www.")
                for item in candidate.evidence_items
                if urlparse(item.source_url).netloc
            }
            if len(evidence_domains) < 2:
                raise RuntimeError("Accepted evidence did not span at least two domains.")

            combined_text = " ".join([
                candidate.market_direction,
                candidate.customer_group,
                candidate.situation,
                candidate.problem,
                candidate.trigger,
                candidate.current_behavior,
                candidate.pain_summary,
                candidate.economic_consequence,
                candidate.existing_attempts,
                candidate.solution_seeking,
                candidate.spending_signal,
                candidate.repeated_pattern,
                candidate.evidence_summary,
            ])

            if _contains_long_dash(combined_text):
                raise RuntimeError("Evidence result contained an em dash or en dash.")

            weak_phrases = {
                "not found",
                "none found",
                "no evidence",
                "unclear",
                "unknown",
                "not available",
                "no direct evidence",
            }

            spending = candidate.spending_signal.strip().lower()
            seeking = candidate.solution_seeking.strip().lower()
            consequence = candidate.economic_consequence.strip().lower()

            has_spending = not any(phrase in spending for phrase in weak_phrases)
            has_seeking = not any(phrase in seeking for phrase in weak_phrases)
            has_consequence = not any(phrase in consequence for phrase in weak_phrases)

            if not has_spending and not (has_seeking and has_consequence):
                raise RuntimeError(
                    "Evidence lacks both a spending signal and the combination of active solution seeking plus meaningful consequence."
                )

            print(
                f"Verified evidence-backed problem: {candidate.problem} "
                f"({len(candidate.evidence_items)} sources, {len(evidence_domains)} domains)"
            )
            return candidate, [
                {
                    "url": item.source_url,
                    "title": item.source_title,
                }
                for item in candidate.evidence_items
            ]

        except RuntimeError as error:
            # A valid Gemini response can still fail NOVA's evidence gate.
            # Treat that as a candidate rejection, not as a fatal discovery error.
            last_error = error
            print(f"Evidence candidate rejected: {error}")
            return None, []

        except Exception as error:
            status_code = _gemini_status_code(error)
            if status_code not in (429, 503):
                raise
            last_error = error
            print(
                f"{model_name} returned {status_code}: {_gemini_error_message(error)}. "
                "Trying the next analysis model..."
            )
            time.sleep(1)

    if last_error:
        print(f"All Gemini analysis models failed: {last_error}")
    return None, []


INTENT_SIGNAL_TYPES = Literal[
    "customer_pain",
    "solution_seeking",
    "spending",
    "failed_attempt",
    "workaround",
    "economic_consequence",
    "existing_solution",
    "customer_language",
]


class IntentEvidenceItem(BaseModel):
    source_title: str = Field(description="Title of the public source.")
    source_url: str = Field(description="Exact URL from the supplied evidence.")
    source_type: str = Field(description="Type of public source.")
    signal_type: INTENT_SIGNAL_TYPES = Field(
        description=(
            "Exactly one primary signal category. Use one of: customer_pain, "
            "solution_seeking, spending, failed_attempt, workaround, "
            "economic_consequence, existing_solution, customer_language."
        )
    )
    excerpt: str = Field(
        description="A short faithful paraphrase of the relevant evidence. Do not invent a quote."
    )


class IntentValidationGeneration(BaseModel):
    target_customer: str
    problem_context: str
    trigger: str
    current_behavior: str
    failed_alternatives: str
    desired_outcome: str
    constraints: str
    objections: str
    customer_language: str
    existing_solutions: str

    solution_gap: str = Field(
        description=(
            "Evidence-grounded inference describing what existing approaches do not "
            "adequately address. Clearly phrase it as an inference."
        )
    )
    potential_solution: str = Field(
        description=(
            "A plausible solution concept derived from the evidence. This is a hypothesis, "
            "not proof of demand."
        )
    )
    recommended_format: str = Field(
        description=(
            "One suitable digital delivery format, such as ebook, course, workbook, "
            "toolkit, checklist bundle, templates, spreadsheet, challenge, resource pack, "
            "PPT/deck, PDF guide, hybrid product, or another appropriate format."
        )
    )
    why_format: str = Field(
        description="Why the recommended format fits the problem and desired outcome."
    )
    validation_questions: str = Field(
        description=(
            "3 to 6 concrete questions for direct customer validation, especially questions "
            "that test current behavior, urgency, existing spending, and willingness to pay. "
            "Put one question per line."
        )
    )
    evidence_confidence: str = Field(
        description="Evidence strength only. Use low, moderate, or high. Never imply profitability."
    )
    evidence_summary: str
    evidence_items: list[IntentEvidenceItem] = Field(min_length=4, max_length=10)


def _intent_search_terms(text, limit=7):
    stop_words = {
        "the", "and", "for", "with", "without", "from", "into", "that", "this",
        "their", "they", "them", "are", "is", "an", "a", "of", "to", "in", "on",
        "by", "or", "due", "using", "across", "during", "about", "very", "specific",
        "efficient", "difficulty", "difficult", "accurately", "accurate", "requiring",
        "managing", "management", "system", "systems", "data", "current",
    }
    words = re.findall(r"[A-Za-z0-9]+", text.lower())
    terms = []
    for word in words:
        if len(word) < 4 or word in stop_words or word in terms:
            continue
        terms.append(word)
        if len(terms) >= limit:
            break
    return terms


def _intent_research_queries(problem):
    customer_terms = _intent_search_terms(problem.customer_group, limit=5)
    problem_terms = _intent_search_terms(problem.problem, limit=7)
    situation_terms = _intent_search_terms(problem.situation, limit=5)

    customer = " ".join(customer_terms) or "small business owners"
    problem_text = " ".join(problem_terms) or "workflow problems"
    situation = " ".join(situation_terms)

    queries = [
        f"{customer} {problem_text} complaints",
        f"{customer} {problem_text} recommendations",
        f"{customer} {problem_text} alternatives",
        f"{customer} {problem_text} spreadsheet OR manual",
        f"{customer} {problem_text} software OR tool",
        f"{customer} {problem_text} cost OR price OR paid",
        f"{customer} {situation} problems forum OR reddit",
    ]

    # Avoid duplicate queries while preserving intentionally broad variants.
    return list(dict.fromkeys(queries))


def generate_intent_validation(problem) -> IntentValidationGeneration:
    client = get_gemini_client()

    direction = ResearchDirection(
        market_direction=problem.market_direction or "Target customer problem",
        customer_group_hint=problem.customer_group,
        search_queries=_intent_research_queries(problem),
    )

    seed_sources = []
    for item in getattr(problem, "existing_evidence", []) or []:
        seed_sources.append(
            {
                "source_url": getattr(item, "source_url", ""),
                "source_title": getattr(item, "source_title", "Public web source"),
                "source_type": getattr(item, "source_type", ""),
                "signal_type": getattr(item, "signal_type", ""),
                "excerpt": getattr(item, "excerpt", ""),
            }
        )

    sources = _collect_evidence_sources(
        direction,
        seed_sources=seed_sources,
        max_sources=16,
    )

    if len(sources) < 6:
        raise RuntimeError(
            f"INTENT could only collect {len(sources)} usable public sources. "
            "NOVA will not manufacture evidence to fill the brief."
        )

    domains = _source_domains(sources)
    if len(domains) < 2:
        raise RuntimeError(
            "INTENT evidence came from fewer than two independent domains."
        )

    evidence_bundle = _format_evidence_bundle(sources)

    prompt = f"""
You are NOVA's INTENT validation analyst.

A problem candidate has already passed NOVA's initial evidence gate. Your job is to
investigate it more deeply using ONLY the public evidence supplied below.

Do not browse. Do not invent facts, quotes, statistics, customer counts, spending,
search volume, willingness to pay, or market size.

IMPORTANT DISTINCTIONS:
- Observed evidence = directly supported by supplied sources.
- Inference = a reasoned interpretation of multiple observed signals.
- Hypothesis = a proposed solution or format that still needs validation.
Never present an inference or hypothesis as observed evidence.
Never call the opportunity profitable or validated.
Evidence confidence describes evidence strength only. It is not a sales probability.

INVESTIGATE:
1. Who specifically experiences the problem?
2. In what recurring context?
3. What triggers the problem?
4. What are people doing now?
5. What alternatives, tools, services, or workarounds have they tried?
6. What appears to fail, remain manual, expensive, fragmented, or inconvenient?
7. What outcome do people appear to want?
8. What constraints or objections are visible?
9. What customer language repeats across sources?
10. What existing solutions already exist?
11. Based on the evidence, what solution gap can reasonably be inferred?
12. Propose one plausible solution hypothesis.
13. Recommend the most suitable digital delivery format for that solution hypothesis.
14. Give direct validation questions that could test willingness to pay.

EVIDENCE RULES:
- Search snippets are leads. Prefer actual page text.
- Do not treat generic marketing copy as customer evidence.
- Each evidence item must use a URL from the supplied source list exactly.
- Do not pretend one source represents multiple independent customers.
- Include diverse source types where available.
- Do not fabricate missing spending signals. If spending evidence is absent, say "not found".
- Assign each evidence item exactly one signal_type from the controlled categories.
- Use customer_pain or customer_language only when the source contains customer-originated language or a concrete customer complaint/problem description.
- Use solution_seeking only when the source actually shows someone asking for help, recommendations, alternatives, or instructions.
- Use spending only when the source contains a real paid solution, price, purchase, paid workaround, or explicit willingness-to-pay language.
- Use failed_attempt or workaround only when a person or business reports trying something that did not adequately solve the problem or describes a manual workaround.
- Use economic_consequence only when the source describes time, money, revenue, risk, delay, or another concrete consequence.
- Use existing_solution only when the source primarily documents an existing tool, service, or alternative. Existing solution evidence is not the same thing as solution-seeking evidence.
- Do not use em dashes or en dashes.

INITIAL PROBLEM
Customer group: {problem.customer_group}
Situation: {problem.situation}
Problem: {problem.problem}
Trigger: {problem.trigger}
Current behavior: {problem.current_behavior}

EXISTING DISCOVERY EVIDENCE
Pain: {problem.evidence_profile.pain_summary if getattr(problem, "evidence_profile", None) else ""}
Economic consequence: {problem.evidence_profile.economic_consequence if getattr(problem, "evidence_profile", None) else ""}
Existing attempts: {problem.evidence_profile.existing_attempts if getattr(problem, "evidence_profile", None) else ""}
Solution seeking: {problem.evidence_profile.solution_seeking if getattr(problem, "evidence_profile", None) else ""}
Spending signal: {problem.evidence_profile.spending_signal if getattr(problem, "evidence_profile", None) else ""}
Repeated pattern: {problem.evidence_profile.repeated_pattern if getattr(problem, "evidence_profile", None) else ""}

SUPPLIED PUBLIC EVIDENCE
{evidence_bundle}
"""

    models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash-lite"]
    last_error = None

    for model_name in models_to_try:
        try:
            print(
                f"Analyzing INTENT evidence: {model_name} | "
                f"{problem.problem} | {len(sources)} sources"
            )

            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=IntentValidationGeneration,
                    temperature=0.2,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )

            if not response.parsed:
                raise RuntimeError("No structured INTENT validation returned.")

            result = response.parsed
            supplied_urls = {source["url"].rstrip("/") for source in sources}
            valid_items = [
                item
                for item in result.evidence_items
                if item.source_url.rstrip("/") in supplied_urls
            ]

            if len(valid_items) < 4:
                raise RuntimeError(
                    f"INTENT could substantiate only {len(valid_items)} supplied sources."
                )

            result.evidence_items = valid_items[:10]

            evidence_domains = {
                urlparse(item.source_url).netloc.lower().removeprefix("www.")
                for item in result.evidence_items
                if urlparse(item.source_url).netloc
            }

            if len(evidence_domains) < 2:
                raise RuntimeError(
                    "INTENT evidence did not span at least two independent domains."
                )

            combined_text = " ".join(
                [
                    result.target_customer,
                    result.problem_context,
                    result.trigger,
                    result.current_behavior,
                    result.failed_alternatives,
                    result.desired_outcome,
                    result.constraints,
                    result.objections,
                    result.customer_language,
                    result.existing_solutions,
                    result.solution_gap,
                    result.potential_solution,
                    result.recommended_format,
                    result.why_format,
                    result.validation_questions,
                    result.evidence_summary,
                ]
            )

            if _contains_long_dash(combined_text):
                raise RuntimeError(
                    "INTENT result contained an em dash or en dash."
                )

            print(
                f"INTENT validation completed: {len(result.evidence_items)} sources, "
                f"{len(evidence_domains)} domains"
            )
            return result

        except RuntimeError as error:
            last_error = error
            print(
                f"INTENT validation failed with {model_name}: {error}. "
                "Trying the next INTENT analysis model..."
            )
            time.sleep(1)

        except Exception as error:
            status_code = _gemini_status_code(error)
            if status_code not in (429, 503):
                raise
            last_error = error
            print(
                f"{model_name} returned {status_code}: {_gemini_error_message(error)}. "
                "Trying the next INTENT analysis model..."
            )
            time.sleep(1)

    raise RuntimeError(
        "NOVA could not complete INTENT validation with sufficiently grounded evidence. "
        "Try the investigation again."
    ) from last_error

def generate_problem_discovery() -> ProblemDiscoveryGeneration:
    client = get_gemini_client()
    directions = _generate_research_directions(client)

    verified = []
    used_problems = set()

    for direction in directions:
        if len(verified) >= 6:
            break

        candidate, sources = _verify_problem_with_web(client, direction)
        if candidate is None:
            continue

        normalized_problem = " ".join(candidate.problem.lower().split())
        if normalized_problem in used_problems:
            continue

        used_problems.add(normalized_problem)
        verified.append(candidate)

    if len(verified) < 4:
        raise RuntimeError(
            f"NOVA found only {len(verified)} evidence-backed problems. "
            "It will not lower the evidence standard just to fill the screen. Try discovery again."
        )

    return ProblemDiscoveryGeneration(problems=verified)
