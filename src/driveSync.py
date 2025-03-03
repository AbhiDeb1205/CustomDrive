from re import I
from tkinter import N, SEL
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import os
import json
from datetime import datetime
import hashlib
import time
import magic
from tqdm import tqdm
from generic import DateTimeOperations as gen
from generic import Logger
SCOPES = ['https://www.googleapis.com/auth/drive.file']
# SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.file']

class Logger:
    def __init__(self, log_file='app.log'):
        self.log_file = log_file

    def log(self, message):
        with open(self.log_file, 'a', encoding='utf-8') as file:
            msg = f"{datetime.now()}: {message}\n"
            file.write(msg)

class GCloudDriver:
    
    def __init__(self, local_target, drive_target):
        self.logger = Logger()
        self.local_target = local_target
        self.drive_target = drive_target
        self.service = self.authenticate()
        self.recent_file_md = None
        self.md_data = None
        self.md_md = None  # Initialize Logger
        
        self.md_file_name = "drive_metadata_ssoc.json"
        self.md_exists = self.check_file_exists(self.md_file_name, self.drive_target)
        if self.md_exists:
            self.md_md = self.recent_file_md[0]
            temp = self.getFile(fid = self.md_md['id'])
            try:
                self.md_data = json.loads(temp.decode('utf-8'))
            except json.JSONDecodeError:
                self.logger.log("md is empty")
            self.logger.log(f"Metadata: {self.md_md}")
            self.logger.log(json.dumps(self.md_data, indent=4))
        else:
            with open(self.md_file_name, 'w') as newMd:
                newMd.close()
            self.upload_file(self.md_file_name, 'text/plain', self.drive_target)
            self.md_exists = self.check_file_exists(self.md_file_name, self.drive_target)
            if self.md_exists:
                self.logger.log("Newly Created*******")
                self.md_md = self.recent_file_md[0]
            else:
                self.logger.log(f"not created: {self.md_exists}")

    # Authenticate function
    def authenticate(self):
        creds = None
        self.logger.log("Starting authentication process.")
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            self.logger.log("Loaded credentials from token.json.")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self.logger.log("Refreshed expired credentials.")
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                self.logger.log("Performed new OAuth flow.")

            with open('token.json', 'w') as token:
                token.write(creds.to_json())
                self.logger.log("Saved new credentials to token.json.")
        
        self.logger.log("Authentication process completed.")
        return build('drive', 'v3', credentials=creds)

    def sync_drive(self):
        for f in self.md_data.keys():
            for idx, upfile in enumerate(self.md_data[f]):
                if upfile is not None:
                    if self.getFileMd5(fid=upfile['id']) == upfile['md5']:
                        if self.getFileMd5(fpath=upfile['location']) == upfile['md5']:
                            self.logger.log("No Changes...")
                            continue
                        else:
                            self.logger.log(f"Local File:{f} has been changed since last upload")
                            updated_file = self.update_file(file_id=upfile['id'], file_path=upfile['location'], mime_type='text/plain')
                            self.logger.log(f"File {updated_file['name']} has been updated.")
                    else:
                        if self.getFileMd5(fpath=upfile['location']) == upfile['md5']:
                            self.logger.log(f"Up Shared File:{f} has been changed since last upload")
                        else:
                            self.logger.log(f"Both Local and Shared File:{f} has been changed since last upload")
                            local_modified_time = upfile['modified_time']
                            new_local_modified_time = gen.format_date(local_date=os.path.getmtime(upfile['location']))
                   ###FIX-ME:: UPDATE local_modified_time to real time
                            local_modified_time = upfile['uptime']
                            up_modified_time = upfile['uptime']
                            file_info = self.service.files().get(fileId=upfile['id'],
                                    supportsAllDrives=True,  
                                    fields='modifiedTime').execute()
                            new_up_modified_time = gen.format_date(mod_date=file_info['modifiedTime'])

                            local_diff = datetime.strptime(new_local_modified_time.split('+')[0], '%Y-%m-%d %H:%M:%S.%f') - datetime.strptime(local_modified_time.split('+')[0], '%Y-%m-%d %H:%M:%S.%f')
                            up_diff = datetime.strptime(new_up_modified_time.split('+')[0], '%Y-%m-%d %H:%M:%S.%f') - datetime.strptime(up_modified_time.split('+')[0], '%Y-%m-%d %H:%M:%S.%f')

                            self.logger.log(f"{str(local_diff)=}")
                            self.logger.log(f"{str(up_diff)=}")
                            self.logger.log(f"{str(local_modified_time)=}")
                            self.logger.log(f"{str(new_local_modified_time)=}")
                            self.logger.log(f"{str(up_modified_time)=}")
                            self.logger.log(f"{str(new_up_modified_time)=}")
                            if local_diff > up_diff:
                                self.logger.log("Up and local files both not up to date, local file is more latest")
                            else:
                                self.logger.log("Up and local files both not up to date, up file is more latest")


    # Upload file function
    def upload_file(self, file_path, mime_type, folder_id=None):
        self.logger.log(f"Uploading file: {file_path}")
        drive_service = self.service
        abs_path = os.path.abspath(file_path)
        fmd5 = self.getFileMd5(fpath=file_path)
        idx = None
        filename = os.path.basename(file_path)
        isNewFileWithSimName = True
        extend = False
        self.logger.log("----getting local creation date")
        formatted_creation_date = gen.format_date(local_date=os.path.getctime(file_path))
        self.logger.log("----getting local modified date")
        if self.md_data is not None and filename in self.md_data.keys():
            formatted_modified_date = gen.format_date(local_date=os.path.getmtime(file_path))
        else:
            formatted_modified_date = gen.format_date(local_date=time.time())

        temp = [{"creation_time": formatted_creation_date,
                 "modified_time": formatted_modified_date,
                 "md5": fmd5,
                 "location": abs_path,
                 "uptime": None,
                 "id": None}]
        self.logger.log(f'{temp=}')
        # ------

        media = MediaFileUpload(file_path, mimetype='text/plain', resumable=True)
        self.logger.log("******************************************")
        if self.md_data is not None and filename in self.md_data.keys():
            # If curr filename present in drive

            for idx, upfile in enumerate(self.md_data[filename]):
                self.logger.log(f"upfile: {upfile}")
                self.logger.log(f"abs_path: {abs_path}")
                if upfile["location"] == abs_path:
                    isNewFileWithSimName = False
                    # Uploaded file loc is same as file loc to be uploaded
                    if fmd5.lower() == upfile["md5"].lower():
                        self.logger.log("******************************************")
                        self.logger.log("*************Already UptoDate*************")
                        self.logger.log("******************************************")
                        return True
                    else:
                        self.logger.log("Content changed since last Upload")
                        updated_file = self.service.files().update(
                            fileId=upfile['id'],
                            media_body=media,
                            supportsAllDrives=True
                        ).execute()
                        ###FIX-ME:: ADD check if successfully updated by comparing md5
                        time.sleep(2)
                        self.md_data[filename][idx]["md5"] = fmd5
                        self.md_data[filename][idx]["modified_time"] = formatted_modified_date
            if isNewFileWithSimName:
                # Is Diff file with similar name
                if self.md_exists:
                    extend = True
                else:
                    #ROOT MD missing ERROR
                    self.logger.log("#######-----ERR:Root Md missing !False-----#######")
                    # return False
        if isNewFileWithSimName:
            # filename is new to drive
            file_metadata = {'name': filename}
            # Set the parent folder if provided
            if folder_id:
                file_metadata['parents'] = [folder_id]
            file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id',
                supportsAllDrives=True
            ).execute()
            # Fix-Me::: check if file uploaded
            ###FIX-ME:: ADD check if successfully updated by comparing md5
            time.sleep(2)
            if self.md_exists:
                #if not first time user:

                temp[0]['id'] = file['id']
                self.logger.log(f'File uploaded successfully with File ID: {file["id"]}')
                file_info = self.get_file(file_id=temp[0]['id'])
                self.logger.log(f"{file_info=}")

                temp[0]['uptime'] = gen.format_date(mod_date=file_info['modifiedTime'])
                self.logger.log(file)
                # ----- Updating self.md with local file md dict
                if self.md_data is None:
                    self.md_data = {filename: temp}
                elif extend:
                    self.md_data[filename].extend(temp)
                else:
                    self.md_data[filename] = temp
                # ------

                # ----- Uploading self.md to drive
                self.logger.log(f"{self.md_data=}")
                self.logger.log("")
                updated_file = self.update_file(file_id=self.md_md['id'], file_path=self.md_file_name, mime_type='text/plain')
                self.logger.log(f"File {updated_file['name']} has been updated.")
                # ------

            else:
                #ROOT MD missing ERROR
                self.logger.log("#######-----ERR:Root Md missing-----#######")
                return False

        # ----- Uploading self.md to drive
        updated_file = self.update_file(file_id=self.md_md['id'], file_path=self.md_file_name, mime_type='text/plain')
        self.logger.log(f"File {updated_file['name']} has been updated.")
        # ------

        return False

    def create_file(self, file_name, file_path, mime_type, folder_id=None):
        self.logger.log(f"Creating file: {file_name}")
        if file_path is not None:
            if folder_id is None:
                self.logger.log("No folder ID provided. Please provide a folder ID to create a file.")
                return
            if file_name is None:
                file_name = os.path.basename(file_path)
            file_path = file_path
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            file_metadata = {
                'name': file_name,
                'parents': [folder_id]
            }
            new_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                supportsAllDrives=True
            ).execute()
    ###FIX-ME:: ADD check if file Created and remove sleep
            time.sleep(2)
            self.logger.log(f"File created: {new_file['name']} (ID: {new_file['id']})")
            return new_file
        else:
            self.logger.log("No file path provided. Please provide a file path to create a file.")

    def get_file(self, file_id=None, file_name=None, folder_id=None):
        self.logger.log(f"Retrieving file: {file_name}")
        if file_id is not None:
            file_id = file_id
            try:
                request = self.service.files().get(fileId=file_id, supportsAllDrives=True, fields='modifiedTime, name')
                file_content = request.execute()
                self.logger.log(f"File with ID {file_id} retrieved successfully.")
                return file_content
            except HttpError as error:
                self.logger.log(f"An error occurred while retrieving file with ID {file_id}: {error}")
                return None
        else:
            self.logger.log("No file ID provided. Please provide a file ID to get a file.")
            return None

    def update_file(self, file_id=None, file_path=None, mime_type=None, folder_id=None):
        self.logger.log(f"Updating file: {file_path}")
        if file_id is not None:
            # Check if the file being updated is the metadata file then first create the metadata local file
            if os.path.basename(file_path) == self.md_file_name:
                self.update_file(file_path=file_path)
            file_id = file_id
            media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
            updated_file = self.service.files().update(
                fileId=file_id,
                media_body=media,
                supportsAllDrives=True
            ).execute()
            self.logger.log(f"File updated: {updated_file['name']} (ID: {updated_file['id']})")
            return updated_file
        elif file_path is not None:
            with open(file_path, 'w') as newMd:
                if os.path.basename(file_path) == self.md_file_name:
                    json.dump(self.md_data, newMd)
                else:
                    # if not md file then create a new file
                    print(f"Not md file", file_path)
                newMd.close()
        else:
            self.logger.log("No file ID or file path provided. Please provide either to update a file.")

    def check_access(self, folder_id):
        service = self.service
        try:
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id,parents,name,mimeType)",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                pageSize=1000,
                pageToken=None,
                corpora='allDrives'
            ).execute()

            files = results.get('files')
            self.logger.log(f"Files in folder {folder_id}: {files}")
            if not files:
                self.logger.log(f"No files found in folder {folder_id}. This could mean the folder is empty or doesn't exist.")
            else:
                self.logger.log(f"Files found in folder {folder_id}:")
                for file in files:
                    self.logger.log(f"File: {file['name']} (ID: {file['id']})")

        except Exception as e:
            self.logger.log(f"An error occurred: {e}")

    def getFileMetadata(self, fpath=None, fid=None):
        if fpath is not None:
            local_file_path = fpath
            local_modified_time = datetime.fromtimestamp(os.path.getmtime(local_file_path))
            return datetime.strptime(str(local_modified_time), '%Y-%m-%d %H:%M:%S.%f')
        if fid is not None:
            # file_id = fid
            # file_metadata = authenticate().files().get(fileId=file_id,
                # supportsAllDrives=True,  
                # fields='modifiedTime').execute()
            # drive_modified_time = file_metadata['modifiedTime']
            # return datetime.strptime(str(drive_modified_time), '%Y-%m-%dT%H:%M:%S.%fZ')
            results = self.service.files().list(
                q=f"name='token2.json' and parents in '{folder_id}'",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                fields="files(id, name, modifiedTime)"
            ).execute()

            # Check if any files are returned
            files = results.get('files', [])
            
            print("---------",files)
    
    def check_file_exists(self, filename, folder_id):
        query = f"name = '{filename}' and '{folder_id}' in parents"# and trashed = false"
        self.logger.log(query)
        drive_service = self.service
        
        # List files with the search query
        results = drive_service.files().list(q=query, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        
        # Check if files were found
        items = results.get('files', [])
        
        if not items:
            self.logger.log(f"No file found with name {filename}")
            return False
        else:
            self.logger.log(f"File '{filename}' found.")
            self.logger.log(str(items))
            self.recent_file_md = items
            return True
        
        
        query = f"'{folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])

        for item in items:
            self.logger.log(f"File: {item['name']} ID: {item['id']}")
            
        
        # Test listing all files without filtering by folder
        q = "trashed = false and 'root' in parents"
        q = "trashed = false"
        results = drive_service.files().list(q=q,
                        fields="files(id, name, parents)",
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True).execute()
        items = results.get('files', [])

        for item in items:
            # self.logger.log(f"ALL File: {item['name']} ID: {item['id']} parent: {item['parents']}")
            self.logger.log(str(item))

    def getMime(self, filepath):
        if os.path.exists(filepath):
            mime_type = magic.Magic(mime=True)
            file_mime_type = mime_type.from_file(filepath)
            self.logger.log(f"File MIME type for {filepath}: {file_mime_type}")
            return file_mime_type
        else:
            self.logger.log(f"Invalid path: {filepath}")
            return ""

    def getFileMd5(self, fpath=None, fid=None):
        if fpath is not None:
            self.logger.log(f"Reading Md5 for local file: {fpath}")
            md5_hash = hashlib.md5()
            with open(fpath, 'rb') as file:
                for chunk in iter(lambda: file.read(4096), b""):
                    md5_hash.update(chunk)
            file_md5 = md5_hash.hexdigest()
            self.logger.log(f"MD5 for local file {fpath}: {file_md5}")
            return file_md5
        if fid is not None:
            self.logger.log(f"Reading Md5 for file ID: {fid}")
            file_id = fid
            drive_service = self.service
            request = drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
            drive_file_content = request.execute()
            drive_file_hash = hashlib.md5(drive_file_content).hexdigest()
            self.logger.log(f"MD5 for file ID {fid}: {drive_file_hash}")
            return drive_file_hash
            
    def getFile(self, fpath=None, fid=None):
        if fpath is not None:
            return None
        if fid is not None:
            file_id = fid
            drive_service = self.service
            try:
                request = drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
                existing_file_content = request.execute()
                existing_file_hash = hashlib.md5(existing_file_content).hexdigest()
                self.logger.log(f"File content and hash retrieved: {existing_file_hash=}, {existing_file_content=}")
                
                file_metadata = drive_service.files().get(fileId=file_id, supportsAllDrives=True, fields='md5Checksum').execute()
                content_md5 = file_metadata.get('md5Checksum')
                self.logger.log(f"File metadata retrieved: {content_md5=}")
                return existing_file_content
            except HttpError as error:
                self.logger.log(f"An error occurred while retrieving file with ID {file_id}: {error}")
                return None

    def create_folder(self, folder_name, parent_folder_id):
        """Create a folder on Google Drive."""
        self.logger.log(f"Creating folder: {folder_name}")
        
        # Check if folder already exists
        query = f"name = '{folder_name}' and '{parent_folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        results = self.service.files().list(q=query, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        items = results.get('files', [])
        
        if items:
            self.logger.log(f"Folder '{folder_name}' already exists in parent folder ID: {parent_folder_id}")
            return items[0]  # Return the existing folder
        
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }

        try:
            # Create the folder
            folder = self.service.files().create(body=file_metadata, fields='id', supportsAllDrives=True).execute()
            self.logger.log(f'Folder "{folder_name}" created with ID: {folder["id"]}')
            return folder
        except HttpError as error:
            self.logger.log(f'An error occurred while creating folder: {folder_name} inside Parent:{parent_folder_id}:\n {error}')
        return False
    
    def get_folder_size(self, folder_path):
        total_size = 0
        # Walk through all files and subfolders in the directory
        if os.path.isfile(folder_path):
            size = os.path.getsize(folder_path)
            self.logger.log(f"Size of file {folder_path}: {size} bytes")
            return size
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                # Add the size of each file to the total size
                if os.path.getsize(file_path) < 100000000:
                    file_size = os.path.getsize(file_path)
                    total_size += file_size
                    self.logger.log(f"Adding size of file {file_path}: {file_size} bytes")
        self.logger.log(f"Total size of folder {folder_path}: {total_size} bytes")
        return total_size

    def generate_tree(self, path, indent=""):
        tree_structure = ""  # Initialize an empty string to hold the tree structure

        # Check if the provided path exists
        if os.path.exists(path):
            # List directories and files in the current directory
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)

                    # Check if the item is a directory
                    if os.path.isdir(item_path):
                        tree_structure += f"{indent}├── {item}/\n"  # Append folder to tree string
                        tree_structure += self.generate_tree(item_path, indent + "│   ")  # Recursive call for nested directories
                    else:
                        tree_structure += f"{indent}├── {item}\n"  # Append file to tree string
            except PermissionError:
                self.logger.log(f"Permission error: {path}")
        else:
            tree_structure = "The specified path does not exist."
            self.logger.log(tree_structure)
        
        return tree_structure
    
    def clean_fname(self, fname):
        tab = "│ "
        sib = "├── "
        cleaned_name = fname.replace(tab,"").replace(sib,"").strip(" ").strip("/")
###FIX-ME:: special chars not supported by logger
        # self.logger.log(f"Cleaned filename: {cleaned_name}")
        return cleaned_name

    def read_tree(self, tree, rootDirName):
        # ININ,STAY,BACK
        tab = "│ "
        sib = "├── "
        preLine = ""
        
        root = Path(os.path.abspath(rootDirName))
        self.logger.log(f"PATH::::::{root}")
        hist = {}

        folder_id = rootdir
        # root_folder = driver.create_folder(os.path.basename(root), rootdir)
        
        # if not root_folder:
            # self.logger.log(f"Creating folder Failed: {root_folder}")
            # return False
        
        preLine = os.path.basename(root)
        parent = [[str(rootDirName), root_drive_dir]]
        with tqdm(total=self.get_folder_size(path), unit="B", desc="Uploading files") as pbar:
            for x, line in enumerate(tree.splitlines()):
                self.logger.log(f"{line=}")
                self.logger.log(f"{parent=}")
                cCount = line.split(sib)[0].count(tab)
                pCount = preLine.split(sib)[0].count(tab)
                # items = [i[0] for i in parent]
                if pCount < cCount:
                    prev_folder = driver.create_folder(self.clean_fname(preLine), parent[-1][1])
                    parent.append([preLine, prev_folder['id']])
                    self.logger.log(f'{parent=}')
                    self.logger.log("parent:" + "/".join([self.clean_fname(i[0]) for i in parent]))
                    self.logger.log("ININ parent:" + "/".join([self.clean_fname(i[0]) for i in parent]) + self.clean_fname(line))
                    
                if pCount > cCount:
                    for i in range(pCount-cCount):
                        parent.pop()
                        self.logger.log("parent:" + "/".join([self.clean_fname(i[0]) for i in parent]))
                        self.logger.log("BACK parent:" + "/".join([self.clean_fname(i[0]) for i in parent]) + self.clean_fname(line))
                else:
                    self.logger.log(str(parent))
                    self.logger.log("parent:" + "/".join([self.clean_fname(i[0]) for i in  parent]))
                    self.logger.log("STAY " + line)
                self.logger.log("")
                cleaned = [self.clean_fname(i[0]) for i in  parent]
                cleaned.append(self.clean_fname(line))
                item = os.path.join("/".join(cleaned))
                if os.path.isfile(item) and os.path.getsize(item) < 100000000:
                    self.logger.log("------------------------is FIle:" + item)
                    self.logger.log(f"{parent=}")                    
                    self.upload_file(item, self.getMime(item), parent[-1][1])
                    self.logger.log(f"updated:{self.get_folder_size(item)=}")
                    pbar.update(self.get_folder_size(item))
                self.logger.log("")
                preLine = line

# Example usage
import sys
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Google Drive Sync Script')
parser.add_argument('--root_dir_id', required=True, help='The root directory ID on Google Drive')
parser.add_argument('--local_dir_path', required=True, help='The local directory path to backup')
args = parser.parse_args()

root_drive_dir = args.root_dir_id

driver = GCloudDriver(".", root_drive_dir)
folder_id = '17jq3u-Suvq3UE5AfMSfnrOn4hg4GgWlr'  # The folder ID extracted from the URL
folder_id = '1mNXqQmfWoG-KmfzHNHlRVAVafWAoDwt0'  # The folder ID extracted from the URL

folder_id = '1n4EwZFpkvC330rYNZBo2Ftw9dYaYj1KK'  # The folder ID extracted from the URL
folder_id = '18CGD5omuOJwrn2l5QINl_5cBPyvVmAy-'  # The folder ID extracted from the URL

root_drive_dir = sys.argv[1]
root_drive_dir = "15U-HuE7EHb7WawCCfXLORbw8GO72lGcA"

root_drive_dir = args.root_dir_id

driver = GCloudDriver(".", root_drive_dir)

# local_time = driver.getFileMetadata(fpath='./token2.json')
# print(local_time)

bkupdir = "15U-HuE7EHb7WawCCfXLORbw8GO72lGcA"
rootdir = "1n4EwZFpkvC330rYNZBo2Ftw9dYaYj1KK"

rootdir = bkupdir

# file = sys.argv[2]
# print("calling:",file)
# driver.upload_file(file, 'text/plain', rootdir)
# driver.check_file_exists(file, rootdir)

file_id = '1ViHzZmOhS6CLzj54wW5D8aUu6l6LcphK' #realjson
file_id = '12GLKfZ6EJ89k_zsu-s8QnKJs9D-S5lAt' #credjson



from pathlib import Path

path = r'D:\UniqueTcCounter'
path = os.path.abspath(args.local_dir_path)
if not os.path.exists(path):
    print(f"Path doesnot exist: {path}")
    exit
tree = driver.generate_tree(path)
driver.read_tree(tree, path)
driver.sync_drive()

# for file in root.rglob("*"):  # rglob("*") returns all files and subdirectories recursively
    # if file.is_dir():
        # file = str(file)
        # print(f"Directory: {file}")
        # newPath = file.replace(str(root), "").split("\\") #Gets each folder after root in order
# ###FIX-ME:: ADD check IF NOT NONE AFTER SPLIT
        # prePath = root_folder
        # hist_list = [prePath]
        # for i, folder in enumerate(newPath):
            # prePath = driver.create_folder(folder, prePath['id'])
            # hist_list.append(prePath)
        
    # else:
        # print(f"File: {file}")