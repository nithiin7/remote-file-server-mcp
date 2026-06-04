from . import get_file_info, list_files, read_files, search_file


def register_all(mcp) -> None:
    list_files.register(mcp)
    read_files.register(mcp)
    get_file_info.register(mcp)
    search_file.register(mcp)
