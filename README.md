# TeleX
An unofficial Telegram message exchange rebot

![alt tag](https://github.com/gavincyi/TeleX/blob/master/doc/flow.jpg)

### Objective

Telex provides annoymous communication channel to exchange queries and responses in Telegram. 

1. A person (we call him "Customer") sends out a query to a robot. 
2. The rebot passes the query to the channel with a key (the query key)
3. Subscribers in the channel (we call them "Agents") can all see the query
4. Agents can response the query and send it to the rebot by the query key
5. The rebot passes the response back to the customer with another key (the response key)
6. The customer and agent can communicate under the query and response key

### Functionality

The following commands are supported in the rebot
* Query 
  - Query is sent out to the channel
  - Any subscriber in the channel can response the query through the bot
* Response 
  - Response is the private message between two anonymous users.
  - Agent can reply the reponse by the query ID.
  - Customer can reply the response by the source ID.
* Match 
  - Provide a way to reveal the own identity. 
  - Identities are revealed only when both agree to match.
* NoMatch
  - Terminate the conversation.
  - If anyone sends "NoMatch" on the query or source ID, the opponent will no longer send message to him.

### Dependency
The project supports python in version greater or equal to 2.7.

The following python packages are required. Highly recommend to use pip to install them.
* python-telegram-bot
* pyyaml

### Installation

1.  Clone the project

  Please clone the project to the corresponding directory.

        ```
        git clone https://github.com/gavincyi/TeleX.git
        ```

2.  Install the dependency

        ```
        pip install python-telegram-bot --upgrade
        pip install pyyaml --upgrade
        ```

3.  Configuration

  Set up the config.yaml. For details, please refer to section [Configuration](### Configuration)

### Configuration ###

Items:
- api_token
- channel_name
- log_path
- db_path






