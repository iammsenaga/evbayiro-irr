# Contributing to Evbayiro-IRR

Bug reports, documentation improvements, and focused code contributions are welcome.

## Reporting an issue

Open an issue in the GitHub repository. Include the package version, Python version, a minimal cash-flow example, the RRR and other relevant parameters, the result you expected, and the result or error you observed. Do not include confidential company or project cash flows.

## Proposing a change

For a substantial change, open an issue first to discuss the intended behavior and its relationship to the RRR-First method. Submit changes as a pull request against `main`, with a concise description of the problem and solution. Keep pull requests focused and update tests and documentation when behavior or user-facing output changes.

## Tests

Run the test suite from the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

New behavior should include tests for expected results and relevant edge cases. Changes to the search or closure logic should preserve the distinction between the NPV decision at the supplied RRR and the reported IRR boundary.

## Review and support

The project maintainer reviews proposed changes for correctness, reproducibility, compatibility, and consistency with the documented method. The GitHub issue tracker is the public channel for bug reports and support questions. A contribution is not accepted until it has been reviewed and merged by the maintainer.
