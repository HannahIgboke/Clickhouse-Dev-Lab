"""The exam objectives, as published at https://clickhouse.com/learn/certification.

Tasks refer to them by code (M1, I3, ...). Codes starting with S are stretch topics:
taught in the official course but not listed as exam objectives.
"""

DOMAINS = {
    "M": "Modeling data",
    "I": "Inserting data",
    "A": "Analyzing data",
    "O": "Optimizing query performance",
    "D": "Deduplication and mutations",
    "S": "Stretch (beyond the objectives)",
}

OBJECTIVES = {
    "M1": "Create a new database",
    "M2": "Create a new table that satisfies a given criteria or matches a given file format",
    "M3": "Choose efficient data types for columns when appropriate",
    "M4": "Define an efficient primary key given the queries that will be executed",
    "M5": "Define and query a Dictionary",
    "I1": "Insert a local file into a table",
    "I2": "Insert a file from cloud storage into a table",
    "I3": "Insert data from common file formats such as Parquet, CSV or TSV",
    "I4": "Perform minor transformations on data while inserting",
    "I5": "Insert data from one table into another",
    "A1": "Write a query that satisfies a given criteria",
    "A2": "Write a query that uses regular functions",
    "A3": "Write a query that uses aggregate functions",
    "A4": "Use a GROUP BY to compute buckets of aggregated values over a timeframe",
    "O1": "Define a materialized view that stores the result of a non-aggregation query",
    "O2": "Define a materialized view that uses AggregatingMergeTree or SummingMergeTree",
    "O3": "Define a projection",
    "O4": "Define a set or minmax skipping index",
    "D1": "Delete rows using a lightweight delete",
    "D2": "Implement an efficient upsert strategy using ReplacingMergeTree",
    "D3": "Implement frequent updates using CollapsingMergeTree",
    "S1": "Partitioning and TTL",
    "S2": "Joins",
    "S3": "Refreshable materialized views",
    "S4": "Compression codecs",
}

# Task `domains:` keys -> objective code prefix
DOMAIN_KEYS = {"modeling": "M", "inserting": "I", "analyzing": "A",
               "optimizing": "O", "dedup": "D", "stretch": "S"}


def domain_of(code: str) -> str:
    return DOMAINS[code[0]]


def exam_codes() -> list[str]:
    return [c for c in OBJECTIVES if not c.startswith("S")]
