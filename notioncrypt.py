import sys
import os
import time
import json

from cryptography.fernet import Fernet, InvalidToken
from decouple import config
from notion_client import Client
from notion_client.errors import APIResponseError, APIErrorCode
from notioncrypt_functions import (
	get_id, get_url, get_children_blocks, encryptcontent, decryptcontent,
	create_new_page, get_meta_details, UnsupportedBlockError
)


from pprint import pprint
def create_env():
	""" helper function that takes in the relevant credentials and 
		creates a .env file 
	"""
	token = input("NOTION_TOKEN: ")
	key = input("ENCRYPT_KEY: ")
	with open(".env", "w") as file:
		file.write(f"NOTION_TOKEN={token}\n")
		file.write(f"ENCRYPT_KEY={key}\n")

def create_encrypted_backup(parentid, encryptedblocks, page_id):
	directory = os.path.join("Backups")
	if not (os.path.exists(directory) and os.path.isdir(directory)):
		os.mkdir(directory)

	with open(os.path.join(directory, page_id), "w") as file:
		json.dump(encryptedblocks, file, indent=3)

def main():

	# handle 
	if sys.argv[1:]:
		if sys.argv[1] == "generate_key":
			print("warning if you lose your key you will not be able to decrypt your pages")
			print(Fernet.generate_key())
			exit()
		elif sys.argv[1] == "create_env":
			create_env()
			exit()
		elif sys.argv[1] == "help":
			print(
			"valid options:\n" +
			"\tpython notioncrypt.py : to run the program\n" +
			"\tpython notioncrypt.py generate_key: to generate a valid fernet key\n" +
			"\tpython notioncrypt.py create_env: to create a .env file with valid credentials"
			)
			exit()
		else:
			print(f"Unknown option: {sys.argv[1]}")
			print("try python notioncrypt.py help for more info")
			exit()


	token = config("NOTION_TOKEN", default=None)
	key = config("ENCRYPT_KEY", default=None)

	if not token:
		print("your notion token not set as an environmental variable")
		exit()
	if not key:
		print("your encryption key not set as an environmental variable")
		exit()

	notion = Client(auth=token)
	f = Fernet(key)

	print("Encrypt a Notion Page: Select 1")
	print("Decrypt an Encrypted Notion Page: Select 2")

	while True:
		response = input("->")
		if response not in ["1", "2"]:
			print("invalid response") 
		else:
			break

	while True:
		print("Enter the link of the page: ", end="")
		page_url = input()
		try:
			page_id = get_id(page_url)
			break
		except ValueError as v:
			print(f"{v}")

	try:
		meta_pagedetails = get_meta_details(notion, page_id)
		print(meta_pagedetails)
		if not meta_pagedetails:
			print("page passed has a database parent or is a workspace level page")
			print("Only pages that have a page as a parent is currently supported")
			exit()
	except APIResponseError as error:
		if error.code == APIErrorCode.ObjectNotFound:
			print("Either the resource has not been shared with the integration or the resource does not exist"
				+ "or you passed in a database url")
		if error.code == APIErrorCode.Unauthorized:
			print("your notion token might be invalid")
		if error.code == APIErrorCode.InternalServerError:
			print("An error occured on notion's server's try again")
		if error.code == APIErrorCode.RestrictedResource:
			print("The bearer token used does not have permission to perform this action")
		if error.code == APIErrorCode.ServiceUnavailable:
			print("Notion is currently Unavailable try again")

		exit()


	# will remove from here
	blocks = get_children_blocks(notion, page_id)

	if response == "1":
		try:
			modifiedblocks = encryptcontent(blocks, f)
		except UnsupportedBlockError:
			print("your page contains other kind of blocks or embedded pages")
			print("Only pages that contain textlike blocks are currently supported")
			print("Cannot Encrypt page")
			exit()
	if response == "2":
		try:
			modifiedblocks = decryptcontent(blocks, f)
		except (InvalidToken, UnsupportedBlockError):
			print("Either the encrypted page has been modified or a different encrypt key was passed")
			exit()

	try:
		create_new_page(notion, meta_pagedetails, modifiedblocks)
	except APIResponseError as error:
		if error.code == APIErrorCode.ObjectNotFound:
			print("the integration does not have access to the parent of this integration")
		else:
			print(error)
		exit()

	if response == "1":
		time.sleep(3)
		titles = [title["text"]["content"] for title in meta_pagedetails["properties"]["title"]]
		titles = "".join(titles)
		results = notion.search(query=titles, sort={
					"direction":"descending",
      				"timestamp":"last_edited_time"
				}
			)
		
		new_encryptedpage_id = results["results"][0]["id"]
		create_encrypted_backup(notion, modifiedblocks, new_encryptedpage_id)


	print(f"Operation successfull, check out {get_url(meta_pagedetails['parent']['page_id'])}")

main()
#create_encrypted_backup(2,4)