from pathlib import Path
import tempfile

from packaging_service import generate_product_pdf


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "test-product.pdf"

        generate_product_pdf(
            str(output),
            "NOVA Packaging Test",
            "A reader-ready digital guide",
            "A short product description.",
            "Payday checklist\n- Review the calendar\n- Check the weekly limit",
            [
                (1, "Understanding the Problem", "# Understanding the Problem\n\nThis is the first section."),
                (2, "Build the System", "This is the second section.\n\n- Map the dates\n- Review the result"),
            ],
        )

        if not output.exists() or output.stat().st_size < 5000:
            raise RuntimeError("Packaging test did not produce a valid PDF file.")

        print("Product packaging test passed!")
        print("PDF size:", output.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
