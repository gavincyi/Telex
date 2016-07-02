#!/bin/python
from src.txn import txn
from src.user_state import user_state
from src.message import message
import telegram


class handler:
    def __init__(self, logger, conf):
        self.logger = logger
        self.conf = conf
        self.session = 0
        self.channel_name = conf.channel_name
        self.id = 0
        self.main_keyboard = telegram.ReplyKeyboardMarkup(
                              [['/' + handler.query_handler_name(), '/' + handler.response_handler_name()],
                               ['/Deal', '/Block', '/Help']])
        self.back_keyboard = telegram.ReplyKeyboardMarkup(
                             [['/Back']])
        self.yes_no_keyboard = telegram.ReplyKeyboardMarkup(
                             [['/' + handler.yes_handler_name(), '/' + handler.no_handler_name()]])

    @staticmethod
    def query_handler_name():
        return 'Query'

    @staticmethod
    def response_handler_name():
        return 'Response'

    @staticmethod
    def help_handler_name():
        return 'Help'

    @staticmethod
    def yes_handler_name():
        return 'Yes'

    @staticmethod
    def no_handler_name():
        return 'No'

    @staticmethod
    def back_handler_name():
        return 'Back'

    def init_db(self, database_client):
        self.database_client = database_client

        # Get the latest id
        row = self.database_client.selectone(self.database_client.txn_table_name,
                                             "inid",
                                             "session = %d" % self.session,
                                             "session desc, inid desc")
        if row is None or not row[0]:
            self.id = 0
        else:
            self.id = row[0]

        self.logger.info("Current Id = %d" % self.id)

    def start_handler(self, bot, update):
        """
        Start handler
        :param bot: Callback bot
        :param update: Callback update
        """
        # Update user state
        us = user_state(update.message.chat_id, user_state.states.START)
        self.database_client.insert_or_replace(self.database_client.user_states_table_name,
                                               us.str())

        # Welcome message
        print_out = 'Welcome to TeleX, %s!\n'%update.message.from_user.first_name
        print_out += "TeleX is a community to connect demand and provider.\n"
        print_out += "The identity is not revealed until the request and response are matched.\n"

        # Send out message
        bot.sendMessage(update.message.chat_id,
                        text=print_out,
                        reply_markup = self.main_keyboard)

    def query_handler(self, bot, update):
        """
        Query handler
        :param bot: Callback bot
        :param update: Callback update
        """
        local_chat_id = update.message.chat_id
        row = self.database_client.selectone(self.database_client.user_states_table_name,
                                            "*",
                                            "chatid=%s"%local_chat_id)

        us = user_state(dbrow=row)
        us.jump(user_state.transitions.QUERYING)

        if us.chatid == str(local_chat_id) and us.state == user_state.states.QUERY_PENDING_MSG:
            # Update user state
            self.database_client.insert_or_replace(self.database_client.user_states_table_name,
                                                   us.str())
            # Send out message
            bot.sendMessage(local_chat_id,
                            text="Please tell me your query.",
                            reply_markup=self.back_keyboard)
        else:
            self.logger.warn("%s: No transition state for %s" % (local_chat_id, "QUERYING"))
            self.start_handler(bot, update)

    def response_handler(self, bot, update):
        """
        Response handler
        :param bot: Callback bot
        :param update: Callback update
        """
        local_chat_id = update.message.chat_id
        row = self.database_client.selectone(self.database_client.user_states_table_name,
                                             "*",
                                             "chatid=%s"%local_chat_id)

        us = user_state(dbrow=row)
        us.jump(user_state.transitions.RESPONSING)

        if us.chatid == str(local_chat_id) and us.state == user_state.states.RESPONSE_PENDING_ID:
            # Update user state
            self.database_client.insert_or_replace(self.database_client.user_states_table_name,
                                                   us.str())
            # Send out message
            bot.sendMessage(local_chat_id,
                            text="Please input the target ID.",
                            reply_markup=self.back_keyboard)
        else:
            self.logger.warn("%s: No transition state for %s" % (local_chat_id, "RESPONSING"))
            self.start_handler(bot, update)

    def response_backup_handler(self, bot, update):
        """
        Response handler
        :param bot: Callback bot
        :param update: Callback update
        """
        text = update.message.text.replace("/%s"%handler.response_handler_name(), '').strip()
        first_space = text.find(" ")

        # Query id validation
        if first_space == -1:
            bot.sendMessage(update.message.chat_id,
                            "Please provide a query id and an answer. Please send \"/%s %s\" for detailed usage."%
                            (handler.help_handler_name(), handler.response_handler_name()))
            return

        # Query id validation in database
        query_id = int(text[:first_space])
        row = self.database_client.selectone(self.database_client.txn_table_name,
                                             "*",
                                             "inid = %d" % query_id)

        if not row[0]:
            bot.sendMessage(update.message.chat_id,
                            "Query id (%s) cannot be found. Please send \"/%s %s\" for detailed usage."%
                            (query_id, handler.help_handler_name(), handler.response_handler_name()))
            return

        response = text[first_space+1:]

        # Insert the transaction into db
        self.id += 1
        txn_record = txn(self.session, self.id, update.message.chat_id)
        txn_record.outid = row[txn.inid_index()]
        txn_record.outchatid = row[txn.inchatid_index()]
        self.database_client.insert_or_replace(self.database_client.txn_table_name,
                                               txn_record.str())

        bot.sendMessage(txn_record.outchatid,
                        text="Response <%d> - Reply for query <%d>:\n%s" % (self.id, query_id, response))
        bot.sendMessage(update.message.chat_id,
                        text="Response <%d> is sent." % self.id)

    def yes_handler(self, bot, update):
        """
        Yes button handler
        :param bot: Callback bot
        :param update: Callback update
        """
        local_chat_id = update.message.chat_id
        row = self.database_client.selectone(self.database_client.user_states_table_name,
                                             "*",
                                             "chatid=%s"%local_chat_id)

        us = user_state(dbrow=row)

        if us.state == user_state.states.QUERY_PENDING_CONFIRM:
            row = self.database_client.selectone(self.database_client.messages_table_name,
                                                 "*",
                                                 "session = %d and chatid = '%s'" % (self.session, local_chat_id),
                                                 "date desc, time desc")
            if not row:
                self.logger.warn("Cannot find message. (session = %d, chatid = %d)" %
                                 (self.session, local_chat_id))

                # Handle same as "No" for error case
                self.no_handler(bot, update)

            else:
                us.jump(user_state.transitions.YES)

                # Update user state
                self.database_client.insert_or_replace(self.database_client.user_states_table_name,
                                                       us.str())

                # Acknowledge the user
                bot.sendMessage(local_chat_id,
                                text="Query %d has sent to channel" % row[3])

                # Change the state of the user first
                self.start_handler(bot, update)

                # Broadcast it in the channel
                bot.sendMessage(self.channel_name,
                                text="Time: %s %s\nQuery: %d\nQuery: %s"%(row[0], row[1], row[3], row[5]))

        elif us.state == user_state.states.RESPONSE_PENDING_CONFIRM:
            message_row = self.database_client.selectone(self.database_client.messages_table_name,
                                                 "*",
                                                 "session = %d and chatid = '%s'" % (self.session, local_chat_id),
                                                 "date desc, time desc")

            txn_row = self.database_client.selectone(self.database_client.txn_table_name,
                                                 "*",
                                                 "session = %d and inchatid = '%s'" % (self.session,local_chat_id),
                                                 "date desc, time desc")
            if not message_row or not txn_row:
                if not message_row:
                    self.logger.warn("Cannot find message. (session = %d, chatid = %d)" %
                                     (self.session, local_chat_id))
                if not txn_row:
                    self.logger.warn("Cannot find txn. (session = %d, inchatid = '%s'" %
                                     (self.session, local_chat_id))

                # Handle same as "No" for error case
                self.no_handler(bot, update)

            else:
                out_id = txn_row[3]
                out_chat_id = txn_row[4]
                msg = message_row[5]

                us.jump(user_state.transitions.YES)

                # Update user state
                self.database_client.insert_or_replace(self.database_client.user_states_table_name,
                                                       us.str())

                # Acknowledge the user
                bot.sendMessage(local_chat_id,
                                text="Response %d has sent to channel" % out_id)

                # Change the state of the user first
                self.start_handler(bot, update)

                # Broadcast it in the channel
                bot.sendMessage(out_chat_id,
                                text="Time: %s %s\nQuery : %d\nResponse : %s"%
                                (message_row[0], message_row[1], out_id, msg))

    def no_handler(self, bot, update):
        """
        No button handler
        :param bot: Callback bot
        :param update: Callback update
        """
        local_chat_id = update.message.chat_id
        row = self.database_client.selectone(self.database_client.user_states_table_name,
                                             "*",
                                             "chatid=%s"%local_chat_id)

        us = user_state(dbrow=row)
        us.jump(user_state.transitions.NO)

        # Update user state
        self.database_client.insert_or_replace(self.database_client.user_states_table_name,
                                               us.str())

        # Send out message
        bot.sendMessage(local_chat_id,
                        text="Action has been canceled.",
                        reply_markup=telegram.ReplyKeyboardHide())
        self.start_handler(bot, update)

    def help_handler(self, bot, update):
        """
        Help handler
        :param bot: Callback bot
        :param update: Callback update
        """
        self.logger.info("Not yet implemented")

    def set_value_handler(self, bot, update):
        local_chat_id = update.message.chat_id
        row = self.database_client.selectone(self.database_client.user_states_table_name,
                                             "*",
                                             "chatid=%s"%local_chat_id)

        user_state_record = user_state(dbrow=row)
        user_state_record.jump(user_state.transitions.YES)

        if user_state_record.chatid == str(local_chat_id):
            if user_state_record.state == user_state.states.QUERY_PENDING_CONFIRM:
                self.query_set_value_handler(bot, update, user_state_record)
            elif user_state_record.state == user_state.states.RESPONSE_PENDING_MSG:
                self.response_msg_set_value_handler(bot, update, user_state_record)
            elif user_state_record.state == user_state.states.RESPONSE_PENDING_CONFIRM:
                self.response_confirm_set_value_handler(bot, update, user_state_record)

    def response_confirm_set_value_handler(self, bot, update, user_state_record):
        local_chat_id = update.message.chat_id
        row = self.database_client.selectone(self.database_client.txn_table_name,
                                             "*",
                                             "inchatid=%s" % local_chat_id,
                                             "date desc, time desc")

        if not row:
            # Cannot find the query id. Reset the state
            user_state_record.jump(user_state.transitions.NO)

            # Update user state
            self.database_client.insert_or_replace(self.database_client.user_states_table_name,
                                                   user_state_record.str())

            self.logger.warn("Cannot find the inchatid (%s) from txn" % local_chat_id)

            self.start_handler(bot, update)

        else:
            # Store the message
            id = row[5]
            message_record = message(self.session, id, local_chat_id)
            message_record.msg = update.message.text
            self.database_client.insert_or_replace(self.database_client.messages_table_name,
                                                   message_record.str())

            # Update user state
            self.database_client.insert_or_replace(self.database_client.user_states_table_name,
                                                   user_state_record.str())

            bot.sendMessage(update.message.chat_id,
                            text="Confirm your response:\n%s"%message_record.msg,
                            reply_markup=self.yes_no_keyboard)

    def response_msg_set_value_handler(self, bot, update, user_state_record):
        query_id = update.message.text
        row = self.database_client.selectone(self.database_client.txn_table_name,
                                             "*",
                                             "inid = %s" % query_id)

        if not row:
            # Cannot find the query id. Reset the state
            user_state_record.jump(user_state.transitions.NO)

            # Update user state
            self.database_client.insert_or_replace(self.database_client.user_states_table_name,
                                                   user_state_record.str())

            bot.sendMessage(update.message.chat_id,
                            text="Cannot find the target ID",
                            reply_markup=telegram.ReplyKeyboardHide)

            self.start_handler(bot, update)

        else:
            self.id += 1
            txn_record = txn(session=self.session, inid=self.id, inchatid=update.message.chat_id)
            txn_record.outid = row[txn.inid_index()]
            txn_record.outchatid = row[txn.inchatid_index()]
            self.database_client.insert_or_replace(self.database_client.txn_table_name,
                                                   txn_record.str())

            # Update user state
            self.database_client.insert_or_replace(self.database_client.user_states_table_name,
                                                   user_state_record.str())

            bot.sendMessage(update.message.chat_id,
                            text="Please input the response.",
                            reply_markup=self.back_keyboard)

    def query_set_value_handler(self, bot, update, user_state_record):
        local_chat_id = update.message.chat_id

        # Increment id to provide an unique id
        self.id += 1

        # Insert the transaction into database
        txn_record = txn(self.session, self.id, local_chat_id)
        self.database_client.insert(self.database_client.txn_table_name,
                                    txn_record.str())

        # print out
        question = update.message.text
        self.logger.info("Query <%d> ChatId <%s>: %s"%(self.id, \
                                                       update.message.chat_id, \
                                                       question))

        # Update user state
        self.database_client.insert_or_replace(self.database_client.user_states_table_name,
                                               user_state_record.str())

        # Insert question into messages
        message_record = message(self.session, self.id, local_chat_id)
        message_record.msg = question
        self.database_client.insert_or_replace(self.database_client.messages_table_name,
                                               message_record.str())

        # Acknowledge the demand
        bot.sendMessage(update.message.chat_id,
                        text="Confirm your question:\n%s"%question,
                        reply_markup=self.yes_no_keyboard)

