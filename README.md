# PDFCrowd Python SDK

The Python SDK provides API clients for converting HTML, PDF, and images.
It supports Python 2.7 and Python 3 and has no third-party runtime dependencies.

```sh
python -m pip install pdfcrowd
```

See the [Python documentation](https://pdfcrowd.com/api/client-library/python/)
for authentication, conversion examples, and API references.

## Migrating converter commands

Starting with version 7.0.0, this package contains only the Python API. The
`html2pdf`, `html2image`, `image2pdf`, `image2image`, `pdf2pdf`, `pdf2html`,
`pdf2text`, and `pdf2image` commands are provided by `pdfcrowd-cli`.
The CLI requires Python 3.8 or later; the SDK continues to support Python 2.7.

Install the CLI with pipx:

```sh
pipx install pdfcrowd-cli
html2pdf --help
```

Or install it in your Python virtual environment:

```sh
python -m pip install pdfcrowd-cli
html2pdf --help
```

The CLI installs a compatible SDK automatically. Python applications that
import `pdfcrowd` continue to use the API clients directly.
