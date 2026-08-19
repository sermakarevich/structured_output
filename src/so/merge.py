import logging
import re
from collections import Counter

from pydantic import BaseModel

from so import llm
from so.prompts import merge_prompt
from so.schema import ReportExtraction

logger = logging.getLogger(__name__)


class ValueGroup(BaseModel):
    canonical_value: str | None
    count: int
    variants: list[str]


class MergedField(BaseModel):
    path: str
    value: str | None
    confidence: int
    candidates: list[ValueGroup]


class MergeGroup(BaseModel):
    canonical_value: str
    variants: list[str]


class MergeGroups(BaseModel):
    groups: list[MergeGroup]


def _stringify_item(item) -> str:
    if isinstance(item, BaseModel):
        return ", ".join(str(v) for v in flatten(item).values() if v is not None)
    return str(item)


def flatten(extraction: BaseModel) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for name, value in extraction:
        if isinstance(value, list):
            items = sorted(s for i in value if (s := _stringify_item(i)))
            result[name] = ", ".join(items) if items else None
        elif isinstance(value, BaseModel):
            for sub_path, sub_value in flatten(value).items():
                result[f"{name}.{sub_path}"] = sub_value
        else:
            result[name] = str(value) if value is not None else None
    return result


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def _exact_groups(values: list[str | None]) -> list[ValueGroup]:
    nulls = sum(1 for v in values if v is None)
    non_null = [v for v in values if v is not None]

    groups: dict[str, Counter] = {}
    for v in non_null:
        key = _normalize(v)
        groups.setdefault(key, Counter())[v] += 1

    result = []
    if nulls:
        result.append(ValueGroup(canonical_value=None, count=nulls, variants=[]))
    for counter in groups.values():
        canonical, _ = counter.most_common(1)[0]
        result.append(
            ValueGroup(
                canonical_value=canonical,
                count=sum(counter.values()),
                variants=list(counter.keys()),
            )
        )
    return result


async def merge(extractions: list[ReportExtraction]) -> list[MergedField]:
    flattened = [flatten(e) for e in extractions]
    paths = list(flattened[0].keys()) if flattened else []

    merged_fields = []
    for path in paths:
        values = [f[path] for f in flattened]
        exact_groups = _exact_groups(values)
        distinct_non_null = [g for g in exact_groups if g.canonical_value is not None]

        if len(distinct_non_null) <= 1:
            groups = exact_groups
            logger.info("merge %s: exact", path)
        else:
            raw_variants = sorted({v for g in distinct_non_null for v in g.variants})
            llm_groups = await llm.structured(merge_prompt(path, raw_variants), MergeGroups)

            exact_by_variant = {v: g for g in distinct_non_null for v in g.variants}
            llm_variants = {v for g in llm_groups.groups for v in g.variants}
            if llm_variants != set(raw_variants):
                logger.warning(
                    "merge %s: llm output mismatched variants, falling back to exact", path
                )
                groups = exact_groups
            else:
                groups = []
                null_group = next((g for g in exact_groups if g.canonical_value is None), None)
                if null_group:
                    groups.append(null_group)
                for llm_group in llm_groups.groups:
                    count = sum(exact_by_variant[v].count for v in llm_group.variants)
                    groups.append(
                        ValueGroup(
                            canonical_value=llm_group.canonical_value,
                            count=count,
                            variants=llm_group.variants,
                        )
                    )
                logger.info(
                    "merge %s: llm, %d variants -> %d groups",
                    path,
                    len(raw_variants),
                    len(llm_groups.groups),
                )

        groups.sort(key=lambda g: g.count, reverse=True)
        winner = groups[0]
        merged_fields.append(
            MergedField(
                path=path,
                value=winner.canonical_value,
                confidence=winner.count,
                candidates=groups,
            )
        )

    return merged_fields
