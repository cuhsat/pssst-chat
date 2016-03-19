#!/usr/bin/env python
"""
Copyright (C) 2016  Christian Uhsat <christian@uhsat.de>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
import curses
import os
import re
import sys
import time

from threading import Thread


try:
    from pssst import Pssst, CLI
except ImportError:
    sys.exit("Requires Pssst (https://github.com/cuhsat/pssst)")


__all__, __version__ = ["PssstChat"], "0.2.1"


class PssstChat:
    """
    Basic chat class using the Pssst protocol.

    Methods
    -------
    run()
        Starts the chat and runs its input processing.
    exit()
        Exits the chat and halts all its threads.

    """
    INTRO = "Type 'USERNAME ...' to send a message and 'exit' to exit."

    def __init__(self, profile):
        """
        Initializes the instance with the given profile.

        Parameters
        ----------
        param profile : tuple
            The users profile.

        Raises
        ------
        Exception
            Because the profile is required.

        """
        if not profile:
            raise Exception("Profile required")

        self.buffer = [PssstChat.INTRO, ""]
        self.pssst = Pssst(*profile)
        self.halt = False

    def __repr__(self):
        """
        Returns the chat version.

        Returns
        -------
        string
            The chat version.

        """
        return "Pssst Chat " + __version__

    def __enter__(self):
        """
        Sets the terminal mode and curses screen.

        Returns
        -------
        PssstChat
            The chat instance.

        """
        title = "%s - %s" % (repr(self.pssst), self.pssst.api)

        def setup(screen):
            """
            Curses wrapped method.

            Parameters
            ----------
            param screen : screen
                The curses screen.

            """
            height, width = screen.getmaxyx()

            curses.noecho()
            curses.cbreak()
            screen.keypad(True)

            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
            screen.addstr(0, 0, title.ljust(width), curses.color_pair(1))

            self.screen = screen
            self.height = height
            self.width = width

        curses.wrapper(setup)

        return self

    def __exit__(self, *args):
        """
        Resets the terminal mode.

        Parameters
        ----------
        param args : tuple
            Unused parameters.

        """
        curses.endwin()

    def __pssst_push(self, receiver, message):
        """
        Pushes a chat message to the receiver.

        Parameters
        ----------
        param receiver : string
            The chat receiver.
        param message : string
            The chat message.

        """
        try:
            self.pssst.push(receiver, message)
        except Exception as ex:
            self.buffer.append("Error: %s" % ex)

    def __pssst_pull(self):
        """
        Pulls all chat messages.

        Returns
        -------
        List
            The chat messages.

        """
        try:
            return self.pssst.pull()
        except Exception as ex:
            self.buffer.append("Error: %s" % ex)

    def __thread(self):
        """
        Constantly pull messages to the buffer.

        Notes
        -----
        This method runs asynchronous in a background thread.

        """
        while not self.halt:
            for data in self.__pssst_pull() or []:
                data = data.decode("utf-8")

                chunks = range(0, len(data), self.width)
                self.buffer += [data[i:i + self.width] for i in chunks]

            self.__render()
            time.sleep(1)

    def __render(self):
        """
        Renders the buffer.

        """
        cursor = self.screen.getyx()
        window = self.buffer[-(self.height - 2):]

        for y in range(len(window)):
            self.screen.addstr(1 + y, 0, window[y])
            self.screen.clrtoeol()

        self.screen.move(*cursor)
        self.screen.refresh()

    def __prompt(self):
        """
        Returns the user input.

        Returns
        -------
        string
            The user input.

        """
        prompt, y = "%s> " % repr(self.pssst.user), self.height - 1

        self.screen.addstr(y, 0, prompt)
        self.screen.move(y, len(prompt))
        self.screen.clrtoeol()

        return self.screen.getstr().strip()

    def run(self):
        """
        Starts the chat and runs its input processing.

        """
        self.thread = Thread(target=self.__thread)
        self.thread.daemon = True
        self.thread.start()

        while True:
            self.__render()

            line = self.__prompt()

            if not line:
                continue

            # Exit command
            elif line.lower() == 'exit':
                return self.exit()

            # Push command
            elif re.match("^(pssst\.)?\w{2,63}\W+.+$", line):
                self.__pssst_push(*line.split(" ", 1))

            # Unknown
            else:
                self.buffer.append("Error: Unknown command")

    def exit(self):
        """
        Exits the chat and halts all its threads.

        """
        self.halt = True
        self.thread.join()
        self.screen.clear()
        self.screen.refresh()


def main(script, arg="--help", *args):
    """
    Usage: %s [option|username|-]

    Options:
      -h, --help      Shows the usage
      -l, --license   Shows the license
      -v, --version   Shows the version

    Report bugs to <christian@uhsat.de>
    """
    try:
        script = os.path.basename(script)

        if arg in ("/?", "-h", "--help", None):
            print(re.sub("(?m)^ {4}", "", main.__doc__ % script).strip())

        elif arg in ("-l", "--license"):
            print(__doc__.strip())

        elif arg in ("-v", "--version"):
            print("Pssst Chat " + __version__)

        else:
            with PssstChat(CLI.profile(arg)) as chat:
                chat.run()

    except KeyboardInterrupt:
        print("Abort")

    except Exception as ex:
        return "Error: %s" % ex


if __name__ == "__main__":
    sys.exit(main(*sys.argv))
