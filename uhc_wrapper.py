import pexpect
import pexpect.replwrap
import codecs

# Name of server jar
server_jar = 'minecraft_server.1.9.jar'

# Command line builder
commandline = 'java -jar ' + server_jar + ' nogui'

# Spawn the server
minecraft = pexpect.spawn(commandline,timeout=None,encoding=None)

# Flag as running
running = minecraft.isalive()

while(running):
    result = minecraft.expect([pexpect.EOF,'You need to agree to the EULA in order to run the server. Go to eula.txt for more info.\r\n'])
    print(minecraft.before.replace(b'\r',b'').decode(),end='')

    if result == 0:
        print('Server has stopped')
        running = False
    elif result == 1:
        print(minecraft.after.replace(b'\r',b'').decode(),end='')
        print('\033[31m\033[1meula.txt needs to be completed\033[m')
