# Frontend conventions

Use TypeScript and React. Keep reusable presentation and shared business components in `src/components`; pages, page-specific components and local logic in `src/pages`; static assets in `src/assets`; API and external communication without JSX or UI hooks in `src/services`; reusable functions and constants without React, global state or browser side effects in `src/shared`; and shared state, sessions, caches, subscriptions and their coordination in `src/store`.

Keep component- and page-specific hooks near their consumers. Hooks subscribing to a cache or session belong with that infrastructure; do not place hooks in `shared` automatically. Use PascalCase for component and page names, descriptive names for functions and hooks, and reserve the `use` prefix for hooks.

Use `index.tsx` for component and page entry files, with local `index.css` when needed. Do not create empty CSS files or purposeless directories. Place unit tests near the code as `*.test.ts` or `*.test.tsx`; cross-module integration tests may have a dedicated directory. Prefer explicit imports over a central component barrel. Preserve compatible existing conventions and avoid unrelated migrations.

Use semantic HTML and look for existing controls before creating new ones. Visual primitives receive data and callbacks, preserving native attributes, refs, accessibility and keyboard behavior. Buttons default to `type="button"`; submit explicitly, name icon-only actions, and communicate pending states while preventing duplicate actions. Prefer native selects unless requirements justify otherwise. Distinguish loading, refresh, success and error states; do not treat failures as empty data or zero.
