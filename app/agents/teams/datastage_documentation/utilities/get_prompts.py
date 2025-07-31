def open_prompt(full_path: str) -> str:
    with open(full_path, "r", encoding="utf-8") as file:
        return file.read()