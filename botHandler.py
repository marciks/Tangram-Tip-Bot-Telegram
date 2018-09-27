import requests
import sqlite3
import json
from pprint import pprint
from time import sleep
#from threading import Thread

class botHandler():

#-- Telegram API
    
    def __init__(self, token, password, db_name, alpha_api_token):
        self.token = token
        self.url = 'https://api.telegram.org/bot{}/'.format(self.token)
        self.alpha_api_token = alpha_api_token
        self.alpha_api_url = "http://41.185.26.184:8081/"
        self.password = password
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()


    def getUrl(self, method, payload = ""):
        request = requests.get(self.url+method, params = payload)
        return request.json()

    def getUpdates(self, offset=None, timeout=30):
        method = 'getUpdates'
        payload = {"offset": offset, 'timeout': timeout}
        while True:
            updates  = self.getUrl(method, payload)
            if updates['ok'] == True:
                updates = updates['result']
                if len(updates) > 0:
                    return updates
                else:
                    print('listening...')
            else:
                print('Service unavaible')


    def getChatID(self, update):
        chat_id = update['message']['chat']['id']
        return chat_id

    def getChatID_Link(self, update):
        chat_id = self.dbChecker('chat_id', self.getUsername(update))
        return chat_id

    def sendMessage(self, chat_id, text):
        params = {
               "chat_id": chat_id,
               "text": text
            }
        message = self.getUrl("sendMessage?", params)
        
    def getText(self, update):
        user_text = update['message']['text']
        return user_text

    def getUsername(self, update):
        username = update['message']['chat']['username']
        return username

    def getLinkByUsername(self, username):
        link = self.dbChecker('address', username)
        return link
        
#-- Tangram API
        
    def tangramRequest(self, method, payload):
        url = self.alpha_api_url
        headers = {"accept":"application/json",
                   "Authorization":self.alpha_api_token,
                   "Content-Type":"application/json"}
        r = requests.post(url+method, headers=headers, json=payload)
        pprint(r.json())
        return r


    def accountAPI(self):
        method = 'actor/wallet/create'
        payload = {'password': self.password}
        account = self.tangramRequest(method, payload).json()
        return account

    def walletAPI(self, account):
        method = 'actor/wallet/address'
        payload = {'identifier': account['id'], 'password': self.password}
        wallet = self.tangramRequest(method, payload).json()
        return wallet


    def tipTGM(self, update, user_text):
        method = 'actor/wallet/transfer/funds'
        payload = {
                      "identifier": "{}".format(self.dbChecker('identifier', self.getUsername(update))),
                      "password": "{}".format(self.password),
                      "account": "{}".format(self.dbChecker('address', self.getUsername(update))),
                      "change": "{}".format(self.dbChecker('address', self.getUsername(update))),
                      "link": "{}".format(self.getLinkByUsername(user_text[1])),
                      "amount": "{}".format(user_text[2])
                   }

        response = self.tangramRequest(method, payload)
        print(response.json(), '\n\n')
        return response

    def balTGM(self, update):
        method = 'actor/wallet/balance'
        payload = {
                      "identifier": "{}".format(self.dbChecker('identifier', self.getUsername(update))),
                      "password": "{}".format(self.password),
                      "address": "{}".format(self.dbChecker('address', self.getUsername(update)))
                  }
        balance = self.tangramRequest(method, payload).json()
        
        return balance
    
    def depositTGM(self, update):
        wallet = self.getLinkByUsername(self.getUsername(update))
        return wallet
    
    def withdrawTGM(self, update, user_text):
        method = 'actor/wallet/transfer/funds'
        payload = {
                      "identifier": "{}".format(self.dbChecker('identifier', self.getUsername(update))),
                      "password": "{}".format(self.password),
                      "account": "{}".format(self.dbChecker('address', self.getUsername(update))),
                      "change": "{}".format(self.dbChecker('address', self.getUsername(update))),
                      "link": "{}".format(user_text[1]),
                      "amount": "{}".format(user_text[2])
                    }

        response = self.tangramRequest(method, payload).json()
        
        return response


#-- Database
    

    def setup(self):
        command = '''
                    CREATE TABLE IF NOT EXISTS accounts(
                                            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                            account_name VARCHAR(255) NOT NULL UNIQUE,
                                            identifier VARCHAR(255) NOT NULL UNIQUE,
                                            password VARCHAR(255) NOT NULL,
                                            address VARCHAR(255) NOT NULL UNIQUE,
                                            chat_id INTEGER NOT NULL UNIQUE
                                          )
                  '''

        self.cursor.execute(command)
        self.conn.commit()
        
    def isRegistered(self, update):
        try:
            user = self.dbChecker('account_name', self.getUsername(update))
            if self.getUsername(update) == user:
                return True
            else:
                msg = "You are not registered.. Type /start"
                self.sendMessage(self.getChatID(update), msg)
                return False
            
        except Exception as e:
            print(e)
            return False
        
    def accountReg(self, update):
        account = self.accountAPI()
        account_name = update['message']['chat']['username']
        identifier = account['id']
        password = self.password
        address = self.walletAPI(account)['address']
        chat_id = update['message']['chat']['id']
        command = """
                    INSERT INTO accounts (account_name, identifier, password, address, chat_id)
                    VALUES (?, ?, ?, ?, ?)
        
                  """
        try:
            self.cursor.execute(command, (account_name, identifier, password, address, chat_id))
            self.conn.commit()
            return "Welcome to the Tangram tip bot!\nType /help to see all commands"

        except Exception as e:
            print(e)
            return "User already registered "
            
    def dbChecker(self, select, where):   
        command = """ SELECT %s FROM accounts WHERE account_name = ? """
        
        r = self.cursor.execute(command %(select), (where,))
        return ("%s" % r.fetchone())
    

    