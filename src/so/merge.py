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


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def _flatten_arenas(
    name: str, arenas: list, arena_key_map: dict[str, str]
) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for arena in arenas:
        if arena.name is None:
            logger.warning("flatten %s: arena with null name skipped", name)
            continue
        key = _normalize(arena.name)
        key = arena_key_map.get(key, key)
        for sub_path, sub_value in flatten(arena).items():
            if sub_path == "name":
                continue
            result[f"{name}.{key}.{sub_path}"] = sub_value
    return result


def flatten(
    extraction: BaseModel, arena_key_map: dict[str, str] | None = None
) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for name, value in extraction:
        if name == "arenas":
            result.update(_flatten_arenas(name, value, arena_key_map or {}))
        elif isinstance(value, BaseModel):
            for sub_path, sub_value in flatten(value, arena_key_map).items():
                result[f"{name}.{sub_path}"] = sub_value
        else:
            result[name] = str(value) if value is not None else None
    return result


async def _canonicalize_arena_keys(extractions: list[ReportExtraction]) -> dict[str, str]:
    by_key: dict[str, Counter] = {}
    for extraction in extractions:
        for arena in extraction.arenas:
            if arena.name is None:
                continue
            by_key.setdefault(_normalize(arena.name), Counter())[arena.name] += 1

    if len(by_key) <= 1:
        return {}

    representatives = {key: counter.most_common(1)[0][0] for key, counter in by_key.items()}
    llm_groups = await llm.structured(
        merge_prompt("arenas.name", sorted(representatives.values())), MergeGroups
    )

    llm_variants = {v for g in llm_groups.groups for v in g.variants}
    if llm_variants != set(representatives.values()):
        logger.warning("merge arenas.name: llm output mismatched variants, keeping keys as-is")
        return {}

    key_by_representative = {rep: key for key, rep in representatives.items()}
    arena_key_map = {}
    for llm_group in llm_groups.groups:
        canonical_key = _normalize(llm_group.canonical_value)
        for variant in llm_group.variants:
            arena_key_map[key_by_representative[variant]] = canonical_key
    return arena_key_map


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
    arena_key_map = await _canonicalize_arena_keys(extractions)
    flattened = [flatten(e, arena_key_map) for e in extractions]
    paths = sorted({path for f in flattened for path in f})

    merged_fields = []
    for path in paths:
        values = [f.get(path) for f in flattened]
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
