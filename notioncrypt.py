
import sys

from cryptography.fernet import Fernet, InvalidToken
from decouple import config
from notion_client import Client
from notion_client.errors import APIResponseError, APIErrorCode
# from notion_client.errors import (
# 	InternalServerError, ObjectNotFound, Unauthorized, RestrictedResource, 
# 	ServiceUnavailable
# )

from pprint import pprint 

from notioncrypt_functions import (
	get_id, get_url, get_children_blocks, encryptcontent, decryptcontent,
	create_new_page
)


def create_env():
	token = input("NOTION_TOKEN: ")
	key = input("ENCRYPT_KEY: ")
	with open(".env", "w") as file:
		file.write(f"NOTION_TOKEN={token}\n")
		file.write(f"ENCRYPT_KEY={key}\n")

def main():

	if sys.argv[1:]:
		if sys.argv[1] == "generate_key":
			print(Fernet.generate_key())
			exit()
		elif sys.argv[1] == "create_env":
			create_env()
			exit()
		else:
			print("invalid argument passed")
			exit()

	token = config("NOTION_TOKEN", default=None)
	key = config("ENCRYPT_KEY", default=None)

	if not token:
		print("your notion token not set as an environmental variable")
		exit()
	if not key:
		print("your encryption key not set as an environmental variable")
		exit()

	print(token)
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
		blocks = get_children_blocks(notion, page_id)
	except APIResponseError as error:
		if error.code == APIErrorCode.ObjectNotFound:
			print("Either the resource has not been shared with the integration or the resource does not exist ")
		if error.code == APIErrorCode.Unauthorized:
			print("your notion token might be invalid")
		exit()



	if response == "1":
		modifiedblocks = encryptcontent(blocks, f)
	if response == "2":
		try:
			modifiedblocks = decryptcontent(blocks, f)
		except InvalidToken:
			print("Either the encrypted page has been modified or a different encrypt key was passed")
			exit()



	try:
		parent_id = create_new_page(notion, page_id, modifiedblocks)
	except APIResponseError as error:
		if error.code == APIErrorCode.ObjectNotFound:
			print("the integration does not have access to the parent of this integration")
		exit()
	except Exception as error:
		print(error)


	print(f"Operation successfull, check out {get_url(parent_id)}")

main()