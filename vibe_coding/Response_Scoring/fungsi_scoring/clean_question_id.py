import numpy as np
import pandas as pd

def clean_question_id(series_or_columns):
    """Normalize Question IDs for consistent matching."""
    return (
        pd.Series(series_or_columns)
        .astype("string")
        .str.replace(r"^ID\s*:\s*", "", regex=True)
        .str.replace(r"\.0$", "", regex=True)
        .str.strip()
        .replace("", pd.NA)
    )