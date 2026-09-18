from ai_service import (
    ContentBlueprintGenerationResponse,
    generate_content_blueprints,
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
    def __init__(self, section_id, position, title, purpose):
        self.id = section_id
        self.position = position
        self.title = title
        self.purpose = purpose


class DemoBrief:
    def __init__(self, section_id, objective, key_concepts, practical_steps, example_scenario, common_mistakes, reader_outcome):
        self.section_id = section_id
        self.objective = objective
        self.key_concepts = key_concepts
        self.practical_steps = practical_steps
        self.example_scenario = example_scenario
        self.common_mistakes = common_mistakes
        self.reader_outcome = reader_outcome


sections = [
    DemoSection(1, 1, "Understanding the Single-Income Reality", "Explain the core problem."),
    DemoSection(2, 2, "Mapping Your Actual Cash Flow", "Build a baseline."),
    DemoSection(3, 3, "Sequencing Bills to Match Pay Dates", "Align income and bills."),
    DemoSection(4, 4, "Establishing the Three-Tier Expense System", "Prioritize spending."),
    DemoSection(5, 5, "Capping Variable Daily Spending", "Control flexible spending."),
    DemoSection(6, 6, "Building a Starter Emergency Fund", "Create a small buffer."),
    DemoSection(7, 7, "Rebalancing Your Budget Mid-Month", "Adjust when plans change."),
    DemoSection(8, 8, "Maintaining Long-Term Financial Control", "Maintain the system."),
]

briefs = [
    DemoBrief(1, "Explain the core problem.", "Income timing", "Map the problem", "A realistic household cash-flow example.", "Treating the problem as a discipline failure.", "The reader understands the structural issue."),
    DemoBrief(2, "Build a baseline.", "Actual spending", "Review recent transactions", "A reader discovers forgotten small expenses.", "Relying on memory.", "The reader has a truthful baseline."),
    DemoBrief(3, "Align income and bills.", "Due-date timing", "Map bills against pay dates", "A bill arrives before the next paycheck.", "Assuming due dates cannot change.", "The reader sees the timing gaps."),
    DemoBrief(4, "Prioritize spending.", "Expense tiers", "Sort expenses into tiers", "A household separates essentials from flexible spending.", "Treating every expense as essential.", "The reader can prioritize quickly."),
    DemoBrief(5, "Control flexible spending.", "Weekly caps", "Set a realistic weekly limit", "A separate spending account protects bill money.", "Setting an unrealistic cap.", "The reader has a practical spending boundary."),
    DemoBrief(6, "Create a small buffer.", "Starter emergency fund", "Choose a reachable savings target", "A small buffer covers a routine surprise expense.", "Waiting for perfect finances before saving.", "The reader has a first layer of resilience."),
    DemoBrief(7, "Adjust when plans change.", "Mid-month rebalancing", "Shift money between categories", "A higher utility bill requires a deliberate adjustment.", "Abandoning the whole budget.", "The reader can adapt without panic."),
    DemoBrief(8, "Maintain the system.", "Review routine", "Schedule a short recurring review", "A payday check keeps the system current.", "Stopping after initial progress.", "The reader has a sustainable routine."),
]

result = generate_content_blueprints(
    DemoOpportunity(),
    DemoTransformation(),
    DemoSummary(),
    sections,
    briefs,
    "ebook",
)

assert isinstance(result, ContentBlueprintGenerationResponse)
assert len(result.blueprints) == 8
assert [item.position for item in result.blueprints] == list(range(1, 9))
assert all(400 <= item.target_word_count <= 1800 for item in result.blueprints)

print("Content blueprints generated successfully!")
print(f"Number of blueprints: {len(result.blueprints)}")

for blueprint in result.blueprints:
    print(f"\n{blueprint.position}.")
    print(f"Hook angle: {blueprint.hook_angle}")
    print(f"Core explanation: {blueprint.core_explanation}")
    print(f"Supporting points:\n{blueprint.supporting_points}")
    print(f"Reader action: {blueprint.reader_action}")
    print(f"Example: {blueprint.example_scenario}")
    print(f"Misconception or objection: {blueprint.misconception_or_objection}")
    print(f"Transition: {blueprint.transition_to_next}")
    print(f"Avoid:\n{blueprint.avoid}")
    print(f"Target word count: {blueprint.target_word_count}")
