"""Create a harmless local PDF for exercising the upload endpoint."""

from pathlib import Path

import fitz


def main() -> None:
    fixture_directory = Path(__file__).resolve().parents[1] / 'tests' / 'fixtures'
    pdf_path = fixture_directory / 'sample_notice.pdf'
    png_path = fixture_directory / 'sample_notice.png'
    fixture_directory.mkdir(parents=True, exist_ok=True)

    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), 'COLLEGE NOTICE')
    page.insert_text((72, 100), 'Exam forms must be submitted by 20 December 2026.')
    page.insert_text((72, 128), 'All final-year students should contact the Examination Cell.')
    document.save(pdf_path)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    pixmap.save(png_path)
    document.close()
    print(f'Created {pdf_path} and {png_path}')


if __name__ == '__main__':
    main()
