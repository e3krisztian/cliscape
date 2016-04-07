'''
A minimalist (by intention) wrapper/dispatcher for argparse when you need
to support more than one commands or even a hierarchy of them (svn/git).

You will need to know `argparse.ArgumentParser.add_argument` as it is used
to declare arguments, but use named parameters except for the option names.

For single command scripts, be more minimalist and just use argparse directly.

:)
'''


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function


import argparse


__all__ = 'ArgumentParser Command Parser'.split()


class Command:
    '''
    Base class for application defined command classes that link
    argparse (user input), and a function.
    '''

    def configure_parser(self, parser):
        '''
        (advanced) Override to declare command arguments.

        This is and advanced entry point, override only for commands that
        need customization beyond `add_argument` calls
        (e.g. custom argument groups).

        Most of the time overriding `arguments` is enough
        (default implementation just calls `arguments`).
        '''
        self.arguments(parser.add_argument)

    def arguments(self, arg):
        '''
        Override to declare command arguments.

        Use `arg` as if it would be `parser.add_argument` e.g. as
        arg('param')
        arg('--option', help='changes how the command behaves')
        '''
        pass

    @property
    def description(self):
        '''
        Command description.

        Defaults to the class docstring.
        '''
        assert self.__doc__ is not None, self.__class__
        return self.__doc__

    def run(self, args):
        '''
        The function that gets called with the parsed arguments.

        You will want to override it!
        '''
        raise NotImplementedError


class Parser:
    def __init__(self, argumentparser):
        self.argumentparser = argumentparser
        # This is ugly :(
        # subparsers should be an `argparse` implementation detail, but is not
        self._subparsers = self.argumentparser.add_subparsers()

        def print_help(args):
            self.argumentparser.print_help()
        self.argumentparser.set_defaults(_cliscape__run=print_help)

    def _make_command(self, commandish):
        '''
        Make a proper Command instance.

        This is a convenience function to allow for easier to read client code,
        while still remaining quite strict on what is supported.
        '''
        if isinstance(commandish, Command):
            return commandish
        if issubclass(commandish, Command):
            instance = commandish()
            return instance
        if callable(commandish):
            # XXX: introspect parameter names, default values, annotations?
            raise NotImplementedError(
                'Can not yet work with vanilla callables')

    def command(self, name, commandish, title):
        '''
        Declare a command.

        Its name will be `name` and its arguments are defined by `commandish`
        Its help line will be `title`, while its help will be generated from
        its arguments.
        '''
        command = self._make_command(commandish)
        parser = self._subparsers.add_parser(
            name, help=title, description=command.description)
        command.configure_parser(parser)
        parser.set_defaults(_cliscape__run=command.run)

    def commands(self, *names_commands_and_title):
        '''
        Convenience for declaring more than one commands.

        Takes a sequence of alternating names, commands and titles.
        '''
        names    = names_commands_and_title[0::3]
        commands = names_commands_and_title[1::3]
        titles   = names_commands_and_title[2::3]

        MISMATCH = 'Names, commands, and titles do not match up!'
        assert len(names) == len(commands), MISMATCH
        assert len(names) == len(titles), MISMATCH
        assert all(isinstance(n, ''.__class__) for n in names), MISMATCH
        assert all(isinstance(t, ''.__class__) for t in titles), MISMATCH

        for name, command, title in zip(names, commands, titles):
            self.command(name, command, title)

    def group(self, name, title='', help=None):
        '''
        Declare a command group.

        Returns a `Parser` for the group to declare subcommands.
        '''
        parser = self._subparsers.add_parser(
            name, help=title + '...', description=help)
        return self.__class__(parser)

    def dispatch(self, argv):
        '''
        Parse `argv` and dispatch to the appropriate command.
        '''
        args = self.argumentparser.parse_args(argv)
        args._cliscape__run(args)


def ArgumentParser(*args, **kwargs):
    '''
    Convenience wrapper for `argparse.ArgumentParser`.

    Has the same parameters, so look up `ArgumentParser`.
    The returned object is however a `Parser` object, that
    wraps the newly created `argparse.ArgumentParser`.
    '''
    return Parser(argparse.ArgumentParser(*args, **kwargs))
