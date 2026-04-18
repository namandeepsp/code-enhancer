TECHNOLOGY_HINTS: dict[str, str] = {
    # Python
    "fastapi":      "Use Pydantic v2 models, FastAPI dependency injection, proper HTTP status codes, and async functions.",
    "django":       "Follow Django ORM patterns, use class-based views where appropriate, respect Django's app structure.",
    "flask":        "Use Flask blueprints, proper error handlers, and Flask-SQLAlchemy patterns if DB is involved.",

    # JavaScript / TypeScript
    "express":      "Use async/await throughout, proper Express error middleware (4-arg), no callback hell.",
    "nextjs":       "Use App Router conventions, server components by default, client components only when needed.",
    "react":        "Functional components only, proper hook usage, no prop drilling — use context or state management.",
    "nestjs":       "Use NestJS decorators, dependency injection, proper module structure, DTOs with class-validator.",

    # Go
    "gin":          "Idiomatic Go error handling (return error, don't panic), context propagation, Gin middleware patterns.",
    "go":           "Standard library Go patterns, proper error wrapping with fmt.Errorf, table-driven tests.",

    # Java
    "spring-boot":  "Use @Service/@Repository separation, constructor injection (not field injection), proper exception handling.",
    "quarkus":      "Use Quarkus CDI, reactive patterns where appropriate, MicroProfile annotations.",

    # Database
    "sqlalchemy":   "Use SQLAlchemy 2.0 style (select() statements), proper session management, avoid N+1 queries.",
    "prisma":       "Use Prisma client patterns, proper transaction handling, type-safe queries.",
}
