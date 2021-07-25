from typing import Any, Dict
from urllib.parse import urlparse
from uuid import UUID

def get_url(object_id: str) -> str:
    """Return the URL for the object with the given id."""
    return "https://notion.so/" + UUID(object_id).hex


def get_id(url: str) -> str:
    """Return the id of the object behind the given URL."""
    parsed = urlparse(url)
    if "notion.so" != parsed.netloc[-9:]:
        raise ValueError("Not a valid Notion URL.")
    path = parsed.path
    if len(path) < 32:
        raise ValueError("The path in the URL seems to be incorrect.")
    raw_id = path[-32:]
    return str(UUID(raw_id))

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