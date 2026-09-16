"""
М33: CLI интерфейс
Консольные команды для автоматизации.
"""
import argparse
import sys
class CLIModule:
    def __init__(self):
        self.parser = argparse.ArgumentParser(prog="excel-studio-hr")
        self.subparsers = self.parser.add_subparsers()
    def add_command(self, name: str, handler, description: str):
        p = self.subparsers.add_parser(name, help=description)
        p.set_defaults(func=handler)
    def run(self, args=None):
        parsed = self.parser.parse_args(args)
        if hasattr(parsed, "func"):
            return parsed.func(parsed)
        self.parser.print_help()
        return 0

__all__ = ['CLIModule']
