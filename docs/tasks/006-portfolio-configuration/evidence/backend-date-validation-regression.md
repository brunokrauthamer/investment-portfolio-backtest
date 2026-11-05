## Exact date format regression

After the initial route implementation, the API contract test was extended to reject a numeric date (`0`) and an ISO datetime (`2024-12-31T00:00:00`). Before the fix, `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio -v` failed both new subcases: each returned HTTP 200 instead of 422 because Pydantic's `date` parser accepted those values.

The request model now checks that each date is a string matching `YYYY-MM-DD` and parses it as a real calendar date before field validation. The same focused suite passed all five tests afterward; see `backend-date-regression-green.txt`.
