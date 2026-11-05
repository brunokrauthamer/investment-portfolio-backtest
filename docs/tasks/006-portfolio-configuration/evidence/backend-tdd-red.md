TDD baseline run (before adding the portfolio router):

Command: `backend/.venv/Scripts/python.exe -m unittest backend.src.api.tests.test_portfolio -v`

Observed result: 5 tests ran and the suite failed with 14 assertions. `GET /api/indexes` returned HTTP 404 instead of 200, valid POSTs returned 404 instead of 200, and invalid POSTs returned 404 instead of the expected 422. These were behavior failures because the routes did not yet exist. The 7 backend route and health tests pass after the implementation.