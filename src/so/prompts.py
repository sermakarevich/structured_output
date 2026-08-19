def extraction_prompt() -> str:
    return (
        "The document is provided as one image per page. Read all pages, including "
        "charts, tables and figures, and fill every field of the JSON schema. "
        "Use null when the document does not state a value. "
        "Extract EVERY arena of competition listed in the report, with all its numeric parameters, "
        "reading values from the exhibit tables and charts; do not stop after a few. "
        "Numbers must be given as numbers, and dates written exactly as they appear in the document. "
        "For nested organization fields, the parent company goes in the outer `name` field and any "
        "named sub-unit (institute, research arm, division) goes in `business_unit`. "
        "Respond with JSON only."
    )


def merge_prompt(path: str, variants: list[str]) -> str:
    listed = "\n".join(f"{i + 1}. {v}" for i, v in enumerate(variants))
    return (
        f"The strings below are candidate values for the field `{path}`, produced by "
        "independent extraction runs over the same document. "
        "Group semantically equivalent values together, for example "
        '"MGI" == "McKinsey Global Institute" and '
        '"$29 trillion to $48 trillion" == "29-48 trillion USD". '
        "For each group, pick the most complete variant as the canonical_value. "
        "Every input variant must appear in exactly one group.\n\n"
        f"VARIANTS:\n{listed}"
    )


def investigation_prompt(path: str, candidates: list[tuple[str | None, int]]) -> str:
    listed = "\n".join(
        f"{value if value is not None else 'not found'} — {count} runs"
        for value, count in candidates
    )
    return (
        f"Independent extraction runs disagreed about the field `{path}`. "
        "Here are the candidate values with how many runs produced each:\n"
        f"{listed}\n\n"
        "Re-read the attached page images, including charts and tables, and decide the correct value. "
        "Cite where in the document the evidence is, with a short verbatim quote. "
        "Set resolved=false if the document is genuinely ambiguous."
    )
