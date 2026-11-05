# API module guidance

- Keep each controller thin: declare the HTTP route and its request/response contract, then call the relevant service. Controllers must not own application decisions, validation rules, catalogs, calculations, data access, or response construction beyond HTTP-specific translation.
- Put API application behavior in `service/`. Services own fixed catalogs and defaults, business validation, transformations, calculations, and orchestration. Keep services independent of FastAPI so they can be called directly.
- Keep Pydantic request and response shapes in `model/`. Use model validation for parsing and basic wire-shape/type checks; put cross-field and application rules in services.
- Keep HTTP-specific adapters such as request decoding in `transport/`, not in controllers or services. Wire routes, adapters, and exception handlers in the API application entry point.
- Have services raise API-independent errors for invalid application input. Translate those errors to HTTP status codes at the application boundary.
- Do not initiate network access or data acquisition during API import or startup.
