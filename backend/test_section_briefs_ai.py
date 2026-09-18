from ai_service import (
    SectionBriefGenerationResponse,
    generate_section_briefs,
)


class DemoOpportunity:
    industry = "Personal Finance"
    niche = "Single-Income Households"
    title = "Paycheck-to-Paycheck Budgeting"
    problem = "Helping single-income households stop running out of money before payday."


class DemoTransformation:
    before_emotional_state = "Anxious about running out of money before payday."
    before_core_fear = "An unexpected bill will create a financial crisis."
    before_daily_experience = "Constantly checking balances and rationing spending."
    before_identity = "Feels unable to manage a single household income."
    after_emotional_state = "Calmer and more confident about daily spending."
    after_core_fear = "Unexpected costs are manageable rather than catastrophic."
    after_daily_experience = "Uses a clear spending rhythm and reaches payday with money left."
    after_identity = "Sees themselves as a capable household money manager."


class DemoSummary:
    title = "The Single-Income Cash Flow Reset"
    subtitle = "A practical framework for stopping paycheck-to-paycheck stress."
    about = "A practical guide for single-income households."
    what_youll_learn = "Map bills\nControl weekly spending\nPrepare for irregular expenses"
    bonus_materials = "Payday planner\nExpense checklist"


class DemoSection:
    def __init__(self, position, title, purpose):
        self.position = position
        self.title = title
        self.purpose = purpose


sections = [
    DemoSection(1, "Understanding the Single-Income Reality", "Explain the core problem."),
    DemoSection(2, "Mapping Your Actual Cash Flow", "Build a baseline."),
    DemoSection(3, "Sequencing Bills to Match Pay Dates", "Align income and bills."),
    DemoSection(4, "Establishing the Three-Tier Expense System", "Prioritize spending."),
    DemoSection(5, "Capping Variable Daily Spending", "Control flexible spending."),
    DemoSection(6, "Building a Starter Emergency Fund", "Create a small buffer."),
    DemoSection(7, "Rebalancing Your Budget Mid-Month", "Adjust when plans change."),
    DemoSection(8, "Maintaining Long-Term Financial Control", "Maintain the system."),
]

result = generate_section_briefs(
    DemoOpportunity(),
    DemoTransformation(),
    DemoSummary(),
    sections,
    "ebook",
)

assert isinstance(result, SectionBriefGenerationResponse)
assert len(result.briefs) == 8

print("Section briefs generated successfully!")
print(f"Number of briefs: {len(result.briefs)}")

for brief in result.briefs:
    print(f"\n{brief.position}.")
    print(f"Objective: {brief.objective}")
    print(f"Key concepts:\n{brief.key_concepts}")
    print(f"Practical steps:\n{brief.practical_steps}")
    print(f"Example: {brief.example_scenario}")
    print(f"Common mistakes:\n{brief.common_mistakes}")
    print(f"Reader outcome: {brief.reader_outcome}")
