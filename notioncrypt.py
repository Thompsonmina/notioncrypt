import sys
import os
import json

from colorama import init, Fore
from cryptography.fernet import Fernet, InvalidToken
from decouple import config
from notion_client import Client
from notion_client.errors import APIResponseError, APIErrorCode
from notioncrypt_functions import (
	get_id, get_url, get_children_blocks, encryptcontent, decryptcontent,
	create_new_page, get_meta_details, UnsupportedBlockError
)

# allows printing of color to shell
init(autoreset=True)

# the name of the directory that will store the backedup encrypted files
BACKUP_DIRECTORY = "Backups"

# minor utility function for print error messages
print_error = lambda msg: print(Fore.RED + msg)
	

def create_env():
	""" helper function that takes in the relevant credentials and 
		creates a .env file 
	"""
	token = input("NOTION_TOKEN: ")
	key = input("ENCRYPT_KEY: ")
	with open(".env", "w") as file:
		file.write(f"NOTION_TOKEN={token}\n")
		file.write(f"ENCRYPT_KEY={key}\n")

def create_encrypted_backup(encryptedblocks, page_id):
	"""
		Creates back ups of encrypted pages stored as json files with the page id as 
		its filename
	"""
	#create a new directory where backups will be stored if it doesn't already exist
	directory = os.path.join(BACKUP_DIRECTORY)
	if not (os.path.exists(directory) and os.path.isdir(directory)):
		os.mkdir(directory)

	with open(os.path.join(directory, page_id + ".json"), "w") as file:
		json.dump(encryptedblocks, file, indent=1)

def destroy_encrypted_backup(page_id):
	"""
		removes a stored encrypted page from file system
	"""
	path_to_file = f"{BACKUP_DIRECTORY}/{page_id}.json"
	if os.path.isfile(path_to_file):
		os.remove(path_to_file)


def main():
	""" Handles the main user facing logic"""

	# check if extra arguments are passed when running the script
	if sys.argv[1:]:
		if sys.argv[1] == "generate_key" and not sys.argv[2:]:
			print(Fore.YELLOW + "warning if you lose your key you will not be able to decrypt your pages")
			print(f"key: '{Fernet.generate_key().decode()}'")
			exit()
		if sys.argv[1] == "create_env" and not sys.argv[2:]:
			create_env()
			exit()
		if sys.argv[1] == "help" and not sys.argv[2:]:
			print(
			"valid options:\n" +
			"\tpython notioncrypt.py : to run the program\n" +
			"\tpython notioncrypt.py generate_key: to generate a valid fernet key\n" +
			"\tpython notioncrypt.py create_env: to create a .env file with valid credentials"
			)
			exit()
		else:
			print(f"Unknown option: {' '.join(sys.argv[1:])}")
			print("try python notioncrypt.py help for relevant options")
			exit()


	token = config("NOTION_TOKEN", default=None)
	key = config("ENCRYPT_KEY", default=None)

	if not token:
		print_error("your notion token not set as an environmental variable")
		exit()
	if not key:
		print_error("your encryption key not set as an environmental variable")
		exit()

	notion = Client(auth=token)
	fernetobject = Fernet(key)

	print("Encrypt a Notion Page: Select 1")
	print("Decrypt an Encrypted Notion Page: Select 2")

	# ensure user passes in a valid response
	while True:
		response = input("->")
		if response not in ["1", "2"]:
			print("invalid response") 
		else:
			break

	# ensure user passes in a valid notion url
	while True:
		print("Enter the link of the page: ", end="")
		page_url = input()
		try:
			page_id = get_id(page_url)
			break
		except ValueError as v:
			print(f"{v}")

	# Try to establish an initial connection to user's workspace 
	try:
		# get the relevant information needed to create notion pages
		meta_pagedetails = get_meta_details(notion, page_id)
	except APIResponseError as error:
		if error.code == APIErrorCode.ObjectNotFound:
			print_error("Either the resource has not been shared with the integration or the resource does not exist"
				+ "or you passed in a database url")
		if error.code == APIErrorCode.Unauthorized:
			print_error("your notion token might be invalid")
		if error.code == APIErrorCode.InternalServerError:
			print_error("An error occured on notion's server's try again")
		if error.code == APIErrorCode.RestrictedResource:
			print_error("The bearer token used does not have permission to perform this action")
		if error.code == APIErrorCode.ServiceUnavailable:
			print_error("Notion is currently Unavailable try again")
		exit()
	else:
		# check to see if meta_info is exists
		# if it doesn't exist, an unsupported type of notion page was passed
		# only pages that have pages as parents are valid
		if not meta_pagedetails:
			print("page passed has a database parent or is a workspace level page")
			print("Only pages that have a page as a parent is currently supported")
			exit()

	if response == "1":
		print(Fore.GREEN + "encrypting page...")
		handle_encryption(notion, meta_pagedetails, page_id, fernetobject)
		
	if response == "2":
		print(Fore.GREEN + "decrypting page...")
		handle_decryption(notion, meta_pagedetails, page_id, fernetobject)


	print(Fore.GREEN + f"Operation successfull, check out {get_url(meta_pagedetails['parent']['page_id'])}")
	

def handle_decryption(notion, meta_pagedetails, page_id, fernetobject):
	"""
		part of the main program that handles decryption of notion pages.

		decrypts the notion pages from the backup if it exists else fetches the 
		encrypted page and then decrypts it
	"""
	# get all encrypted pages currently stored 
	storedpages = os.listdir(BACKUP_DIRECTORY) if os.path.exists(BACKUP_DIRECTORY) else ""

	# trim the files names in order to remove the .json parts
	storedpages = [page[:-5] for page in storedpages]

	# if the given encrypted page has been backed up then decrypt from backup
	# if not fetch the page
	if page_id in storedpages:
		with open(os.path.join(BACKUP_DIRECTORY, page_id + ".json")) as file:
			blocks = json.load(file)
	else:
		blocks = get_children_blocks(notion, page_id)

	try:
		modifiedblocks = decryptcontent(blocks, fernetobject)
	except (InvalidToken, UnsupportedBlockError):
		print_error("Either the encrypted page has been modified or a different encrypt key was passed")
		print_error("Cannot Decrypt page")
		exit()

	# Create a new Notion page with the decrypted contents
	try:
		create_new_page(notion, meta_pagedetails, modifiedblocks)
	except APIResponseError as error:
		if error.code == APIErrorCode.ObjectNotFound:
			print_error("the integration does not have access to the parent of this page")
		else:
			print_error(error)
		exit()

	# new decrypted page has been created so delete old encrypted page
	notion.pages.update(page_id, **{"archived":True, "properties":meta_pagedetails["properties"]})

	# delete the encrypted page from backup if a new decrypted page
	# was successfully created
	destroy_encrypted_backup(page_id)

		
def handle_encryption(notion, meta_pagedetails, page_id, fernetobject):
	"""
		part of the program that handles encryption of notion pages.

		fetches the notion page, encrypts it, creates a new page with the 
		encrypted content, fetches the id of the new encrypted page 
		and stores it the disk as a json backup
	"""
	
	blocks = get_children_blocks(notion, page_id)
	create_encrypted_backup(blocks, "long")

	try:
		modifiedblocks = encryptcontent(blocks, fernetobject)
	except UnsupportedBlockError:
		print_error("your page contains other kind of blocks or embedded pages")
		print_error("Only pages that contain textlike blocks are currently supported")
		print_error("Cannot Encrypt page")
		exit()

	try:
		create_new_page(notion, meta_pagedetails, modifiedblocks)
	except APIResponseError as error:
		if error.code == APIErrorCode.ObjectNotFound:
			print_error("the integration does not have access to the parent of this page")
		if error.code == APIErrorCode.ValidationError:
			print_error("Cannot Encrypt, page content passed notion api's current limit")
		else:
			print(error)
			raise
		exit()

	# when a new page has been created delete old page
	notion.pages.update(page_id, **{"archived":True, "properties":meta_pagedetails["properties"]})

	
	# get the title of the new page	
	titles = [title["text"]["content"] for title in meta_pagedetails["properties"]["title"]]
	titles = "".join(titles)

	# get the newly created encrypted page back from notion in order to get its id
	results = notion.search(query=titles, sort={
					"direction":"descending",
	  				"timestamp":"last_edited_time"
				})
	new_encryptedpage_id = results["results"][0]["id"]
	
	# create a backup of the newly encrypted page using its id as the filename
	create_encrypted_backup(modifiedblocks, new_encryptedpage_id)


if __name__ == "__main__":
	main()
