import re

SYNDROME_PATTERN = re.compile(r"(症狀: .*?)\s*(證型: .*?證)\s*")


def reorder_syndrome_text(text):
    """Put the syndrome type (證型) before its symptoms (症狀) in each retrieved entry."""
    return SYNDROME_PATTERN.sub(r"\2\n\1\n\n", text)
