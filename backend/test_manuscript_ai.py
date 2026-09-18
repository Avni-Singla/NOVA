from models.opportunity import Opportunity
from models.transformation_map import TransformationMap
from models.product_summary import ProductSummary
from models.section import Section
from models.section_brief import SectionBrief
from models.content_blueprint import ContentBlueprint
from ai_service import generate_manuscript_section


# This test uses a small hand-built context so the AI layer can be validated
# without changing the database or saving generated content.

opportunity = Opportunity(
    industry="Personal Finance",
    niche="Single-Income Households",
    title="Paycheck-to-Paycheck Budgeting",
    problem="Helping single-income households stop running out of money before payday.",
)

transformation = TransformationMap(
    before_emotional_state="Anxious and reactive whenever the account balance drops.",
    before_core_fear="Running out of money before the next payday.",
    before_daily_experience="Bills and ordinary spending compete for the same shrinking balance.",
    before_identity="Feels like someone who is always trying to catch up.",
    after_emotional_state="Calmer and more deliberate about everyday spending.",
    after_core_fear="Unexpected timing problems feel manageable instead of catastrophic.",
    after_daily_experience="Income, bills, weekly spending, and irregular costs have a simple working rhythm.",
    after_identity="Feels capable of managing a single income without constant panic.",
)

summary = ProductSummary(
    title="Single-Income Cash Flow Reset",
    subtitle="A practical system for making one paycheck last through the full cycle.",
    about="A practical guide for households that need a clearer rhythm for bills, spending, and irregular costs.",
    what_youll_learn="Map income and bill timing\nBuild a truthful spending baseline\nCreate a weekly spending rhythm",
    bonus_materials="Payday checklist",
)

section = Section(
    position=1,
    title="Understanding Your Paycheck Reality",
    purpose="Show why cash-flow timing can create stress even when total income appears sufficient.",
)

brief = SectionBrief(
    objective="Help the reader see the structural cash-flow problem clearly.",
    key_concepts="Income timing versus expense timing\nStructural shortfalls\nThe role of a cash-flow map",
    practical_steps="List income dates\nList major recurring bills\nCompare the dates",
    example_scenario="A monthly salary arrives on the first while several bills fall across the first three weeks.",
    common_mistakes="Blaming every shortfall on unnecessary spending.",
    reader_outcome="The reader can identify whether timing is contributing to the problem.",
)

blueprint = ContentBlueprint(
    hook_angle="The problem may be the calendar, not a lack of discipline.",
    core_explanation="Cash-flow stress can come from the timing mismatch between income and expenses.",
    supporting_points="Income timing versus expense timing\nDiscipline cannot fix a mismatched calendar",
    reader_action="Map income dates against the three largest recurring bills.",
    example_scenario="Salary arrives on the first, with rent on the first and other bills later in the month.",
    misconception_or_objection="Running out of money before payday must mean the household simply spends too much.",
    transition_to_next="Once the timing problem is visible, the next step is to see where the money actually goes.",
    avoid="Shaming the reader or making unsupported claims.",
    target_word_count=600,
)


result = generate_manuscript_section(
    opportunity,
    transformation,
    summary,
    section,
    brief,
    blueprint,
    "ebook",
)

word_count = len(result.content.split())
contains_em_dash = "—" in result.content
contains_en_dash = "–" in result.content

print("Manuscript section generated successfully!")
print("Word count:", word_count)
print("Target word count:", blueprint.target_word_count)
print("Contains em dash:", contains_em_dash)
print("Contains en dash:", contains_en_dash)
print("Contains normal hyphen:", "-" in result.content)
print()
print("Preview (first 1000 characters):")
print(result.content[:1000])

if contains_em_dash or contains_en_dash:
    raise RuntimeError(
        "Generated manuscript contains an em dash or en dash. "
        "The manuscript must use normal hyphens only."
    )

print()
print("Manuscript validation passed!")