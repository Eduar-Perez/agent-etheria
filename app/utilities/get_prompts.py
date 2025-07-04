def open_prompt(full_path: str) -> str:
    with open(full_path, "r") as file:
        return file.read()