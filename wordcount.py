"""
wordcount.py - keeps word counts for IRC users
Copyright 2015, Andy Chung, iamchung.com
Licensed under the Eiffel Forum License 2.
"""

from sopel.module import rate, rule
import sopel
import sqlite3

@sopel.module.commands('wordcount')
@rate(5)
def wordcount(bot, trigger):
    # parse and execute command
    raw_args = trigger.group(2)
    output = ''
    if raw_args is None or raw_args == '':
        # display top 10 as default
        dataprovider = DataProvider()
        output = dataprovider.get_totals(0)
    else:
        # get subcommand
        command_parts = raw_args.split(' ', 1)
        if len(command_parts) > 1:
            output = "invalid number of arguments"
        else:
            data = command_parts[0]

            # see if reset
            if command_parts[0] == "reset":
                dataprovider = DataProvider()
                dataprovider.reset_totals();
                output = "totals have been reset"
            else:
                # verify input is int and display user totals
                offset = 0
                try:
                    offset = int(data)
                    dataprovider = DataProvider()
                    output = dataprovider.get_totals(offset)
                except ValueError:
                    output = "enter a valid integer"

    # output results
    bot.say(output)

@rule(r".*")
def wordcountlistener(bot, trigger):
    try:
        words = trigger.match.group(0).split()
        word_count = len(words)

        if word_count > 0:
            dataprovider = DataProvider()
            dataprovider.increment_user_total(trigger.nick, word_count)
    except:
        # silent fail so we don't spam channel
        pass

class DataProvider:
    def __init__(self):
        # check if tables exist and create as necessary
        self.conn = sqlite3.connect("wordcount.db")
        self.dbcursor = self.conn.cursor()
        self.dbcursor.execute("""
            create table if not exists
            wordcount (
                nick text not null primary key,
                words integer not null default 0
            )
        """)
        self.conn.commit()

    def get_totals(self, offset):
        # get the last 10 up until end value or however many we can
        self.dbcursor.execute("""
            select group_concat(msg, ', ') from (
                select (
                    (
                        select count(*) + 1
                        from wordcount b
                        where a.words < b.words
                    ) || '. ' || nick || '(' || words || ')'
                ) as msg
                from wordcount a
                order by words desc limit 10 offset ?
            )
        """, (offset,))
        totals = self.dbcursor.fetchone()
        if totals is None or totals[0] is None:
            msg = "nothing could be found."
        else:
            msg = totals[0]
        self.conn.close()
        return msg

    def increment_user_total(self, nick, num_new_words):
        self.dbcursor.execute("""
            insert or replace
            into wordcount (nick, words)
            values (
                ?,
                coalesce((select words + ? from wordcount where nick = ?), 0)
            )
        """, (nick, num_new_words, nick,))
        self.conn.commit()
        self.conn.close()

    def reset_totals(self):
        self.dbcursor.execute("""
            drop table if exists wordcount
        """)
        self.conn.commit()
        self.conn.close()
