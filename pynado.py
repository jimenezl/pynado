import subprocess
import click
import re
import os

### Insert the location of your Coinado script here! ###
COINADO_SCRIPT_LOCATION = '/home/coinado'

#The following three functions are for deserializing .torrent files
#Written by: 
#Taken from blog at: TODO add link and authors
def tokenize(text, match=re.compile("([idel])|(\d+):|(-?\d+)").match):
    i = 0
    while i < len(text):
        m = match(text, i)
        s = m.group(m.lastindex)
        i = m.end()
        if m.lastindex == 2:
            yield "s"
            yield text[i:i+int(s)]
            i = i + int(s)
        else:
            yield s

def decode_item(next, token):
    if token == "i":
        # integer: "i" value "e"
        data = int(next())
        if next() != "e":
            raise ValueError
    elif token == "s":
        # string: "s" value (virtual tokens)
        data = next()
    elif token == "l" or token == "d":
        # container: "l" (or "d") values "e"
        data = []
        tok = next()
        while tok != "e":
            data.append(decode_item(next, tok))
            tok = next()
        if token == "d":
            data = dict(zip(data[0::2], data[1::2]))
    else:
        raise ValueError
    return data

def decode(text):
    try:
        src = tokenize(text)
        data = decode_item(src.next, src.next())
        for token in src: # look for more tokens
            raise SyntaxError("trailing junk")
    except (AttributeError, ValueError, StopIteration):
        raise SyntaxError("syntax error")
    return data

def getHash(tor_info):
    '''
    Get Hash of a torrent given transmission-show output of a .torrent file

    Returns a string of the hash
    '''
    hash_start_index = tor_info.find("Hash: ") + 6

    end_of_tor_info = tor_info[hash_start_index:]

    tor_hash = end_of_tor_info.split("\n")[0]
    
    return tor_hash

def getFilePaths(torrent_dict):
    '''
    Get File list of a torrent given transmission-show output of a .torrent file

    Returns a list of files that the given torrent includes
    '''

    torrent = torrent_dict

    files = []

    for file in torrent["info"]["files"]:
        files.append(file["path"])

    return files

def getFilesAndSizes(tor_info):
    '''
    Get File list of a torrent given transmission-show output of a .torrent file

    Returns a list of files that the given torrent includes
    '''

    files_start_index = tor_info.find("FILES\n\n") + 7

    end_of_tor_info = tor_info[files_start_index:]

    files = end_of_tor_info.split("\n")

    files = files[:-2]

    return files

def downloadFiles(torrent_hash, file_paths):
    '''
    Downloads the files in file_paths, given that they exist in the torrent specified by the torrent hash.
    Properly creates the directory structure of the torrent.
    
    torrent_hash - string representing the torrent to be downloaded
    file_paths - list of list of strings representing the full path of each file to be downloaded
    '''
    rootDir = os.getcwd()

    for file_path in file_paths:
        print "Currently downloading: " + file_path[-1]
        for directory in file_path[:-1]:
            mk_cd_Dir(directory)
        tor_subproc = subprocess.Popen(["bash",COINADO_SCRIPT_LOCATION, torrent_hash, file_path[-1]], stdout=subprocess.PIPE)    
        print tor_subproc.stdout.readline()
        os.chdir(rootDir)

def promptUserToContinue(message=""):
    '''
    Pauses, prints an optional message, and asks the user if they wish to continue.
    message - string to print to user, optional
    '''
    print message
    click.echo('Continue? [yn] ', nl=False)
    c = click.getchar()
    click.echo()
    if c == 'y':
        click.echo('We will go on')
    else:
        click.echo('Abort!')
        quit()


def mk_cd_Dir(directory):
    '''
    Tries to make a new directory "directory" if it doesn't already exist, and tries to move into it.
    If there are problems with either step, the user is prompted with the error and asked if they want 
    to continue or not.
    '''
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except Exception, e:
        print "there was an error creating the directory \"" + directory + "\" :"
        print e

        promptUserToContinue()

    try:
        os.chdir(directory)
    except Exception, e:
        print "there was an error trying to move into \"" + directory + "\" :"
        print e

        promptUserToContinue()


@click.command()
@click.argument('filename')
def pynado(filename):

    torrent_file_name = filename 

    #get torrent info from transmission
    p = subprocess.Popen(['transmission-show', torrent_file_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tor_info, err = p.communicate()

    if err != "": #if it doesn't exist
        print err
        quit()

    # display torrent info
    print "About to download: "
    for fileAndSize in getFilesAndSizes(tor_info):
        print "  - " + fileAndSize

    #prompt the user
    promptUserToContinue()

    #decode torrent file
    data = open(torrent_file_name, "rb").read()

    torrent = decode(data)
    torrent_name = torrent["info"]["name"]

    #create and move into download directory
    mk_cd_Dir(torrent_name)

    #get files and hash
    list_of_file_paths = getFilePaths(torrent)
    torrent_hash = getHash(tor_info)

    #download torrent
    downloadFiles(torrent_hash, list_of_file_paths)

    print "Finished downloading " + str(len(list_of_file_paths)) + " files."
    print ""

if __name__ == '__main__':
    pynado()