import asyncio
import uuid
import time

class Client:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.__reader: asyncio.StreamReader = reader
        self.__writer: asyncio.StreamWriter = writer
        self.__ip: str = writer.get_extra_info('peername')[0]
        self.__port: int = writer.get_extra_info('peername')[1]
        self.__authenticated = False
        self.__user_id = str(uuid.uuid4())
        self.__connected = int(time.time())
        self.last_command = self.__connected
        self.active = True

    def __str__(self):
        '''
        Outputs client information as '<nickname> <ip>:<port>'
        '''
        return f"{self.nickname} {self.ip}:{self.port}"

    @property
    def reader(self):
        '''
        Gets the StreamReader associated with a client.
        '''
        return self.__reader

    @property
    def writer(self):
        '''
        Gets the StreamWriter associated with a client.
        '''
        return self.__writer

    @property
    def ip(self):
        '''
        Gets the ip associated with a client
        '''
        return self.__ip

    @property
    def port(self):
        '''
        Gets the port associated with a client
        '''
        return self.__port
    
    @property
    def authenticated(self):
        '''
        Represents whether the player has completed the logon process
        '''
        return self.__authenticated
    
    @property
    def user_id(self):
        return self.__user_id

    
    def send_message(self, message):
        '''
        Send a message to this client so we don't have to encode it every time
        '''
        message = message + "\r\n"
        self.writer.write(message.encode('utf8'))

    async def get_message(self):
        '''
        Retrieves the incoming message from a client and returns it in string format.
        '''
        msg = ""

        # TODO: Handle protocol negotiation here

        while "\n" not in msg and self.active:
            bytes = await self.reader.read(1)
            if not bytes:
                self.active = False
                break
            msg += bytes.decode('utf8')

        # strip off newline characters, we add them back in on way out
        msg = msg.replace("\r", "")
        msg = msg.replace("\n", "")

        return msg.strip()
    