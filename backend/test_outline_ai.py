from ai_service import (
    OutlineGeneration,
    TransformationGeneration,
    generate_product_outline,
)


class DemoOpportunity:
    industry = "Personal Finance"
    niche = "Single-Income Households"
    title = "Paycheck-to-Paycheck Budgeting"
    problem = (
        "Helping single-income households stop running out of money "
        "before payday."
    )


class DemoTransformation:
    before_emotional_state = (
        "They feel anxious whenever payday gets close because they are "
        "never quite sure whether the remaining money will last."
    )

    before_core_fear = (
        "They worry that an unexpected expense will force them to borrow "
        "money or sacrifice something important."
    )

    before_daily_experience = (
        "They repeatedly check their bank balance, delay small purchases, "
        "and try to mentally calculate how many days remain until payday."
    )

    before_identity = (
        "They may see themselves as bad with money even though much of "
        "their difficulty comes from timing and cash-flow pressure."
    )

    after_emotional_state = (
        "They feel calmer and more in control because they know what "
        "their paycheck needs to cover and when."
    )

    after_core_fear = (
        "Unexpected expenses still exist, but they have a clearer plan "
        "for absorbing them without immediately destabilizing the month."
    )

    after_daily_experience = (
        "They follow a simple payday and weekly spending system that "
        "makes bills, essentials, irregular costs, and flexible spending "
        "easier to manage."
    )

    after_identity = (
        "They see themselves as capable of managing their household cash "
        "flow without needing a complicated budgeting system."
    )


class DemoProductSummary:
    title = "The Single-Income Budgeting Blueprint"

    subtitle = (
        "A four-week cash flow system for bills, groceries, and flexible spending."
    )

    about = (
        "A practical guide for single-income households that want to stop "
        "running out of money before payday while still leaving room for "
        "small everyday pleasures."
    )

    what_youll_learn = (
        "How to map a paycheck, separate spending categories, release "
        "weekly money, prepare for irregular expenses, and create a "
        "realistic spending rhythm."
    )

    estimated_reading_time = 60
    section_count = 8

    bonus_materials = (
        "Payday Map worksheet, weekly spending checklist, and irregular "
        "expense planning worksheet."
    )


result = generate_product_outline(
    DemoOpportunity(),
    DemoTransformation(),
    DemoProductSummary(),
    "ebook",
)


assert isinstance(result, OutlineGeneration)
assert 7 <= len(result.sections) <= 12

print("Product outline generated successfully!\n")
print(f"Number of sections: {len(result.sections)}\n")

for index, section in enumerate(result.sections, start=1):
    print(f"{index}. {section.title}")
    print(f"   Purpose: {section.purpose}")
    print()