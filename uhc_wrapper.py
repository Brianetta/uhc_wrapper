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

    # Read Minecraft console
    result = minecraft.expect([
        #0
        pexpect.EOF,
        #1
        pexpect.TIMEOUT,
        #2
        '\[[0-9]+:[0-9]+:[0-9]+.*INFO\]: ',
        #3
        '\[[0-9]+:[0-9]+:[0-9]+.*WARN\]: ',
        #4
        '^\w+ joined the game\r\n',
        #5
        '\r\n'
        ],timeout=10)
    
    # Show all unmatched output
    print(minecraft.before.replace(b'\r',b'').decode(),end='')

    if result == 0:
        running = False
    elif result == 1:
        1
    elif result == 2:
        print('\033[32m'+minecraft.after.replace(b'\r',b'').decode()+'\033[m',end='')
    elif result == 3:
        print('\033[33m'+minecraft.after.replace(b'\r',b'').decode()+'\033[m',end='')
    elif result == 4:
        print(minecraft.after.replace(b'\r',b'').decode(),end='')
        minecraft.sendline('say Welcome, ' + minecraft.after.replace(b' joined the game\r\n',b'').decode())
    elif result == 5:
        print(minecraft.after.replace(b'\r',b'').decode(),end='')
