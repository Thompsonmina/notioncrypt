from cryptography.fernet import Fernet, InvalidToken
from decouple import config
from notion_client import Client
from notion_client.errors import APIResponseError, APIErrorCode
# from notion_client.errors import (
# 	InternalServerError, ObjectNotFound, Unauthorized, RestrictedResource, 
# 	ServiceUnavailable
# )

from pprint import pprint 

from helpers import get_id, get_url


def main():
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



def get_parentpage_details(client, pageid):
	page = client.pages.retrieve(pageid)
	if page["parent"]["type"] == "page_id":
		parentid = page["parent"]["page_id"]
		titles = [title["text"]["content"] for title in page["properties"]["title"]["title"]]
		relevantinfo = {
							"parent": {"page_id": parentid},
							"properties": {
								"title": [{"text": {
											"content": title
												}
											} for title in titles]
							}
						}
		return relevantinfo
	return None	


def create_new_page(client, plainpageID, childrenblocks):
	if childrenblocks:
		page_payload = get_parentpage_details(client, plainpageID)
		
		if page_payload:
			page_payload["children"] = childrenblocks
			client.pages.create(**page_payload)
		else:
			raise Exception("The parent of page is unsupported, can only handle pages that have pages as parents")
		return page_payload["parent"]["page_id"] 


def get_children_blocks(client, blockid, recursive=True):
 	children = client.blocks.children.list(blockid).get("results", [])
 	if recursive:
	 	for block in children:
	 		if block["has_children"]:
	 			blocktype = block["type"]
	 			block[blocktype]["children"] = getchildren(client, block["id"])
 	return children


def append_children_to_parentblock(client, blockid, children):
	client.blocks.children.append(blockid, **{"children":children})

def encryptcontent(blocks, fernetobject):
	for block in blocks:
		blocktype = block["type"]
		for richtextobjects in block[blocktype]["text"]:
			if richtextobjects["type"] == "text":
				plaincontent = richtextobjects["text"]["content"]
				encryptedcontent = fernetobject.encrypt(plaincontent.encode("utf-8"))
				richtextobjects["text"]["content"] = encryptedcontent.decode()

		if block["has_children"]:
			block[blocktype]["children"] = encryptcontent(block[blocktype]["children"])


	return blocks


def decryptcontent(blocks, fernetobject):
	for block in blocks:
		blocktype = block["type"]
		for richtextobjects in block[blocktype]["text"]:
			if richtextobjects["type"] == "text":
				encryptedcontent = richtextobjects["text"]["content"]
				try:
					plaincontent = fernetobject.decrypt(encryptedcontent.encode("utf-8"))
				except InvalidToken:
					raise
				richtextobjects["text"]["content"] = plaincontent.decode()
		
		if block["has_children"]:
			block[blocktype]["children"] = decryptcontent(block[blocktype]["children"])


	return blocks

main()
# #oldPageID = "83f6fa134641491286c3b2de1d80d725"
# plainpageid = "9cfbc91c1ca14dc7bffc2c1f8d80d4e2"

# # b = get_children_blocks(notion, plainpageid)
# # en = encryptcontent(b)
# # print(en)
# # #append_children_to_parentblock(notion, blockid, encryptcontent(get_children_blocks(notion, blockid)))
# # #append_children_to_parentblock(notion, oldPageID, decryptcontent(get_children_blocks(notion, blockid)))
# # #pprint(get_parentpage_details(notion, "fef2fef2572d4b65a765f65aa57db72f"))
# # create_new_page(notion, plainpageid, en)

# encryptid = "897f6972911c4534af16b363f764023d"
# b = get_children_blocks(notion, encryptid)
# de = decryptcontent(b)
# create_new_page(notion, encryptid, de)