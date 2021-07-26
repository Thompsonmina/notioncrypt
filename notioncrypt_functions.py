from typing import Any, Dict
from urllib.parse import urlparse
from uuid import UUID
import functools



def get_url(object_id: str) -> str:
    """Return the URL for the object with the given id."""
    return "https://notion.so/" + UUID(object_id).hex


def get_id(url: str) -> str:
    """Return the id of the object behind the given URL."""
    parsed = urlparse(url)
    if "notion.so" != parsed.netloc[-9:]:
        raise ValueError("Not a valid Notion URL.")
    
    path = parsed.path
    if "?" in path:
        pos = path.index("?")
        path = path[:pos]

    if len(path) < 32:
        raise ValueError("The path in the URL seems to be incorrect.")
    raw_id = path[-32:]
    
    return str(UUID(raw_id))

@functools.lru_cache()
def get_parentpage_details(client, pageid: str):
    """
        Get the relevant meta information about the parent of a page,
        only allow pages whose parents are also pages. Pages that belong
        to a notion database or toplevel workspace will not be processed
    """
    PAGE_IDENTIFER = "page_id"
    page = client.pages.retrieve(pageid)
    if page["parent"]["type"] == PAGE_IDENTIFER:
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


def create_new_page(client, parent_pagedetails, children_contentblocks):
    """
        Create a new page with its page contents and attach it 
        to the parent passed
    """
    if children_contentblocks:
        page_payload = parent_pagedetails
        
        if page_payload and children_contentblocks:
            page_payload["children"] = children_contentblocks
            client.pages.create(**page_payload)

@functools.lru_cache()
def get_children_blocks(client, blockid, recursive=True):
    """
        Recursively get all the contents of a block (a page is also a block).
        all the content are also blocks that might have content of thier own
        hence the recursion.
    """
    children = client.blocks.children.list(blockid).get("results", [])
    if recursive:
        for block in children:
            if block["has_children"]:
                blocktype = block["type"]
                block[blocktype]["children"] = getchildren(client, block["id"])
    return children


def append_children_to_parentblock(client, blockid, children):
    """ append children to a block"""
    client.blocks.children.append(blockid, **{"children":children})

def encryptcontent(blocks, fernetobject):
    """
        recursively encrypt all the text content of text blocks
        should ignore other types of blocks i guess 
        todo do something about children page blocks 
    """
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