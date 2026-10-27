# Database

Goal: each endpoint runs a small, fixed number of fast queries.

Applies only when the repo has a data layer (ORM, query builder, raw SQL). Never run against a production database; use the local or test database with seed data large enough to show the problem.

## Lighthouse audits (13.x)

Only indirect: `server-response-time` and `document-latency-insight` for server-rendered pages. Lighthouse cannot see queries; the numbers below are the baseline.

## Measure first

- Turn on query logging (an environment variable or local config, not a committed change; with `--audit`, only if it needs no project file change) for one request of each key endpoint, and save query count and total query time to `.perf/db-<endpoint>.json`:
  - Prisma: `log: ['query']`; Drizzle: `logger: true`; TypeORM: `logging: true`; Sequelize: `logging`; Django: `connection.queries` or django-debug-toolbar; Rails: the request log or `bullet`; SQLAlchemy: `echo=True`; Laravel: `DB::listen`.
- For each slow query: `EXPLAIN ANALYZE` (Postgres), `EXPLAIN` (MySQL, SQLite). Look for sequential scans on large tables, high row estimates, sorts on disk.
- Endpoint timing: server response time for the same request before and after.

## N+1: how to spot it

- The log shows one query for a list, then the same query shape repeated once per row (`SELECT ... WHERE parent_id = ?` × N).
- Code smell: a query or a lazy relation access inside a loop, a `map`, or a per-item resolver (GraphQL).

## Fixes, by frequency

1. **N+1**: eager load (`include` / `with` / `select_related` / `prefetch_related` / `includes` / `joinedload`), or batch (`WHERE id IN (...)`, DataLoader for GraphQL resolvers).
2. **Missing index** on columns used in `WHERE`, `JOIN` and `ORDER BY` of hot queries. Adding an index is a migration: show it and get the user's OK.
3. **Selecting too much**: `SELECT *` and loading relations the response does not use.
4. **Unbounded queries**: no `LIMIT` or pagination on lists that grow.
5. **Work in the app that the database does better**: counting, filtering or sorting in memory after loading every row.
6. **Repeated identical queries per request**: memoize per request, or cache with an explicit expiry.

## Pitfalls

- A query plan on 10 seed rows says nothing. Seed realistic volumes before measuring.
- Eager loading everything trades N+1 for one huge join. Measure both count and time.
- Report the verdict on query count and endpoint time; Lighthouse will not show it.
