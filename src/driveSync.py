from tkinter import N
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
SCOPES = ['https://www.googleapis.com/auth/drive.file']
# SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/drive.file']


class GCloudDriver:
    
    def __init__(self, local_target, drive_target):
        self.local_target = local_target
        self.drive_target = drive_target
        self.service = self.authenticate()
        self.recent_file_md = None
        self.md_data = None
        self.md_md = None
        
        self.md_file_name = "drive_metadata_ssoc.json"
        self.md_exists = self.check_file_exists(self.md_file_name, self.drive_target)
        if self.md_exists:
            self.md_md = self.recent_file_md[0]
            temp = self.getFile(fid = self.md_md['id'])
            try:
                self.md_data = json.loads(temp.decode('utf-8'))
            except json.JSONDecodeError:
                print("md is empty")
            print(self.md_md)
            print(json.dumps(self.md_data, indent=4))
        else:
            with open(self.md_file_name, 'w') as newMd:
                newMd.close()
            self.upload_file(self.md_file_name, 'text/plain', self.drive_target)
            self.md_exists = self.check_file_exists(self.md_file_name, self.drive_target)
            if self.md_exists:
                print("Newly Created*******")
                self.md_md = self.recent_file_md[0]
            else:
                print(f"not created:{self.md_exists}")

    # Authenticate function
    def authenticate(self):
        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        return build('drive', 'v3', credentials=creds)

    def sync_drive(self):
        for f in self.md_data.keys():
            for idx, upfile in enumerate(self.md_data[f]):
                if upfile is not None:
                    if self.getFileMd5(fid=upfile['id']) == upfile['md5']:
                        if self.getFileMd5(fpath=upfile['location']) == upfile['md5']:
                            print("No Changes...")
                            continue
                        else:
                            print(f"Local File:{f} has been changed since last upload")
                            """
                            updated_file = self.service.files().update(
                                fileId=upfile['id'],
                                media_body=MediaFileUpload(upfile['location'], mimetype='text/plain', resumable=True),
                                supportsAllDrives=True
                            ).execute()
                            time.sleep(2)
                            self.md_data[f][idx]['md5'] = self.getFileMd5(fpath=upfile['location'])
                            self.md_data[f][idx]['modified_time'] = gen.format_date(local_date = os.path.getmtime(upfile['location']))
                            """
                    else:
                        if self.getFileMd5(fpath=upfile['location']) == upfile['md5']:
                            print(f" Up Shared File:{f} has been changed since last upload")
                        else:
                            print(f"Both Local and Shared File:{f} has been changed since last upload")
                            local_modified_time = upfile['modified_time']
                            new_local_modified_time = gen.format_date(local_date = os.path.getmtime(upfile['location']))
###FIX-ME:: UPDATE local_modified_time to real time
                            local_modified_time = upfile['uptime']
                            up_modified_time = upfile['uptime']
                            file_info = self.service.files().get(fileId=upfile['id'],
                                    supportsAllDrives=True,  
                                    fields='modifiedTime').execute()
                            new_up_modified_time = gen.format_date(mod_date = file_info['modifiedTime'])

                            # substract local_old - local_new and up_old - up_new and which ever is greater that is the file to be uploaded
                            # local_diff = datetime.strptime(new_local_modified_time, '%Y-%m-%d %H:%M:%S.%f') - datetime.strptime(local_modified_time, '%Y-%m-%d %H:%M:%S.%f')
                            # up_diff = datetime.strptime(new_up_modified_time, '%Y-%m-%d %H:%M:%S.%f') - datetime.strptime(up_modified_time, '%Y-%m-%d %H:%M:%S.%f')


                            # Update the datetime parsing to handle timezone information
                            local_diff = datetime.strptime(new_local_modified_time.split('+')[0], '%Y-%m-%d %H:%M:%S.%f') - datetime.strptime(local_modified_time.split('+')[0], '%Y-%m-%d %H:%M:%S.%f')
                            up_diff = datetime.strptime(new_up_modified_time.split('+')[0], '%Y-%m-%d %H:%M:%S.%f') - datetime.strptime(up_modified_time.split('+')[0], '%Y-%m-%d %H:%M:%S.%f')

                            print(f"{str(local_diff)=}")
                            print(f"{str(up_diff)=}")
                            print(f"{str(local_modified_time)=}")
                            print(f"{str(new_local_modified_time)=}")
                            print(f"{str(up_modified_time)=}")
                            print(f"{str(new_up_modified_time)=}")
                            if local_diff > up_diff:
                                print("Up and local files both not up to date, local file is more latest")
                                """
                                print(f"Uploading local file: {f}")
                                updated_file = self.service.files().update(
                                    fileId=upfile['id'],
                                    media_body=MediaFileUpload(upfile['location'], mimetype='text/plain', resumable=True),
                                    supportsAllDrives=True
                                ).execute()
                                time.sleep(2)
                                self.md_data[f][idx]['md5'] = self.getFileMd5(fpath=upfile['location'])
                                self.md_data[f][idx]['modified_time'] = gen.format_date(local_date=os.path.getmtime(upfile['location']))
                                """
                            else:
                                print("Up and local files both not up to date, up file is more latest")
                                """
                                print(f"Downloading shared file: {f}")
                                file_content = self.getFile(fid=upfile['id'])
                                with open(upfile['location'], 'wb') as local_file:
                                    local_file.write(file_content)
                                self.md_data[f][idx]['md5'] = self.getFileMd5(fpath=upfile['location'])
                                self.md_data[f][idx]['modified_time'] = gen.format_date(local_date=os.path.getmtime(upfile['location']))
                                """


    # Upload file function
    def upload_file(self, file_path, mime_type, folder_id=None):
        drive_service = self.service
        abs_path = os.path.abspath(file_path)
        fmd5 = self.getFileMd5(fpath=file_path)
        idx = None
        filename = os.path.basename(file_path)
        isNewFileWithSimName = True
        extend = False
        # ----- Getting local file md dict:
        # creation_time = os.path.getctime(file_path)
        # creation_date = datetime.fromtimestamp(creation_time)
        # formatted_creation_date = creation_date.strftime('%Y-%m-%d %H:%M:%S.') + f"{creation_date.microsecond // 1000:03}"
        print("----getting local creation date")
        formatted_creation_date = gen.format_date(local_date = os.path.getctime(file_path))
        print("----getting local modified date")
        if self.md_data is not None and filename in self.md_data.keys():
            formatted_modified_date = gen.format_date(local_date = os.path.getmtime(file_path))
        else:
            formatted_modified_date = gen.format_date(local_date = time.time())
            
        # modified_time = os.path.getmtime(file_path)
        # modified_date = datetime.fromtimestamp(modified_time)
        # formatted_modified_date = modified_date.strftime('%Y-%m-%d %H:%M:%S.') + f"{modified_date.microsecond // 1000:03}"
        
        # print(f'{creation_time=} ; {formatted_creation_date=}')
        # print(f'{modified_time=} ; {formatted_modified_date=}')
        temp = [{"creation_time": formatted_creation_date,
                    "modified_time": formatted_modified_date,
                    "md5": fmd5,
                    "location": abs_path,
                    "uptime": None,
                    "id": None}]
        print(f'{temp=}')
        # ------
        
        media = MediaFileUpload(file_path, mimetype='text/plain', resumable=True)
        print("******************************************")
        # print(f"{self.md_data.keys()=}")
        # print(f"{file_path=}")
        
        # print(f"{self.md_data=}")
        if self.md_data is not None and filename in self.md_data.keys():
            # If curr filename present in drive
            
            for idx, upfile in enumerate(self.md_data[filename]):
                print("upfile:",upfile)
                print("abs_path:",abs_path)
                if upfile["location"] == abs_path:
                    isNewFileWithSimName = False
                    # Uploaded file loc is same as file loc to be uploaded
                    if fmd5.lower() == upfile["md5"].lower():
                        print("******************************************")
                        print("*************Already UptoDate*************")
                        print("******************************************")
                        return True
                    else:
                        print("Content changed since last Upload")
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
                    print("#######-----ERR:Root Md missing !False-----#######")
                    # return False
        if isNewFileWithSimName:
            # filename is new to drive
            # if filename == self.md_file_name:
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
                print(f'File uploaded successfully with File ID: {file["id"]}')
                file_info = drive_service.files().get(fileId=temp[0]['id'],
                        supportsAllDrives=True,  
                        fields='modifiedTime').execute()
                temp[0]['uptime'] = gen.format_date(mod_date = file_info['modifiedTime'])
                print(file)
                # ----- Updating self.md with local file md dict
                if self.md_data is None:
                    self.md_data = {filename:temp}
                elif extend:
                    self.md_data[filename].extend(temp)
                else:
                    self.md_data[filename] = temp
                # ------
                
                # ----- Uploading self.md to drive
                print(f"{self.md_data=}")
                with open(self.md_file_name, 'w') as newMd:
                    json.dump(self.md_data, newMd)
                    newMd.close()
                media = MediaFileUpload(self.md_file_name, mimetype='text/plain', resumable=True)
                print("")
                updated_file = self.service.files().update(
                    fileId=self.md_md['id'],
                    media_body=media,
                    supportsAllDrives=True
                ).execute()
                print(f"File {updated_file['name']} has been updated.")
                # ------
                
            else:
                #ROOT MD missing ERROR
                print("#######-----ERR:Root Md missing-----#######")
                return False
            
            
        # ----- Uploading self.md to drive
        with open(self.md_file_name, 'w') as newMd:
            json.dump(self.md_data, newMd)
            newMd.close()
        media = MediaFileUpload(self.md_file_name, mimetype='text/plain', resumable=True)
        print("")
        updated_file = self.service.files().update(
            fileId=self.md_md['id'],
            media_body=media,
            supportsAllDrives=True
        ).execute()
        print(f"File {updated_file['name']} has been updated.")
        # ------
            
        return False

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
            print(files)
            if not files:
                print(f"No files found in folder {folder_id}. This could mean the folder is empty or doesn't exist.")
            else:
                print(f"Files found in folder {folder_id}:")
                for file in files:
                    print(f"File: {file['name']} (ID: {file['id']})")

        except Exception as e:
            print(f"An error occurred: {e}")

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
        print(query)
        drive_service = self.service
        
        # List files with the search query
        results = drive_service.files().list(q=query, supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        
        # Check if files were found
        items = results.get('files', [])
        
        if not items:
            print(f"No file found with name {filename}")
            return False
        else:
            print(f"File '{filename}' found.")
            print(items)
            self.recent_file_md = items
            return True
        
        
        query = f"'{folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        items = results.get('files', [])

        for item in items:
            print(f"File: {item['name']} ID: {item['id']}")
            
        
        # Test listing all files without filtering by folder
        q = "trashed = false and 'root' in parents"
        q = "trashed = false"
        results = drive_service.files().list(q=q,
                        fields="files(id, name, parents)",
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True).execute()
        items = results.get('files', [])

        for item in items:
            # print(f"ALL File: {item['name']} ID: {item['id']} parent: {item['parents']}")
            print(item)

    def getMime(self, filepath):
        if os.path.exists(filepath):
            mime_type = magic.Magic(mime=True)
            file_mime_type = mime_type.from_file(filepath)
            return file_mime_type
        else:
            print("Not a valid path")
            return ""

    def getFileMd5(self, fpath=None, fid=None):
        if fpath is not None:
            print(f"Reading Md5:{fpath}")
            md5_hash = hashlib.md5()
            with open(fpath, 'rb') as file:
                for chunk in iter(lambda: file.read(4096), b""):
                    md5_hash.update(chunk)
            file_md5 = md5_hash.hexdigest()
            return file_md5
        if fid is not None:
            file_id = fid
            drive_service = self.service
            request = drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
            drive_file_content = request.execute()
            drive_file_hash = hashlib.md5(drive_file_content).hexdigest()
            return drive_file_hash
            
    def getFile(self, fpath=None, fid=None):
        if fpath is not None:
            return None
        if fid is not None:
            file_id = fid
            drive_service = self.service
            request = drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
            existing_file_content = request.execute()
            existing_file_hash = hashlib.md5(existing_file_content).hexdigest()
            print(f"{existing_file_hash=} {existing_file_content=}")
            
            
            file_metadata = drive_service.files().get(fileId=file_id, supportsAllDrives=True, fields='md5Checksum').execute()
            content_md5 = file_metadata.get('md5Checksum')
            # print(f"{content_md5=} {existing_file_content=}")
            return existing_file_content

    def create_folder(self, folder_name, parent_folder_id):
        """Create a folder on Google Drive."""
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }

        try:
            # Create the folder
            folder = self.service.files().create(body=file_metadata, fields='id', supportsAllDrives=True).execute()
            print(f'Folder "{folder_name}" created with ID: {folder["id"]}')
            return folder
        except HttpError as error:
            print(f'An error occurred while creating folder: {folder_name} inside Parent:{parent_folder_id}:\n {error}')
        return False
    
    def get_folder_size(self, folder_path):
        total_size = 0
        # Walk through all files and subfolders in the directory
        if os.path.isfile(folder_path):
            return os.path.getsize(folder_path)
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                # Add the size of each file to the total size
                if os.path.getsize(file_path) < 100000000:
                    total_size += os.path.getsize(file_path)
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
                print(f"perm error:{path}")
        else:
            tree_structure = "The specified path does not exist."
        
        return tree_structure
    
    def clean_fname(self, fname):
        tab = "│ "
        sib = "├── "
        return fname.replace(tab,"").replace(sib,"").strip(" ").strip("/")

    def read_tree(self, tree, rootDirName):
        # ININ,STAY,BACK
        tab = "│ "
        sib = "├── "
        preLine = ""
        
        root = Path(os.path.abspath(rootDirName))
        print("PATH::::::",root)
        hist = {}

        folder_id = rootdir
        # root_folder = driver.create_folder(os.path.basename(root), rootdir)
        
        # if not root_folder:
            # print(f"Creating folder Failed: {root_folder}")
            # return False
        
        preLine = os.path.basename(root)
        parent = [[str(rootDirName), root_drive_dir]]
        with tqdm(total=self.get_folder_size(path), unit="B", desc="Uploading files") as pbar:
            for x, line in enumerate(tree.splitlines()):
                print(f"{line=}")
                print(f"{parent=}")
                cCount = line.split(sib)[0].count(tab)
                pCount = preLine.split(sib)[0].count(tab)
                # items = [i[0] for i in parent]
                if pCount < cCount:
                    prev_folder = driver.create_folder(self.clean_fname(preLine), parent[-1][1])
                    parent.append([preLine, prev_folder['id']])
                    print(f'{parent=}')
                    print("parent:","/".join([self.clean_fname(i[0]) for i in parent]))
                    print("ININ","parent:","/".join([self.clean_fname(i[0]) for i in parent]),self.clean_fname(line))
                    
                if pCount > cCount:
                    for i in range(pCount-cCount):
                        parent.pop()
                        print("parent:","/".join([self.clean_fname(i[0]) for i in parent]))
                        print("BACK","parent:","/".join([self.clean_fname(i[0]) for i in parent]),self.clean_fname(line))
                else:
                    print(parent)
                    print("parent:","/".join([self.clean_fname(i[0]) for i in  parent]))
                    print("STAY",line)
                print()
                cleaned = [self.clean_fname(i[0]) for i in  parent]
                cleaned.append(self.clean_fname(line))
                item = os.path.join("/".join(cleaned))
                if os.path.isfile(item) and os.path.getsize(item) < 100000000:
                    print("------------------------is FIle:",item)
                    print(f"{parent=}")                    
                    self.upload_file(item, self.getMime(item), parent[-1][1])
                    print(f"updated:{self.get_folder_size(item)=}")
                    pbar.update(self.get_folder_size(item))
                print()
                preLine = line

# Example usage
import sys
folder_id = '17jq3u-Suvq3UE5AfMSfnrOn4hg4GgWlr'  # The folder ID extracted from the URL
folder_id = '1mNXqQmfWoG-KmfzHNHlRVAVafWAoDwt0'  # The folder ID extracted from the URL

folder_id = '1n4EwZFpkvC330rYNZBo2Ftw9dYaYj1KK'  # The folder ID extracted from the URL
folder_id = '18CGD5omuOJwrn2l5QINl_5cBPyvVmAy-'  # The folder ID extracted from the URL

root_drive_dir = sys.argv[1]
root_drive_dir = "15U-HuE7EHb7WawCCfXLORbw8GO72lGcA"
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
import os
import sys

path=r'D:\UniqueTcCounter'
# tree = driver.generate_tree(path)
# driver.read_tree(tree, path)
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