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


__all__ = 'Command Parser'.split()


class Command:
    '''
    Base class for application defined command classes that link
    argparse (user input), and a function.
    '''

    def arguments(self, arg):
        '''
        Declare command arguments by overriding it.

        `arg` is `Parser.arg` - think of it as `argparser.add_argument`
        e.g. these all work:
        arg('param')
        arg('--option', help='changes how the command behaves')

        There is also an extension, see `Parser.arg` for details.
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
        This is the function that gets called with the parsed arguments.

        You will want to override it!
        '''
        raise NotImplementedError


class Parser:
    '''
    Wrapper for `argparse.ArgumentParser` with conveniences for multi-command
    parsers.
    '''

    argparser = argparse.ArgumentParser

    def __init__(self, argparser):
        '''
        Wrap an `argparse.ArgumentParser`.

        See `new` on how to make a Parser.
        '''
        self.argparser = argparser
        # This is ugly :(
        # subparsers should be an `argparse` implementation detail, but is not
        self.__subparsers = None

        def print_help(args):
            self.argparser.print_help()
        self.argparser.set_defaults(_cliscape__run=print_help)

    @classmethod
    def new(cls, *args, **kwargs):
        '''
        Create a new `Parser`.

        Arguments are passed to `argparse.ArgumentParser()` and the argparser
        is wrapped as `Parser`.

        This eliminates the need for users to import argparse.
        '''
        return cls(argparse.ArgumentParser(*args, **kwargs))

    @property
    def _subparsers(self):
        if self.__subparsers is None:
            self.__subparsers = self.argparser.add_subparsers()
        return self.__subparsers

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

    def arg(self, *args, **kwargs):
        '''
        Declare one or more arguments.

        Same as `argparse.ArgumentParser.add_argument` with an extension:
        when the first and only parameter is a function, it is called with
        the parser to do some non-trivial work, like adding an argument group.

        The argument help is fixed up to show the default value.
        '''
        assert args
        if not kwargs and len(args) == 1 and callable(*args):
            args[0](self)
        else:
            arg_kwargs = dict(kwargs)
            if 'default' in kwargs:
                # extend help with default
                arg_kwargs['help'] = (
                    '{} (default: {!r})'
                    .format(kwargs.get('help', ''), kwargs['default']))
            self.argparser.add_argument(*args, **arg_kwargs)

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
        # declare arguments
        command.arguments(self.__class__(parser).arg)
        parser.set_defaults(_cliscape__run=command.run)

    def commands(self, *names_commands_and_title):
        '''
        Declare any number of commands in one step.

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
        args = self.argparser.parse_args(argv)
        args._cliscape__run(args)
