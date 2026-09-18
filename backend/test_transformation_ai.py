from ai_service import TransformationGeneration, generate_transformation_map


class DemoOpportunity:
    industry = "Personal Finance"
    niche = "Single-Income Households"
    title = "Paycheck-to-Paycheck Budgeting"
    problem = "Helping single-income households stop running out of money before payday."


result = generate_transformation_map(DemoOpportunity())

assert isinstance(result, TransformationGeneration)

print("Transformation generated successfully!\n")
print(result.model_dump_json(indent=2))
