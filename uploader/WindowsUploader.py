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

# Import tkinterdnd2 for drag and drop functionality
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    print("tkinterdnd2 not installed. Install with: pip install tkinterdnd2")
    DND_AVAILABLE = False

def browse_button_bg():
    threading.Thread(target=browse_button).start()

def browse_button():
    folder = filedialog.askdirectory()
    if folder == '':
        return
    process_folder(folder)

def process_folder(folder):
    """Process a folder and update the UI accordingly"""
    folderpath.set(folder)
    statustext.set('Selected ' + folder)
    list = []

    for i in os.listdir(folder):
        if os.path.splitext(i)[1] in allowed_extensions:
            list.append(i)
    if len(list) == 0:
        statustext.set('No images found, allowed formats:'+ str(allowed_extensions))
        upload['state'] = 'disabled'
        drag_drop_area.update_status("No images found in this folder")
        return

    filesize = 0
    for i in list:
        filesize = filesize + os.path.getsize(folder + '/' + i)

    statustext.set('Selected: ' + folder + '\nFound ' + str(len(list)) + ' photos with total filesize of ' +
                   str(int(filesize/1000000)) + 'MB')
    upload['state']='active'
    drag_drop_area.update_status(f"✓ Ready: {len(list)} photos ({int(filesize/1000000)}MB)")
    
    msg['filesize'] = filesize
    msg['folder'] = folder + '/'
    msg['filelist'] = list
    msg['photos'] = len(list)
    msg['token'] = token.get()

class DragDropFrame(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Configure TTK style for drag and drop area
        style = ttk.Style()
        
        # Create custom styles for the drag and drop area
        style.configure('DragDrop.TFrame', 
                    #    relief='sunken', 
                       borderwidth=2,
                       background='#f8f9fa')
        
        style.configure('DragDrop.TLabel', 
                       background='#f8f9fa',
                       foreground='#495057',
                       font=('Arial', 10),
                       anchor='center')
        
        style.configure('DragDropStatus.TLabel',
                       background='#f8f9fa',
                       foreground='#6c757d',
                       font=('Arial', 8),
                       anchor='center')
        
        # Hover styles
        style.configure('DragDropHover.TFrame',
                    #    relief='sunken',
                       borderwidth=2,
                       background="#bbbbbb")
        
        style.configure('DragDropHover.TLabel',
                       background="#bbbbbb",
                       foreground='#0d6efd',
                       font=('Arial', 10),
                       anchor='center')
        
        style.configure('DragDropStatusHover.TLabel',
                       background="#bbbbbb",
                       foreground='#0d6efd',
                       font=('Arial', 8),
                       anchor='center')
        
        # Drag enter styles
        style.configure('DragDropActive.TFrame',
                    #    relief='sunken',
                       borderwidth=2,
                       background='#cfe2ff')
        
        style.configure('DragDropActive.TLabel',
                       background='#cfe2ff',
                       foreground='#0d6efd',
                       font=('Arial', 10),
                       anchor='center')
        
        style.configure('DragDropStatusActive.TLabel',
                       background='#cfe2ff',
                       foreground='#0d6efd',
                       font=('Arial', 8),
                       anchor='center')
        
        # Configure this frame with the custom style
        self.configure(style='DragDrop.TFrame')
        
        # Create main label using TTK
        self.label = ttk.Label(self, 
                              text="📁 Drag and drop a folder here\nor click to browse",
                              style='DragDrop.TLabel')
        self.label.pack(expand=True, fill='both', pady=15)
        
        # Create status label using TTK
        self.status_label = ttk.Label(self,
                                     text="Select a folder containing images",
                                     style='DragDropStatus.TLabel')
        self.status_label.pack(side='bottom', pady=5)
        
        # Set up drag and drop if available
        try:
            from tkinterdnd2 import DND_FILES
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.on_drop)
            self.dnd_bind('<<DragEnter>>', self.on_drag_enter)
            self.dnd_bind('<<DragLeave>>', self.on_drag_leave)
            self.dnd_available = True
        except ImportError:
            self.dnd_available = False
        
        # Bind click event for browsing
        self.bind('<Button-1>', self.on_click)
        self.label.bind('<Button-1>', self.on_click)
        self.status_label.bind('<Button-1>', self.on_click)
        
        # Bind hover events for visual feedback
        self.bind('<Enter>', self.on_enter)
        self.bind('<Leave>', self.on_leave)
        self.label.bind('<Enter>', self.on_enter)
        self.label.bind('<Leave>', self.on_leave)
        self.status_label.bind('<Enter>', self.on_enter)
        self.status_label.bind('<Leave>', self.on_leave)
        
        # Set cursor
        self.configure(cursor='hand2')
        
    def on_click(self, event):
        """Handle click event to browse for folder"""
        # Call your browse function here
        browse_button_bg()
        
    def on_enter(self, event):
        """Handle mouse enter event"""
        self.configure(style='DragDropHover.TFrame')
        self.label.configure(style='DragDropHover.TLabel')
        self.status_label.configure(style='DragDropStatusHover.TLabel')
        
    def on_leave(self, event):
        """Handle mouse leave event"""
        self.configure(style='DragDrop.TFrame')
        self.label.configure(style='DragDrop.TLabel')
        self.status_label.configure(style='DragDropStatus.TLabel')
        
    def on_drag_enter(self, event):
        """Handle drag enter event"""
        self.configure(style='DragDropActive.TFrame')
        self.label.configure(style='DragDropActive.TLabel', text="📁 Drop folder here")
        self.status_label.configure(style='DragDropStatusActive.TLabel')
        
    def on_drag_leave(self, event):
        """Handle drag leave event"""
        self.configure(style='DragDrop.TFrame')
        self.label.configure(style='DragDrop.TLabel', text="📁 Drag and drop a folder here\nor click to browse")
        self.status_label.configure(style='DragDropStatus.TLabel')
        
    def on_drop(self, event):
        """Handle drop event"""
        # Reset appearance
        self.configure(style='DragDrop.TFrame')
        self.label.configure(style='DragDrop.TLabel', text="📁 Drag and drop a folder here\nor click to browse")
        self.status_label.configure(style='DragDropStatus.TLabel')
        
        # Get dropped files/folders
        files = event.data
        if files:
            # Handle different data formats
            if isinstance(files, str):
                # Single file/folder path
                path = files.strip('{}')  # Remove braces if present
            elif isinstance(files, (list, tuple)):
                # Multiple files - use the first one
                path = files[0].strip('{}')
            else:
                return
                
            # Process the path
            if os.path.exists(path):
                if os.path.isdir(path):
                    # It's a directory
                    self.update_status("Processing folder...")
                    threading.Thread(target=lambda: process_folder(path)).start()
                else:
                    # It's a file, use its parent directory
                    parent_dir = os.path.dirname(path)
                    self.update_status("Processing parent folder...")
                    threading.Thread(target=lambda: process_folder(parent_dir)).start()
            else:
                self.update_status("Invalid path dropped")
                
    def update_status(self, message):
        """Update the status label"""
        self.status_label.configure(text=message)

def upload_page():
    # Hide settings page elements
    naviContinue.grid_remove()
    enterToken.grid_remove()
    verifyToken.grid_remove()
    
    # Show upload page elements
    drag_drop_area.grid(row=1, columnspan=2, sticky='ew', pady=10, ipady=20)
    browse.grid(row=2, column=0, sticky='ew')
    upload.grid(row=2, column=1, sticky='ew')
    naviSettings.grid(row=3, column=1, sticky='ew')
    
    statustext.set('Select the folder containing your photos:')

def settings_page():
    # Hide upload page elements
    drag_drop_area.grid_remove()
    browse.grid_remove()
    upload.grid_remove()
    naviSettings.grid_remove()
    
    # Show settings page elements
    enterToken.grid(row=1, columnspan=2, sticky='ew')
    verifyToken.grid(row=2, columnspan=2, sticky='ew')
    naviContinue.grid(row=3, column=1, sticky='ew')
    
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
    drag_drop_area.update_status("Upload in progress...")

    statustext.set('Preparing upload ...')
    r = OpenScanCloud('getTokenInfo', msg)
    if r.status_code != 200:
        statustext.set('Connection failed')
        upload['state'] = 'active'
        browse['state'] = 'active'
        drag_drop_area.update_status("Connection failed")
        return

    msg2 = r.json()

    if msg['filesize'] > msg2['credit']:
        statustext.set('Not enough credit, please contact cloud@openscan.eu')
        upload['state'] = 'active'
        browse['state'] = 'active'
        drag_drop_area.update_status("Not enough credit")
        return

    if msg['filesize'] > msg2['limit_filesize']:
        statustext.set('Filesize limit exceeded')
        upload['state'] = 'active'
        browse['state'] = 'active'
        drag_drop_area.update_status("Filesize limit exceeded")
        return

    zipAndSplit()
    uploadAndStart()
    browse['state'] = 'active'
    drag_drop_area.update_status("Upload complete!")

def zipAndSplit():
    statustext.set('Creating zip ...')
    drag_drop_area.update_status("Creating zip archive...")

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
                drag_drop_area.update_status(f"Splitting archive: part {number}")
                with open(file + '_' + str(number), 'wb+') as chunk_file:
                    chunk_file.write(chunk)
                msg['partslist'].append(file + '_' + str(number))
                number += 1
                chunk = f.read(size_to_split)
        os.remove(file)
    msg['parts'] = len(msg['partslist'])
    statustext.set('preparing project on the OpenScanCloud server')
    drag_drop_area.update_status("Preparing project...")
    r = OpenScanCloud('createProject', msg)
    if r.status_code != 200:
        statustext.set('ERROR: Could not create project')
        drag_drop_area.update_status("ERROR: Could not create project")
        return
    msg['ulink'] = ''
    msg['ulink'] = r.json()['ulink']

def uploadAndStart():
    if msg['ulink'] == '':
        statustext.set('ERROR: Upload not started')
        drag_drop_area.update_status("ERROR: Upload not started")
        return
    i = 0

    filelist = msg['partslist']
    ulinks = msg['ulink']

    for file in filelist:
        statustext.set('uploading part ' + str(i+1) + ' of ' + str(len(filelist)))
        drag_drop_area.update_status(f"Uploading part {i+1} of {len(filelist)}")
        link = ulinks[i]
        i = i+1

        data = open(file, 'rb').read()
        r = requests.post(url=link, data=data, headers={'Content-type': 'application/octet-stream'})
        if r.status_code != 200:
            statustext.set('ERROR: could not upload file' + str(i))
            drag_drop_area.update_status(f"ERROR: could not upload file {i}")
            return
        os.remove(file)

    statustext.set('starting project')
    drag_drop_area.update_status("Starting project...")
    r = OpenScanCloud('startProject', msg)
    if r.status_code != 200:
        statustext.set('ERROR: could not start processing')
        drag_drop_area.update_status("ERROR: could not start processing")
    statustext.set('processing started ... you will get an email soon')
    drag_drop_area.update_status("✓ Processing started!")
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

# TKinter Setup with DnD support
if DND_AVAILABLE:
    window = TkinterDnD.Tk()
else:
    window = tkinter.Tk()

window.title('OpenScan Desktop')
window.geometry('340x280')  # Increased height for drag and drop area
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

# Create drag and drop area
drag_drop_area = DragDropFrame(window, height=80)

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

# Show warning if DnD is not available
if not DND_AVAILABLE:
    statustext.set('Install tkinterdnd2 for full drag & drop support')

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