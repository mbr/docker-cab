import sys

import click


class Table(object):
    def __init__(self, col_sizes=[], spacing=2):
        self.col_sizes = col_sizes
        self.spacing = spacing
        self.space_char = ' '

    def _join_parts(self, parts):
        return (self.space_char * self.spacing).join(parts)

    def format_row(self, *cols):
        parts = []
        for idx, col in enumerate(cols):
            size = self.col_sizes[idx]
            tx = str(col)
            parts.append(tx[:size] + self.space_char * (size - len(tx)))
        return self._join_parts(parts)

    def format_line(self, char='='):
        parts = []
        for n in self.col_sizes:
            parts.append(char * (n // len(char)))
        return self._join_parts(parts)


def exit_err(msg, status=1):
    click.echo(msg, err=1)
    sys.exit(1)
