import tkinter
import tkinter.ttk as ttk
import os
import requests
import time
from zipfile import ZipFile
import sys
from tkinter import filedialog
import webbrowser
import threading
from sys import exit

def browse_button_bg():
    threading.Thread(target=browse_button).start()


def browse_button():
    folder = filedialog.askdirectory()
    if folder == '':
        return
    folderpath.set(folder)
    statustext.set('Selected ' + folder)
    list = []

    for i in os.listdir(folder):
        if os.path.splitext(i)[1] in allowed_extensions:
            list.append(i)
    if len(list) == 0:
        statustext.set('No images found, allowed formats:'+ str(allowed_extensions))
        upload['state'] = 'disabled'
        return

    filesize = 0
    for i in list:
        filesize = filesize + os.path.getsize(folder + '/' + i)

    statustext.set('Selected: ' + folder + '\nFound ' + str(len(list)) + ' photos with total filesize of ' +
                   str(int(filesize/1000000)) + 'MB')
    upload['state']='active'
    msg['filesize'] = filesize
    msg['folder'] = folder + '/'
    msg['filelist'] = list
    msg['photos'] = len(list)
    msg['token'] = token.get()


def upload_page():
    # Hide settings page elements
    naviContinue.grid_remove()
    enterToken.grid_remove()
    verifyToken.grid_remove()
    
    # Show upload page elements
    browse.grid(row=3, column=0, sticky='ew')
    upload.grid(row=3, column=1, sticky='ew')
    naviSettings.grid(row=4, column=1, sticky='ew')
    
    statustext.set('Select the folder containing your photos:')


def settings_page():
    # Hide upload page elements
    browse.grid_remove()
    upload.grid_remove()
    naviSettings.grid_remove()
    
    # Show settings page elements
    enterToken.grid(row=2, columnspan=2, sticky='ew')
    verifyToken.grid(row=3, columnspan=2, sticky='ew')
    naviContinue.grid(row=4, column=1, sticky='ew')
    
    if token.get() == '':
        statustext.set('Please enter a valid OpenScanCloud token')
        naviContinue['state'] = 'disabled'
    else:
        statustext.set('Your OpenScanCloud token:')
        naviContinue['state'] = 'active'


def OpenScanCloud(cmd, msg):
    r = requests.get(server + cmd, auth=(user, pw), params=msg)
    return r

def verify_bg():
    threading.Thread(target=verify).start()

def verify():
    verifyToken['state'] = 'disabled'
    statustext.set('Verifying Token ...')
    msg['token'] = token.get()
    if len(token.get()) < 15:
        statustext.set('Invalid Token')
        verifyToken['state'] = 'active'
        return
    r = OpenScanCloud('getTokenInfo', msg)
    if r.status_code != 200:
        statustext.set('Could not verify token, please try again:')
        naviContinue['state'] = 'disabled'
        verifyToken['state'] = 'active'
        return
    try:
        with open(active_directory + '/token.txt', 'w') as file:
            file.write(msg['token'])
        credit = round(int(r.json()['credit']) / 1000000000, 2)
        filesize = round(int(r.json()['limit_filesize']) / 1000000, 2)
        statustext.set('Token verified and saved.\nYou can upload a total of ' + str(credit) + 'GB\nWith a maximum size of '+str(filesize)+'MB per set')
        naviContinue['state'] = 'active'
    except:
        statustext.set('ERROR: Could not save token.')
    verifyToken['state'] = 'active'


def uploader_bg():
    threading.Thread(target=uploader).start()

def uploader():
    upload['state'] = 'disabled'
    browse['state'] = 'disabled'

    statustext.set('Preparing upload ...')
    r = OpenScanCloud('getTokenInfo', msg)
    if r.status_code != 200:
        statustext.set('Connection failed')
        upload['state'] = 'active'
        browse['state'] = 'active'

        return

    msg2 = r.json()

    if msg['filesize'] > msg2['credit']:
        statustext.set('Not enough credit, please contact cloud@openscan.eu')
        upload['state'] = 'active'
        browse['state'] = 'active'
        return

    if msg['filesize'] > msg2['limit_filesize']:
        statustext.set('Filesize limit exceeded')
        upload['state'] = 'active'
        browse['state'] = 'active'
        return

    zipAndSplit()
    uploadAndStart()
    browse['state'] = 'active'

def zipAndSplit():
    statustext.set('Creating zip ...')

    dir_tmp = active_directory + '/tmp/'

    if not os.path.isdir(dir_tmp):
        os.mkdir(dir_tmp)


    for i in os.listdir(dir_tmp):
        if os.path.isfile(dir_tmp + i):
            os.remove(dir_tmp + i)

    projectname = str(int(time.time()*100))+ '-OSC.zip'
    file = dir_tmp + projectname

    msg['project'] = projectname
    with ZipFile(file, 'w') as zip:
        for i in msg['filelist']:
            statustext.set('Adding to zip: ' + i)
            zip.write(msg['folder'] + i, i)

    msg['filesize'] = os.path.getsize(file)

    msg['partslist'] = [file]

    if os.path.getsize(file) > size_to_split:
        msg['partslist'] = []
        number = 1
        with open(file, 'rb') as f:
            chunk = f.read(size_to_split)
            while chunk:
                statustext.set('Splitting archive into chunks: ' + str(number))
                with open(file + '_' + str(number), 'wb+') as chunk_file:
                    chunk_file.write(chunk)
                msg['partslist'].append(file + '_' + str(number))
                number += 1
                chunk = f.read(size_to_split)
        os.remove(file)
    msg['parts'] = len(msg['partslist'])
    statustext.set('preparing project on the OpenScanCloud server')
    r = OpenScanCloud('createProject', msg)
    if r.status_code != 200:
        statustext.set('ERROR: Could not create project')
        return
    msg['ulink'] = ''
    msg['ulink'] = r.json()['ulink']

def uploadAndStart():
    if msg['ulink'] == '':
        statustext.set('ERROR: Upload not started')
        return
    i = 0

    filelist = msg['partslist']
    ulinks = msg['ulink']

    for file in filelist:
        statustext.set('uploading part ' + str(i+1) + ' of ' + str(len(filelist)))
        link = ulinks[i]
        i = i+1

        data = open(file, 'rb').read()
        r = requests.post(url=link, data=data, headers={'Content-type': 'application/octet-stream'})
        if r.status_code != 200:
            statustext.set('ERROR: could not upload file' + str(i))
            return
        os.remove(file)

    statustext.set('starting project')
    r = OpenScanCloud('startProject', msg)
    if r.status_code != 200:
        statustext.set('ERROR: could not start processing')
    statustext.set('processing started ... you will get an email soon')
    try:
        os.rmdir(active_directory + '/tmp/')
    except:
        pass

## OSC Settings
size_to_split = 200000000 #200MB is the maximum part size (total zip file can be up to 2GB)
limit_filesize = 0
limit_photos = 0
credit = 0
allowed_extensions = ['.jpg', '.jpeg', '.JPG', '.JPEG', '.png', '.PNG']
user = 'openscan'
pw = 'free'
server = 'http://openscanfeedback.dnsuser.de:1334/'
msg = {}

active_directory = os.path.dirname(os.path.realpath(sys.argv[0]))

# TKinter Setup

window = tkinter.Tk()
window.title('OpenScan Desktop')
window.geometry('340x220')
window.resizable(False,False)
window.grid_columnconfigure((0, 1), weight=1)
window.grid_rowconfigure((0, 1, 2, 3, 4), weight=1, minsize=30)


try:
    icon = tkinter.PhotoImage(file='uploader/window_icon.png')
    window.iconphoto(False, icon) 
except:
    pass  # Icon file not found, continue without icon

# Configure TTK styling
style = ttk.Style()
statustext = tkinter.StringVar()
folderpath = tkinter.StringVar()
token = tkinter.StringVar()

# Create all widgets
status = ttk.Label(window, textvariable=statustext)
naviContinue = ttk.Button(text="CONTINUE", command=upload_page)
naviSettings = ttk.Button(text="SETTINGS", command=settings_page)

# Try to load PNG images for buttons, fallback to text if not found
try:
    github_img = tkinter.PhotoImage(file='uploader/&&github_logo.png')
    link = ttk.Button(image=github_img)
    link.image = github_img  # Keep a reference to prevent garbage collection
except:
    link = ttk.Button(text="GITHUB")

try:
    donate_img = tkinter.PhotoImage(file='uploader/&&patreon_logo.png')
    donate = ttk.Button(image=donate_img)
    donate.image = donate_img  # Keep a reference to prevent garbage collection
except:
    donate = ttk.Button(text="DONATE")

link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/OpenScanEu/OpenScanCloud"
                                                      "#current-functionality--desktop-uploader-for-windows--download"))
donate.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.patreon.com/bePatron?u=51974655"))

browse = ttk.Button(text="Select folder", command=browse_button_bg)
upload = ttk.Button(text='Upload Photos', command=uploader_bg)

enterToken = ttk.Entry(textvariable=token, justify='center')
verifyToken = ttk.Button(text="Verify and Save Token", command=verify_bg)

# grid layout
status.grid(row=0, columnspan=2, sticky="ew")

# GitHub and Donate buttons in bottom stay constant. 
link.grid(row=4, column=0, sticky='w')
donate.grid(row=4, column=0, sticky='e')

# Initialize upload button state
upload['state']='disabled'

# Add some padding
for child in window.winfo_children():
    child.grid_configure(padx=5, pady=2)

# Initialize the appropriate page
if os.path.isfile(active_directory + '/token.txt'):
    with open(active_directory + '/token.txt', 'r') as file:
        token.set(file.read())
    upload_page()
else:
    token.set('')
    statustext.set('Please go to SETTINGS and enter a valid token')
    settings_page()

window.mainloop()

exit()