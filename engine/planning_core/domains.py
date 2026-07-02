from __future__ import annotations


DOMAIN_LABEL_BY_CODE = {
    "HYDRAULIC": "유압",
    "STS": "STS",
    "SHAPED_MATERIAL": "이형재",
}

DOMAIN_CODE_BY_SOURCE = {
    "유압": "HYDRAULIC",
    "HYDRAULIC": "HYDRAULIC",
    "STS": "STS",
    "이형재": "SHAPED_MATERIAL",
    "SHAPED_MATERIAL": "SHAPED_MATERIAL",
    "SHAPED MATERIAL": "SHAPED_MATERIAL",
    "SHAPED-MATERIAL": "SHAPED_MATERIAL",
}


def normalize_domain_code(source_value: str) -> str:
    key = str(source_value).strip()
    domain_code = DOMAIN_CODE_BY_SOURCE.get(key)
    if domain_code is None:
        domain_code = DOMAIN_CODE_BY_SOURCE.get(key.upper().replace("_", " "))
    if domain_code is None:
        raise ValueError(f"Unknown planning domain: {source_value}")
    return domain_code
