from mcp.server.fastmcp import FastMCP

from . import get_file_info, list_files, read_files, search_file


def register_all(mcp: FastMCP) -> None:
    list_files.register(mcp)
    read_files.register(mcp)
    get_file_info.register(mcp)
    search_file.register(mcp)
